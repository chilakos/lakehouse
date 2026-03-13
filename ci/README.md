# CI/CD Workflows

## Authoring Convention

The **source of truth** for all GitHub Actions workflows is `ci/.github/workflows/`.

GitHub Actions requires workflow files at `.github/workflows/` in the repository root.
Since Git does not follow directory symlinks, workflow files are **copied** to
`.github/workflows/` with a header comment indicating their source.

### Editing Workflows

1. Edit the file in `ci/.github/workflows/`
2. Copy the updated file to `.github/workflows/` (preserve the source-of-truth comment)
3. Commit both files together

### Workflow Files

| File | Trigger | Purpose |
|------|---------|---------|
| `ci.yml` | PR to dev/staging/main | Lint, test, terraform validate |
| `deploy-dev.yml` | Push to dev | Deploy to dev environment |
| `deploy-staging.yml` | Push to staging | Deploy to staging environment |
| `deploy-prod.yml` | Push to main | Deploy to production |
| `infra.yml` | PR changing infra/** | Terraform plan review on all envs |

### Environment Promotion

```
feature branch --> PR to dev --> merge to dev (auto-deploy)
                                    |
                              PR to staging --> merge to staging (deploy + approval)
                                                    |
                                              PR to main --> merge to main (deploy + approval + smoke tests)
```
