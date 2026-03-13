"""Governance module: data classification, Ranger policy management, audit trail,
freshness tracking, legacy lineage stubs, and anomaly detection.

Provides:
- SensitivityLevel enum and classify_column() for data classification
- Ranger policy helper functions for masking, row filtering, and access control
- Bootstrap script for seeding Ranger policies
- FreshnessSLA/FreshnessStatus and check_table_freshness() for SLA monitoring
- register_legacy_lineage_stub() and source helpers for Marquez lineage stubs
- AuditRecord/AUDIT_SCHEMA and cross-engine normalization functions
- AnomalyType/AnomalyReport/detect_anomalies() for suspicious access detection
- archive_old_records() for S3 Parquet archival of audit records
"""

from .classification import (
    CLASSIFICATION_RULES,
    SensitivityLevel,
    classify_column,
    classify_table_columns,
    get_columns_by_level,
)
from .freshness_tracker import (
    DEFAULT_SLAS,
    FreshnessSLA,
    FreshnessStatus,
    check_table_freshness,
    get_all_freshness,
    get_freshness_badge,
)
from .lineage_stubs import (
    register_legacy_lineage_stub,
    register_snowflake_sources,
    register_teradata_sources,
)
from .ranger_policies import (
    create_access_policy,
    create_masking_policy,
    create_row_filter_policy,
    create_tag_policy,
)
from .audit_schema import (
    AUDIT_SCHEMA,
    AuditRecord,
    normalize_trino_audit,
    normalize_teradata_audit,
    normalize_snowflake_audit,
)
from .anomaly_detector import (
    AnomalyType,
    AnomalyReport,
    detect_anomalies,
    format_anomaly_report,
)

__all__ = [
    # Classification
    "SensitivityLevel",
    "classify_column",
    "classify_table_columns",
    "get_columns_by_level",
    "CLASSIFICATION_RULES",
    # Ranger policies
    "create_masking_policy",
    "create_row_filter_policy",
    "create_tag_policy",
    "create_access_policy",
    # Freshness tracker
    "FreshnessStatus",
    "FreshnessSLA",
    "DEFAULT_SLAS",
    "check_table_freshness",
    "get_freshness_badge",
    "get_all_freshness",
    # Lineage stubs
    "register_legacy_lineage_stub",
    "register_teradata_sources",
    "register_snowflake_sources",
    # Audit schema
    "AuditRecord",
    "AUDIT_SCHEMA",
    "normalize_trino_audit",
    "normalize_teradata_audit",
    "normalize_snowflake_audit",
    # Anomaly detector
    "AnomalyType",
    "AnomalyReport",
    "detect_anomalies",
    "format_anomaly_report",
]
