"""Ranger policy definition utilities for the lakehouse governance framework.

Builds Apache Ranger policy dicts that can be submitted via RangerClient.create_policy().
All functions return policy structures without requiring a live Ranger connection,
making them fully testable in unit tests.

Policy types:
- policyType=0: Standard access (SELECT, INSERT, UPDATE, DELETE)
- policyType=1: Data masking (MASK_NULL, MASK_HASH, MASK_SHOW_LAST_4, etc.)
- policyType=2: Row-level filtering (SQL WHERE clause per group)

Reference: https://ranger.apache.org/api_guide.html
"""

from __future__ import annotations


def _build_policy_item(groups: list[str], accesses: list[dict]) -> dict:
    """Build a Ranger policyItem dict for the given groups and accesses."""
    return {
        "groups": groups,
        "accesses": accesses,
        "conditions": [],
        "delegateAdmin": False,
    }


def create_masking_policy(
    service: str,
    policy_name: str,
    tag_or_resource: dict,
    groups: list[str],
    mask_type: str,
) -> dict:
    """Build a Ranger data masking policy (policyType=1).

    Creates a column masking policy that applies the specified mask type
    to columns matching the tag or resource spec.

    Args:
        service: Ranger service name (e.g., "trino").
        policy_name: Unique policy name.
        tag_or_resource: Resource selector dict. Use {"column": "col_name"} for
            column-based masking or {"tag": "TAG_NAME"} for tag-based masking.
        groups: List of Ranger group names this policy applies to.
        mask_type: Masking algorithm. Valid values: MASK, MASK_SHOW_LAST_4,
            MASK_SHOW_FIRST_4, MASK_HASH, MASK_NULL, MASK_NONE.

    Returns:
        Ranger policy dict with policyType=1 ready for RangerClient.create_policy().
    """
    # Build resource spec from tag_or_resource
    resources: dict = {}
    if "column" in tag_or_resource:
        resources["column"] = {
            "values": [tag_or_resource["column"]],
            "isExcludes": False,
            "isRecursive": False,
        }
    elif "tag" in tag_or_resource:
        resources["tag"] = {
            "values": [tag_or_resource["tag"]],
            "isExcludes": False,
            "isRecursive": False,
        }

    mask_info = {"dataMaskType": {"name": mask_type}}

    policy_item = {
        "groups": groups,
        "accesses": [{"type": "select", "isAllowed": True}],
        "conditions": [],
        "delegateAdmin": False,
        "dataMaskInfo": mask_info,
    }

    return {
        "name": policy_name,
        "service": service,
        "policyType": 1,
        "isEnabled": True,
        "isAuditEnabled": True,
        "resources": resources,
        "dataMaskPolicyItems": [policy_item],
        "policyLabels": [],
    }


def create_row_filter_policy(
    service: str,
    policy_name: str,
    catalog: str,
    schema: str,
    table: str,
    groups: list[str],
    filter_expr: str,
) -> dict:
    """Build a Ranger row-level filter policy (policyType=2).

    Creates a row filter policy that restricts rows visible to the specified
    groups based on a SQL WHERE clause expression.

    Args:
        service: Ranger service name (e.g., "trino").
        policy_name: Unique policy name.
        catalog: Trino catalog name (e.g., "iceberg").
        schema: Schema/database name (e.g., "gold").
        table: Table name (e.g., "trades").
        groups: List of Ranger group names this filter applies to.
        filter_expr: SQL WHERE clause expression (e.g., "business_unit = current_user()").

    Returns:
        Ranger policy dict with policyType=2 ready for RangerClient.create_policy().
    """
    row_filter_item = {
        "groups": groups,
        "accesses": [{"type": "select", "isAllowed": True}],
        "conditions": [],
        "delegateAdmin": False,
        "rowFilterInfo": {"filterExpr": filter_expr},
    }

    return {
        "name": policy_name,
        "service": service,
        "policyType": 2,
        "isEnabled": True,
        "isAuditEnabled": True,
        "resources": {
            "catalog": {
                "values": [catalog],
                "isExcludes": False,
                "isRecursive": False,
            },
            "schema": {
                "values": [schema],
                "isExcludes": False,
                "isRecursive": False,
            },
            "table": {
                "values": [table],
                "isExcludes": False,
                "isRecursive": False,
            },
        },
        "rowFilterPolicyItems": [row_filter_item],
        "policyLabels": [],
    }


def create_tag_policy(
    tag_service: str,
    policy_name: str,
    tag_name: str,
    groups: list[str],
    mask_type: str,
) -> dict:
    """Build a Ranger tag-based masking policy (policyType=1 on tag service).

    Creates a tag-based masking policy that applies to all columns tagged
    with the specified sensitivity tag, regardless of catalog/table/column.
    This is the recommended approach for scaling to 300+ sources.

    Args:
        tag_service: Ranger tag service name (e.g., "trino_tag").
        policy_name: Unique policy name.
        tag_name: Sensitivity tag name (e.g., "RESTRICTED", "CONFIDENTIAL").
        groups: List of Ranger group names this masking applies to.
        mask_type: Masking algorithm (e.g., MASK_NULL, MASK_HASH, MASK_SHOW_LAST_4).

    Returns:
        Ranger policy dict with policyType=1 on the tag service.
    """
    mask_info = {"dataMaskType": {"name": mask_type}}

    policy_item = {
        "groups": groups,
        "accesses": [{"type": "trino:select", "isAllowed": True}],
        "conditions": [],
        "delegateAdmin": False,
        "dataMaskInfo": mask_info,
    }

    return {
        "name": policy_name,
        "service": tag_service,
        "policyType": 1,
        "isEnabled": True,
        "isAuditEnabled": True,
        "resources": {
            "tag": {
                "values": [tag_name],
                "isExcludes": False,
                "isRecursive": False,
            },
        },
        "dataMaskPolicyItems": [policy_item],
        "policyLabels": [],
    }


def create_access_policy(
    service: str,
    policy_name: str,
    catalog: str,
    schema: str,
    table: str,
    groups_permissions: dict[str, list[str]],
) -> dict:
    """Build a Ranger standard access control policy (policyType=0).

    Creates an access policy granting specified permissions to groups on
    a Trino catalog/schema/table resource.

    Args:
        service: Ranger service name (e.g., "trino").
        policy_name: Unique policy name.
        catalog: Trino catalog name (e.g., "iceberg").
        schema: Schema/database name, use "*" for all (e.g., "gold").
        table: Table name, use "*" for all (e.g., "trades").
        groups_permissions: Dict mapping group name to list of permission types.
            Valid permissions: select, insert, update, delete, all.
            Example: {"data_readers": ["select"], "data_admin": ["all"]}.

    Returns:
        Ranger policy dict with policyType=0 ready for RangerClient.create_policy().
    """
    policy_items = []
    for group, permissions in groups_permissions.items():
        accesses = [{"type": perm, "isAllowed": True} for perm in permissions]
        policy_items.append(
            {
                "groups": [group],
                "accesses": accesses,
                "conditions": [],
                "delegateAdmin": False,
            }
        )

    return {
        "name": policy_name,
        "service": service,
        "policyType": 0,
        "isEnabled": True,
        "isAuditEnabled": True,
        "resources": {
            "catalog": {
                "values": [catalog],
                "isExcludes": False,
                "isRecursive": False,
            },
            "schema": {
                "values": [schema],
                "isExcludes": False,
                "isRecursive": False,
            },
            "table": {
                "values": [table],
                "isExcludes": False,
                "isRecursive": False,
            },
        },
        "policyItems": policy_items,
        "policyLabels": [],
    }
