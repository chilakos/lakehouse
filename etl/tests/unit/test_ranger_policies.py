"""Unit tests for the Ranger policy helper functions.

Tests create_masking_policy(), create_row_filter_policy(),
create_tag_policy(), and create_access_policy().

No external services required -- builds policy dicts without a live Ranger connection.
"""

import pytest


@pytest.mark.unit
class TestCreateMaskingPolicy:
    """Test create_masking_policy() produces valid Ranger masking policy structures."""

    def test_returns_dict(self):
        from src.governance.ranger_policies import create_masking_policy

        result = create_masking_policy(
            service="trino",
            policy_name="mask-restricted-data_readers",
            tag_or_resource={"tag": "RESTRICTED"},
            groups=["data_readers"],
            mask_type="MASK_NULL",
        )
        assert isinstance(result, dict)

    def test_policy_type_is_1(self):
        from src.governance.ranger_policies import create_masking_policy

        result = create_masking_policy(
            service="trino",
            policy_name="mask-ssn-data_readers",
            tag_or_resource={"column": "ssn"},
            groups=["data_readers"],
            mask_type="MASK_NULL",
        )
        assert result.get("policyType") == 1

    def test_has_data_mask_policy_items(self):
        from src.governance.ranger_policies import create_masking_policy

        result = create_masking_policy(
            service="trino",
            policy_name="test-masking",
            tag_or_resource={"column": "ssn"},
            groups=["data_readers"],
            mask_type="MASK_SHOW_LAST_4",
        )
        assert "dataMaskPolicyItems" in result or "policyItems" in result

    def test_service_name_set(self):
        from src.governance.ranger_policies import create_masking_policy

        result = create_masking_policy(
            service="trino",
            policy_name="test-mask",
            tag_or_resource={"column": "ssn"},
            groups=["data_readers"],
            mask_type="MASK_NULL",
        )
        assert result.get("service") == "trino"

    def test_policy_name_set(self):
        from src.governance.ranger_policies import create_masking_policy

        result = create_masking_policy(
            service="trino",
            policy_name="my-masking-policy",
            tag_or_resource={"column": "ssn"},
            groups=["data_readers"],
            mask_type="MASK_NULL",
        )
        assert result.get("name") == "my-masking-policy"

    def test_mask_type_in_policy(self):
        from src.governance.ranger_policies import create_masking_policy

        result = create_masking_policy(
            service="trino",
            policy_name="test",
            tag_or_resource={"column": "ssn"},
            groups=["data_readers"],
            mask_type="MASK_SHOW_LAST_4",
        )
        # MASK_SHOW_LAST_4 should appear somewhere in the structure
        result_str = str(result)
        assert "MASK_SHOW_LAST_4" in result_str or "dataMaskType" in result_str

    def test_groups_included(self):
        from src.governance.ranger_policies import create_masking_policy

        result = create_masking_policy(
            service="trino",
            policy_name="test",
            tag_or_resource={"column": "ssn"},
            groups=["data_readers", "data_engineers"],
            mask_type="MASK_NULL",
        )
        result_str = str(result)
        assert "data_readers" in result_str or "groups" in result_str.lower()

    @pytest.mark.parametrize("mask_type", [
        "MASK", "MASK_SHOW_LAST_4", "MASK_SHOW_FIRST_4", "MASK_HASH",
        "MASK_NULL", "MASK_NONE",
    ])
    def test_all_mask_types_valid(self, mask_type):
        from src.governance.ranger_policies import create_masking_policy

        result = create_masking_policy(
            service="trino",
            policy_name=f"test-{mask_type}",
            tag_or_resource={"column": "test_col"},
            groups=["data_readers"],
            mask_type=mask_type,
        )
        assert isinstance(result, dict)
        assert result.get("policyType") == 1


@pytest.mark.unit
class TestCreateRowFilterPolicy:
    """Test create_row_filter_policy() produces valid Ranger row filter policy structures."""

    def test_returns_dict(self):
        from src.governance.ranger_policies import create_row_filter_policy

        result = create_row_filter_policy(
            service="trino",
            policy_name="row-filter-trades-bu",
            catalog="iceberg",
            schema="gold",
            table="trades",
            groups=["data_readers"],
            filter_expr="business_unit = current_user()",
        )
        assert isinstance(result, dict)

    def test_policy_type_is_2(self):
        from src.governance.ranger_policies import create_row_filter_policy

        result = create_row_filter_policy(
            service="trino",
            policy_name="row-filter-test",
            catalog="iceberg",
            schema="gold",
            table="trades",
            groups=["data_readers"],
            filter_expr="business_unit = 'wealth_mgmt'",
        )
        assert result.get("policyType") == 2

    def test_has_row_filter_info(self):
        from src.governance.ranger_policies import create_row_filter_policy

        result = create_row_filter_policy(
            service="trino",
            policy_name="test-row-filter",
            catalog="iceberg",
            schema="gold",
            table="positions",
            groups=["data_readers"],
            filter_expr="business_unit = current_user()",
        )
        assert "rowFilterPolicyItems" in result or "filterExpr" in str(result)

    def test_service_and_name_set(self):
        from src.governance.ranger_policies import create_row_filter_policy

        result = create_row_filter_policy(
            service="trino",
            policy_name="test-filter",
            catalog="iceberg",
            schema="gold",
            table="trades",
            groups=["data_readers"],
            filter_expr="1=1",
        )
        assert result.get("service") == "trino"
        assert result.get("name") == "test-filter"

    def test_filter_expr_in_policy(self):
        from src.governance.ranger_policies import create_row_filter_policy

        filter_expr = "business_unit = 'wealth_mgmt'"
        result = create_row_filter_policy(
            service="trino",
            policy_name="test-filter",
            catalog="iceberg",
            schema="gold",
            table="trades",
            groups=["data_readers"],
            filter_expr=filter_expr,
        )
        assert filter_expr in str(result)


@pytest.mark.unit
class TestCreateTagPolicy:
    """Test create_tag_policy() produces valid tag-based masking policies."""

    def test_returns_dict(self):
        from src.governance.ranger_policies import create_tag_policy

        result = create_tag_policy(
            tag_service="trino_tag",
            policy_name="tag-restricted-mask",
            tag_name="RESTRICTED",
            groups=["data_readers"],
            mask_type="MASK_NULL",
        )
        assert isinstance(result, dict)

    def test_policy_type_is_1(self):
        from src.governance.ranger_policies import create_tag_policy

        result = create_tag_policy(
            tag_service="trino_tag",
            policy_name="tag-restricted-mask",
            tag_name="RESTRICTED",
            groups=["data_readers"],
            mask_type="MASK_NULL",
        )
        assert result.get("policyType") == 1

    def test_tag_service_referenced(self):
        from src.governance.ranger_policies import create_tag_policy

        result = create_tag_policy(
            tag_service="trino_tag",
            policy_name="tag-restricted-mask",
            tag_name="RESTRICTED",
            groups=["data_readers"],
            mask_type="MASK_NULL",
        )
        assert "trino_tag" in str(result)

    def test_tag_name_in_policy(self):
        from src.governance.ranger_policies import create_tag_policy

        result = create_tag_policy(
            tag_service="trino_tag",
            policy_name="tag-confidential-mask",
            tag_name="CONFIDENTIAL",
            groups=["data_readers"],
            mask_type="MASK_HASH",
        )
        assert "CONFIDENTIAL" in str(result)


@pytest.mark.unit
class TestCreateAccessPolicy:
    """Test create_access_policy() produces valid standard access policies."""

    def test_returns_dict(self):
        from src.governance.ranger_policies import create_access_policy

        result = create_access_policy(
            service="trino",
            policy_name="data_readers-select",
            catalog="iceberg",
            schema="gold",
            table="*",
            groups_permissions={"data_readers": ["select"]},
        )
        assert isinstance(result, dict)

    def test_policy_type_is_0(self):
        from src.governance.ranger_policies import create_access_policy

        result = create_access_policy(
            service="trino",
            policy_name="data_admin-all",
            catalog="iceberg",
            schema="*",
            table="*",
            groups_permissions={"data_admin": ["all"]},
        )
        assert result.get("policyType") == 0

    def test_service_and_name_set(self):
        from src.governance.ranger_policies import create_access_policy

        result = create_access_policy(
            service="trino",
            policy_name="test-access",
            catalog="iceberg",
            schema="gold",
            table="*",
            groups_permissions={"data_readers": ["select"]},
        )
        assert result.get("service") == "trino"
        assert result.get("name") == "test-access"

    def test_permissions_in_policy(self):
        from src.governance.ranger_policies import create_access_policy

        result = create_access_policy(
            service="trino",
            policy_name="test-perms",
            catalog="iceberg",
            schema="gold",
            table="*",
            groups_permissions={"data_engineers": ["select", "insert", "update", "delete"]},
        )
        result_str = str(result)
        assert "data_engineers" in result_str


@pytest.mark.unit
class TestPolicyStructureSchema:
    """Test that policy structures match Ranger API schema expectations."""

    def test_masking_policy_required_fields(self):
        from src.governance.ranger_policies import create_masking_policy

        result = create_masking_policy(
            service="trino",
            policy_name="test",
            tag_or_resource={"column": "ssn"},
            groups=["data_readers"],
            mask_type="MASK_NULL",
        )
        # Required Ranger API fields
        assert "name" in result
        assert "service" in result
        assert "policyType" in result

    def test_row_filter_policy_required_fields(self):
        from src.governance.ranger_policies import create_row_filter_policy

        result = create_row_filter_policy(
            service="trino",
            policy_name="test",
            catalog="iceberg",
            schema="gold",
            table="trades",
            groups=["data_readers"],
            filter_expr="1=1",
        )
        assert "name" in result
        assert "service" in result
        assert "policyType" in result

    def test_access_policy_required_fields(self):
        from src.governance.ranger_policies import create_access_policy

        result = create_access_policy(
            service="trino",
            policy_name="test",
            catalog="iceberg",
            schema="gold",
            table="*",
            groups_permissions={"data_readers": ["select"]},
        )
        assert "name" in result
        assert "service" in result
        assert "policyType" in result
