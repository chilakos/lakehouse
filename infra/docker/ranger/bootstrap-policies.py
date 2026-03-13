#!/usr/bin/env python3
"""Bootstrap Ranger Admin with initial Trino policies for the lakehouse platform.

Seeds the following policies in a new Ranger deployment:
1. Trino resource service ("trino") -- catalog/schema/table resource type
2. Trino tag service ("trino_tag") -- tag-based masking
3. Access policies: data_admin (all), data_engineers (DML), data_readers (SELECT)
4. Tag-based masking: RESTRICTED (MASK_NULL for readers, MASK_SHOW_LAST_4 for engineers)
5. Tag-based masking: CONFIDENTIAL (MASK_HASH for readers, MASK_SHOW_LAST_4 for engineers)
6. Row-level filters: gold.trades and gold.positions by business_unit
7. Column classification tags: seed example tags on gold.trades columns

Usage:
    # Wait for Ranger Admin to be ready, then run:
    python3 bootstrap-policies.py --ranger-url http://ranger-admin:6080

    # Or use environment variables:
    RANGER_URL=http://ranger-admin:6080 python3 bootstrap-policies.py

Idempotent: checks if policy exists by name before creating.
"""

import argparse
import logging
import os
import sys

import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RANGER_URL = os.environ.get("RANGER_URL", "http://ranger-admin:6080")
RANGER_USER = os.environ.get("RANGER_USER", "admin")
RANGER_PASSWORD = os.environ.get("RANGER_PASSWORD", "rangerR0cks!")

TRINO_SERVICE_NAME = "trino"
TRINO_TAG_SERVICE_NAME = "trino_tag"

# Role names must match Phase 1 rules.json for backward compatibility
ROLES = {
    "data_admin": "full access to all catalogs",
    "data_engineers": "full DML on iceberg catalog (except sensitive_ns)",
    "data_readers": "SELECT only on iceberg catalog",
}

# Business units for row-level filtering
BUSINESS_UNITS = ["wealth_mgmt", "investment_banking", "risk_management"]


# ---------------------------------------------------------------------------
# Ranger API helpers
# ---------------------------------------------------------------------------

class RangerAdminClient:
    """Lightweight Ranger Admin REST API client."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_service(self, service_name: str) -> dict | None:
        """Return service dict or None if not found."""
        resp = self.session.get(self._url(f"/service/public/v2/api/service/{service_name}"))
        if resp.status_code == 200:
            return resp.json()
        return None

    def create_service(self, service_def: dict) -> dict:
        """Create a new Ranger service."""
        resp = self.session.post(
            self._url("/service/public/v2/api/service"),
            json=service_def,
        )
        resp.raise_for_status()
        log.info("Created service: %s", service_def["name"])
        return resp.json()

    def get_policy_by_name(self, service_name: str, policy_name: str) -> dict | None:
        """Return policy dict or None if not found."""
        resp = self.session.get(
            self._url("/service/public/v2/api/policy"),
            params={"serviceName": service_name, "policyName": policy_name},
        )
        if resp.status_code == 200:
            policies = resp.json()
            if policies:
                return policies[0]
        return None

    def create_policy(self, policy: dict) -> dict:
        """Create a new Ranger policy. Returns created policy."""
        resp = self.session.post(
            self._url("/service/public/v2/api/policy"),
            json=policy,
        )
        resp.raise_for_status()
        log.info("Created policy: %s (type=%s)", policy["name"], policy.get("policyType", 0))
        return resp.json()

    def upsert_policy(self, service_name: str, policy: dict) -> None:
        """Create policy if it doesn't exist (idempotent by name)."""
        existing = self.get_policy_by_name(service_name, policy["name"])
        if existing:
            log.info("Policy already exists, skipping: %s", policy["name"])
        else:
            self.create_policy(policy)


# ---------------------------------------------------------------------------
# Service definitions
# ---------------------------------------------------------------------------

def get_trino_service_def() -> dict:
    """Return Ranger service definition for Trino resource service."""
    return {
        "name": TRINO_SERVICE_NAME,
        "type": "trino",
        "description": "Lakehouse Trino service for Iceberg catalog access",
        "configs": {
            "username": "admin",
            "password": "admin",
            "jdbc.url": f"jdbc:trino://trino:8080/iceberg",
            "jdbc.driverClassName": "io.trino.jdbc.TrinoDriver",
        },
        "isEnabled": True,
    }


def get_trino_tag_service_def() -> dict:
    """Return Ranger tag service definition for Trino tag-based policies."""
    return {
        "name": TRINO_TAG_SERVICE_NAME,
        "type": "tag",
        "description": "Lakehouse tag service for Trino sensitivity classification",
        "configs": {},
        "isEnabled": True,
    }


# ---------------------------------------------------------------------------
# Policy builders
# ---------------------------------------------------------------------------

def _resource(catalog: str, schema: str = "*", table: str = "*", column: str = "*") -> dict:
    """Build Ranger resource dict for a Trino catalog/schema/table/column."""
    return {
        "catalog": {"values": [catalog], "isExcludes": False, "isRecursive": False},
        "schema": {"values": [schema], "isExcludes": False, "isRecursive": False},
        "table": {"values": [table], "isExcludes": False, "isRecursive": False},
        "column": {"values": [column], "isExcludes": False, "isRecursive": False},
    }


def _policy_item(groups: list[str], accesses: list[str]) -> dict:
    """Build a basic policyItem for access control."""
    return {
        "groups": groups,
        "accesses": [{"type": a, "isAllowed": True} for a in accesses],
        "conditions": [],
        "delegateAdmin": False,
    }


def _mask_item(groups: list[str], mask_type: str) -> dict:
    """Build a dataMaskPolicyItem."""
    return {
        "groups": groups,
        "accesses": [{"type": "select", "isAllowed": True}],
        "conditions": [],
        "delegateAdmin": False,
        "dataMaskInfo": {"dataMaskType": {"name": mask_type}},
    }


def _row_filter_item(groups: list[str], filter_expr: str) -> dict:
    """Build a rowFilterPolicyItem."""
    return {
        "groups": groups,
        "accesses": [{"type": "select", "isAllowed": True}],
        "conditions": [],
        "delegateAdmin": False,
        "rowFilterInfo": {"filterExpr": filter_expr},
    }


def build_access_policies() -> list[dict]:
    """Build standard access control policies for three roles."""
    return [
        # data_admin: full access to all catalogs
        {
            "name": "data_admin-all-access",
            "service": TRINO_SERVICE_NAME,
            "policyType": 0,
            "isEnabled": True,
            "isAuditEnabled": True,
            "resources": _resource("*"),
            "policyItems": [_policy_item(["data_admin"], ["all"])],
            "policyLabels": ["bootstrap"],
        },
        # data_engineers: full DML on iceberg (except sensitive_ns schema)
        {
            "name": "data_engineers-iceberg-dml",
            "service": TRINO_SERVICE_NAME,
            "policyType": 0,
            "isEnabled": True,
            "isAuditEnabled": True,
            "resources": {
                "catalog": {"values": ["iceberg"], "isExcludes": False, "isRecursive": False},
                "schema": {"values": ["sensitive_ns"], "isExcludes": True, "isRecursive": False},
                "table": {"values": ["*"], "isExcludes": False, "isRecursive": False},
                "column": {"values": ["*"], "isExcludes": False, "isRecursive": False},
            },
            "policyItems": [
                _policy_item(["data_engineers"], ["select", "insert", "update", "delete"]),
            ],
            "policyLabels": ["bootstrap"],
        },
        # data_readers: SELECT only on iceberg (except sensitive_ns schema)
        {
            "name": "data_readers-iceberg-select",
            "service": TRINO_SERVICE_NAME,
            "policyType": 0,
            "isEnabled": True,
            "isAuditEnabled": True,
            "resources": {
                "catalog": {"values": ["iceberg"], "isExcludes": False, "isRecursive": False},
                "schema": {"values": ["sensitive_ns"], "isExcludes": True, "isRecursive": False},
                "table": {"values": ["*"], "isExcludes": False, "isRecursive": False},
                "column": {"values": ["*"], "isExcludes": False, "isRecursive": False},
            },
            "policyItems": [_policy_item(["data_readers"], ["select"])],
            "policyLabels": ["bootstrap"],
        },
    ]


def build_tag_masking_policies() -> list[dict]:
    """Build tag-based masking policies for all four sensitivity levels."""
    return [
        # RESTRICTED: MASK_NULL for readers, MASK_SHOW_LAST_4 for engineers, MASK_NONE for admin
        {
            "name": "tag-RESTRICTED-masking",
            "service": TRINO_TAG_SERVICE_NAME,
            "policyType": 1,
            "isEnabled": True,
            "isAuditEnabled": True,
            "resources": {
                "tag": {"values": ["RESTRICTED"], "isExcludes": False, "isRecursive": False},
            },
            "dataMaskPolicyItems": [
                _mask_item(["data_readers"], "MASK_NULL"),
                _mask_item(["data_engineers"], "MASK_SHOW_LAST_4"),
                _mask_item(["data_admin"], "MASK_NONE"),
            ],
            "policyLabels": ["bootstrap", "pii", "restricted"],
        },
        # CONFIDENTIAL: MASK_HASH for readers, MASK_SHOW_LAST_4 for engineers, MASK_NONE for admin
        {
            "name": "tag-CONFIDENTIAL-masking",
            "service": TRINO_TAG_SERVICE_NAME,
            "policyType": 1,
            "isEnabled": True,
            "isAuditEnabled": True,
            "resources": {
                "tag": {"values": ["CONFIDENTIAL"], "isExcludes": False, "isRecursive": False},
            },
            "dataMaskPolicyItems": [
                _mask_item(["data_readers"], "MASK_HASH"),
                _mask_item(["data_engineers"], "MASK_SHOW_LAST_4"),
                _mask_item(["data_admin"], "MASK_NONE"),
            ],
            "policyLabels": ["bootstrap", "pii", "confidential"],
        },
        # INTERNAL: MASK_NONE for all (classified but not masked)
        {
            "name": "tag-INTERNAL-masking",
            "service": TRINO_TAG_SERVICE_NAME,
            "policyType": 1,
            "isEnabled": True,
            "isAuditEnabled": True,
            "resources": {
                "tag": {"values": ["INTERNAL"], "isExcludes": False, "isRecursive": False},
            },
            "dataMaskPolicyItems": [
                _mask_item(["data_readers", "data_engineers", "data_admin"], "MASK_NONE"),
            ],
            "policyLabels": ["bootstrap", "internal"],
        },
        # PUBLIC: MASK_NONE for all
        {
            "name": "tag-PUBLIC-masking",
            "service": TRINO_TAG_SERVICE_NAME,
            "policyType": 1,
            "isEnabled": True,
            "isAuditEnabled": True,
            "resources": {
                "tag": {"values": ["PUBLIC"], "isExcludes": False, "isRecursive": False},
            },
            "dataMaskPolicyItems": [
                _mask_item(["data_readers", "data_engineers", "data_admin"], "MASK_NONE"),
            ],
            "policyLabels": ["bootstrap", "public"],
        },
    ]


def build_row_filter_policies() -> list[dict]:
    """Build row-level filter policies for gold.trades and gold.positions."""
    tables = ["trades", "positions"]
    policies = []
    for table in tables:
        policies.append({
            "name": f"row-filter-gold-{table}-by-business-unit",
            "service": TRINO_SERVICE_NAME,
            "policyType": 2,
            "isEnabled": True,
            "isAuditEnabled": True,
            "resources": {
                "catalog": {"values": ["iceberg"], "isExcludes": False, "isRecursive": False},
                "schema": {"values": ["gold"], "isExcludes": False, "isRecursive": False},
                "table": {"values": [table], "isExcludes": False, "isRecursive": False},
            },
            "rowFilterPolicyItems": [
                # Each business unit group sees only their rows
                _row_filter_item(
                    ["wealth_mgmt"],
                    "business_unit = 'wealth_mgmt'",
                ),
                _row_filter_item(
                    ["investment_banking"],
                    "business_unit = 'investment_banking'",
                ),
                _row_filter_item(
                    ["risk_management"],
                    "business_unit = 'risk_management'",
                ),
                # data_readers not in a BU group get an empty result (deny-all filter)
                _row_filter_item(["data_readers"], "1=0"),
            ],
            "policyLabels": ["bootstrap", "row-filter", "business-unit"],
        })
    return policies


# ---------------------------------------------------------------------------
# Column classification tag seeding
# ---------------------------------------------------------------------------

def seed_classification_tags(client: RangerAdminClient) -> None:
    """Seed Ranger Atlas tags on example gold.trades columns.

    Tags drive the masking policies -- once a column is tagged RESTRICTED,
    the RESTRICTED masking policy applies automatically.
    """
    # Tags are applied via the Tag REST API (atlas-style)
    tag_assignments = [
        # gold.trades.ssn -> RESTRICTED
        {"column": "iceberg.gold.trades.ssn", "tag": "RESTRICTED"},
        # gold.trades.account_number -> RESTRICTED
        {"column": "iceberg.gold.trades.account_number", "tag": "RESTRICTED"},
        # gold.trades.trader_email -> CONFIDENTIAL
        {"column": "iceberg.gold.trades.trader_email", "tag": "CONFIDENTIAL"},
        # gold.trades.business_unit -> INTERNAL
        {"column": "iceberg.gold.trades.business_unit", "tag": "INTERNAL"},
        # gold.trades.symbol -> PUBLIC
        {"column": "iceberg.gold.trades.symbol", "tag": "PUBLIC"},
    ]

    log.info("Seeding %d column classification tags...", len(tag_assignments))
    for assignment in tag_assignments:
        log.info(
            "  %s -> %s (tag service API call deferred -- requires Atlas integration)",
            assignment["column"],
            assignment["tag"],
        )
    log.info(
        "Note: Column tag assignment requires Ranger Tag Store or Atlas REST API. "
        "For dev, apply tags via Ranger Admin UI: Services > trino_tag > Tags."
    )


# ---------------------------------------------------------------------------
# Main bootstrap flow
# ---------------------------------------------------------------------------

def bootstrap(ranger_url: str) -> None:
    """Run the full bootstrap sequence against Ranger Admin."""
    client = RangerAdminClient(ranger_url, RANGER_USER, RANGER_PASSWORD)

    log.info("Bootstrapping Ranger at %s", ranger_url)

    # 1. Ensure Trino resource service exists
    if not client.get_service(TRINO_SERVICE_NAME):
        client.create_service(get_trino_service_def())
    else:
        log.info("Service already exists: %s", TRINO_SERVICE_NAME)

    # 2. Ensure Trino tag service exists
    if not client.get_service(TRINO_TAG_SERVICE_NAME):
        client.create_service(get_trino_tag_service_def())
    else:
        log.info("Service already exists: %s", TRINO_TAG_SERVICE_NAME)

    # 3. Access policies (policyType=0)
    log.info("Seeding access policies...")
    for policy in build_access_policies():
        client.upsert_policy(TRINO_SERVICE_NAME, policy)

    # 4. Tag-based masking policies (policyType=1)
    log.info("Seeding tag-based masking policies...")
    for policy in build_tag_masking_policies():
        client.upsert_policy(TRINO_TAG_SERVICE_NAME, policy)

    # 5. Row-level filter policies (policyType=2)
    log.info("Seeding row-filter policies...")
    for policy in build_row_filter_policies():
        client.upsert_policy(TRINO_SERVICE_NAME, policy)

    # 6. Seed classification tags on example columns
    seed_classification_tags(client)

    log.info("Bootstrap complete. Ranger policies are ready.")
    log.info(
        "Next steps:\n"
        "  1. Verify Ranger Admin UI at %s/login.jsp\n"
        "  2. Apply column tags via UI (trino_tag service)\n"
        "  3. Run integration tests: cd etl && python3 -m pytest tests/integration/test_ranger_masking.py",
        ranger_url,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap Ranger Admin with Trino lakehouse policies",
    )
    parser.add_argument(
        "--ranger-url",
        default=RANGER_URL,
        help=f"Ranger Admin URL (default: {RANGER_URL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print policies without applying them",
    )
    args = parser.parse_args()

    if args.dry_run:
        log.info("=== DRY RUN: Access Policies ===")
        for p in build_access_policies():
            log.info("  [access] %s", p["name"])
        log.info("=== DRY RUN: Tag Masking Policies ===")
        for p in build_tag_masking_policies():
            log.info("  [masking] %s", p["name"])
        log.info("=== DRY RUN: Row Filter Policies ===")
        for p in build_row_filter_policies():
            log.info("  [row-filter] %s", p["name"])
        return

    try:
        bootstrap(args.ranger_url)
    except requests.ConnectionError as e:
        log.error("Cannot connect to Ranger Admin at %s: %s", args.ranger_url, e)
        log.error("Is ranger-admin container running? docker compose up ranger-admin")
        sys.exit(1)
    except requests.HTTPError as e:
        log.error("Ranger API error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
