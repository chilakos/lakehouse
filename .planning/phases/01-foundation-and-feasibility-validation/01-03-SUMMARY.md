---
phase: 01-foundation-and-feasibility-validation
plan: 03
subsystem: infra
tags: [terraform, github-actions, cicd, s3, kms, minio, nessie, trino, helm, security-groups, oidc, tls]

# Dependency graph
requires:
  - phase: 01-01
    provides: "Mono-repo structure, Terraform scaffolding with root main.tf and env-specific tfvars"
provides:
  - "Terraform modules for S3 (SSE-KMS), MinIO, networking, Nessie (Helm + TLS), Trino (Helm + LDAP + TLS)"
  - "Root Terraform module wiring all 5 modules with cross-module output passing"
  - "GitHub Actions CI workflow (lint, test, terraform validate/fmt)"
  - "GitHub Actions deploy workflows for dev, staging, prod with OIDC and environment protection"
  - "GitHub Actions infra plan review workflow posting Terraform plans as PR comments"
  - "S3 SSE-KMS encryption at rest with KMS key rotation (SEC-05)"
  - "TLS/HTTPS on Nessie and Trino endpoints via cert-manager (SEC-06)"
affects: [01-04, 02-01]

# Tech tracking
tech-stack:
  added: [aws-kms, aws-s3-sse, helm-release, cert-manager, github-actions-oidc, terraform-workspaces]
  patterns: [standalone-sg-rules-for-cross-references, workflow-copy-with-source-header, templatefile-helm-values, environment-isolation-via-workspaces]

key-files:
  created:
    - infra/terraform/modules/s3/main.tf
    - infra/terraform/modules/s3/variables.tf
    - infra/terraform/modules/s3/outputs.tf
    - infra/terraform/modules/minio/main.tf
    - infra/terraform/modules/minio/variables.tf
    - infra/terraform/modules/minio/outputs.tf
    - infra/terraform/modules/networking/main.tf
    - infra/terraform/modules/networking/variables.tf
    - infra/terraform/modules/networking/outputs.tf
    - infra/terraform/modules/nessie/main.tf
    - infra/terraform/modules/nessie/variables.tf
    - infra/terraform/modules/nessie/outputs.tf
    - infra/terraform/modules/nessie/values.yaml.tpl
    - infra/terraform/modules/trino/main.tf
    - infra/terraform/modules/trino/variables.tf
    - infra/terraform/modules/trino/outputs.tf
    - infra/terraform/modules/trino/values.yaml.tpl
    - ci/.github/workflows/deploy-dev.yml
    - ci/.github/workflows/deploy-staging.yml
    - ci/.github/workflows/deploy-prod.yml
    - ci/.github/workflows/infra.yml
    - .github/workflows/ci.yml
    - .github/workflows/deploy-dev.yml
    - .github/workflows/deploy-staging.yml
    - .github/workflows/deploy-prod.yml
    - .github/workflows/infra.yml
    - ci/README.md
  modified:
    - infra/terraform/main.tf
    - infra/terraform/variables.tf
    - ci/.github/workflows/ci.yml
    - infra/terraform/environments/dev/terraform.tfvars
    - infra/terraform/environments/staging/terraform.tfvars
    - infra/terraform/environments/prod/terraform.tfvars

key-decisions:
  - "Used standalone aws_security_group_rule resources for cross-SG references to break Terraform cycle dependency"
  - "Copied workflow files to .github/workflows/ instead of symlink (git does not follow directory symlinks)"
  - "Nessie Helm values use templatefile() with .yaml.tpl for environment-specific configuration injection"
  - "Trino uses REST catalog type (iceberg.catalog.type=rest) pointing to Nessie internal endpoint"
  - "OIDC for all AWS authentication in GitHub Actions (no long-lived credentials)"
  - "Matrix strategy in infra.yml runs Terraform plan across all 3 environments in parallel"

patterns-established:
  - "Standalone SG rules: use aws_security_group_rule for cross-SG references to avoid circular dependencies"
  - "Workflow authoring convention: source of truth in ci/.github/workflows/, copies at .github/workflows/"
  - "Helm values templating: templatefile() with .yaml.tpl files for environment injection"
  - "Environment isolation: Terraform workspaces + per-environment tfvars files"
  - "OIDC auth: all deployment workflows use aws-actions/configure-aws-credentials with role-to-assume"

requirements-completed: [CICD-02, CICD-03, CICD-04, SEC-05, SEC-06]

# Metrics
duration: 12min
completed: 2026-03-13
---

# Phase 1 Plan 3: Terraform IaC Modules and GitHub Actions CI/CD Summary

**Five Terraform modules (S3 with SSE-KMS, MinIO, networking, Nessie Helm, Trino Helm with LDAP/TLS) wired in root module, plus 5 GitHub Actions workflows for CI and environment promotion via OIDC**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-13T02:22:12Z
- **Completed:** 2026-03-13T02:34:08Z
- **Tasks:** 3
- **Files modified:** 33

## Accomplishments
- Five Terraform modules fully implemented: S3 (SSE-KMS encryption, KMS key rotation, versioning, public access block, IAM policy), MinIO (bucket config via mc CLI, Kubernetes credentials secret), networking (least-privilege security groups for Nessie/Trino/PostgreSQL), Nessie (Helm release with PostgreSQL backend, TLS via cert-manager), Trino (Helm release with HTTPS, LDAP auth, file-based access control, Iceberg REST catalog)
- Root main.tf wires all 5 modules with cross-module output passing (S3 bucket name to Nessie, Nessie internal endpoint to Trino)
- Five GitHub Actions workflows: CI (lint, test, terraform validate/fmt on PRs), deploy-dev (auto on push to dev), deploy-staging (with environment protection), deploy-prod (with smoke tests), infra.yml (Terraform plan review on infra PRs across all 3 environments)
- All deployment workflows use OIDC for AWS authentication (no long-lived credentials)
- Terraform validate passes cleanly, terraform fmt passes cleanly
- SEC-05 satisfied: S3 SSE-KMS with KMS key rotation enabled
- SEC-06 satisfied: TLS on Nessie (Quarkus HTTPS) and Trino (coordinator HTTPS port 8443) via cert-manager certificates

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Terraform modules for S3, MinIO, and networking** - `2287bcb` (feat)
2. **Task 2: Create Terraform modules for Nessie and Trino, wire root module** - `7f19cf8` (feat)
3. **Task 3: Create GitHub Actions CI/CD workflows for environment promotion** - `e304098` (feat)

## Files Created/Modified
- `infra/terraform/modules/s3/main.tf` - S3 bucket with SSE-KMS, KMS key with rotation, versioning, public access block, IAM policy
- `infra/terraform/modules/s3/variables.tf` - Environment, bucket prefix, KMS deletion window, tags
- `infra/terraform/modules/s3/outputs.tf` - Bucket name/ARN, KMS key ARN/ID, IAM policy ARN
- `infra/terraform/modules/minio/main.tf` - Bucket creation via mc CLI, Kubernetes secret for credentials
- `infra/terraform/modules/minio/variables.tf` - Endpoint, credentials (sensitive), bucket names, namespace
- `infra/terraform/modules/minio/outputs.tf` - Endpoint, bucket names, credentials secret name
- `infra/terraform/modules/networking/main.tf` - Security groups for Nessie, Trino, PostgreSQL with standalone cross-SG rules
- `infra/terraform/modules/networking/variables.tf` - VPC ID, allowed CIDRs, environment, tags
- `infra/terraform/modules/networking/outputs.tf` - Security group IDs for Nessie, Trino, PostgreSQL
- `infra/terraform/modules/nessie/main.tf` - Helm release for Nessie, cert-manager TLS certificate
- `infra/terraform/modules/nessie/variables.tf` - Replicas, DB password, S3/MinIO config, TLS secret
- `infra/terraform/modules/nessie/outputs.tf` - HTTPS and internal endpoints
- `infra/terraform/modules/nessie/values.yaml.tpl` - Helm values template with PostgreSQL, TLS, S3/MinIO config
- `infra/terraform/modules/trino/main.tf` - Helm release for Trino, access control ConfigMap, cert-manager TLS
- `infra/terraform/modules/trino/variables.tf` - Workers, memory, LDAP, TLS, access control rules
- `infra/terraform/modules/trino/outputs.tf` - HTTPS endpoint, coordinator service name
- `infra/terraform/modules/trino/values.yaml.tpl` - Helm values with catalog, LDAP, TLS, resource limits
- `infra/terraform/main.tf` - Root module wiring all 5 modules with cross-module dependencies
- `infra/terraform/variables.tf` - Extended with networking, MinIO, Nessie, Trino, LDAP variables
- `ci/.github/workflows/ci.yml` - Updated: split terraform-fmt into own job, removed push trigger
- `ci/.github/workflows/deploy-dev.yml` - Deploy to dev on push to dev branch
- `ci/.github/workflows/deploy-staging.yml` - Deploy to staging with environment protection
- `ci/.github/workflows/deploy-prod.yml` - Deploy to production with smoke tests
- `ci/.github/workflows/infra.yml` - Terraform plan review on infra PRs, posts as PR comment
- `.github/workflows/*.yml` - Copies of ci/ workflows for GitHub Actions discovery
- `ci/README.md` - Authoring convention documentation

## Decisions Made
- **Standalone SG rules for cross-references:** Used `aws_security_group_rule` instead of inline `ingress`/`egress` blocks for cross-security-group references (Nessie <-> Trino, Nessie -> Postgres) to break Terraform's circular dependency error
- **Copy over symlink for GitHub workflow discovery:** Git stores directory symlinks as single entries (not resolving contents), so GitHub Actions cannot discover workflows via symlinked directories. Copied files with `# Source of truth: ci/.github/workflows/` header comments instead
- **Trino REST catalog type:** Used `iceberg.catalog.type=rest` pointing to Nessie's `/iceberg` endpoint with `prefix=main`, consistent with the decision made in Plan 01-01
- **OIDC everywhere:** All deployment workflows use `aws-actions/configure-aws-credentials@v4` with `role-to-assume` from secrets -- no long-lived AWS credentials
- **Matrix strategy for infra plan:** `infra.yml` runs Terraform plan across dev/staging/prod in parallel via matrix strategy, posting each as a separate PR comment
- **Environment variable injection for security:** Used `env:` blocks in infra.yml to avoid direct use of `${{ matrix.environment }}` in shell commands (GitHub Actions security best practice)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed security group circular dependency**
- **Found during:** Task 2 (terraform validate)
- **Issue:** Inline security group rules in networking module created a cycle: Nessie SG referenced Trino SG (ingress), Trino SG referenced Nessie SG (egress), Nessie SG referenced Postgres SG (egress), Postgres SG referenced Nessie SG (ingress)
- **Fix:** Extracted all cross-SG references into standalone `aws_security_group_rule` resources
- **Files modified:** `infra/terraform/modules/networking/main.tf`
- **Verification:** `terraform validate` passes cleanly
- **Committed in:** 7f19cf8 (Task 2 commit)

**2. [Rule 1 - Bug] Added missing filter block to S3 lifecycle rule**
- **Found during:** Task 2 (terraform validate)
- **Issue:** AWS provider warning: lifecycle rule requires either `filter` or `prefix` attribute
- **Fix:** Added empty `filter {}` block to lifecycle rule (applies to all objects)
- **Files modified:** `infra/terraform/modules/s3/main.tf`
- **Verification:** `terraform validate` passes without warnings
- **Committed in:** 7f19cf8 (Task 2 commit)

**3. [Rule 3 - Blocking] Installed Terraform for validation**
- **Found during:** Task 2 (terraform validate step)
- **Issue:** Terraform CLI not available on execution environment
- **Fix:** Installed Terraform 1.7.5 from HashiCorp releases
- **Files modified:** None (system tool installation)
- **Verification:** `terraform --version` shows 1.7.5

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness. SG cycle fix is a common Terraform pattern. No scope creep.

## Issues Encountered
- GitHub Actions security hook flagged workflow files for review. All workflows were verified to not use untrusted user input in `run:` commands. The `infra.yml` was updated to use `env:` blocks for matrix values as a security best practice.

## User Setup Required
None - no external service configuration required. AWS credentials and GitHub secrets (AWS_ROLE_ARN) must be configured separately per environment before workflows can execute.

## Next Phase Readiness
- All 5 Terraform modules are fully implemented and validate cleanly -- ready for `terraform plan` against real AWS infrastructure
- GitHub Actions workflows are ready for use once repository branches (dev, staging) are created and GitHub environment protection rules are configured
- Nessie and Trino modules use cert-manager for TLS -- cert-manager CRDs and ClusterIssuer must be deployed to the Kubernetes cluster before applying
- Plan 01-04 (multi-engine query validation, RBAC, benchmarks) can proceed as Terraform IaC foundation is complete
- The 3 deployment environments (dev/staging/prod) each get isolated Nessie + Trino + S3 infrastructure via Terraform workspaces

## Self-Check: PASSED

- All 30 key files verified present on disk
- All 3 task commits verified in git history (2287bcb, 7f19cf8, e304098)
- Terraform validate passes cleanly
- Terraform fmt check passes cleanly
- All 5 CI/CD workflow files are valid YAML

---
*Phase: 01-foundation-and-feasibility-validation*
*Completed: 2026-03-13*
