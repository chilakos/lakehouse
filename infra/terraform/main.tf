# Lakehouse Infrastructure - Root Module Composition
#
# Composes all infrastructure modules for the lakehouse platform.
# Each environment (dev/staging/prod) gets fully isolated infrastructure
# via Terraform workspaces and environment-specific tfvars.

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "lakehouse"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# Networking module - VPC, subnets, security groups
# -----------------------------------------------------------------------------

module "networking" {
  source = "./modules/networking"

  environment   = var.environment
  vpc_id        = var.vpc_id
  allowed_cidrs = var.allowed_cidrs
}

# -----------------------------------------------------------------------------
# S3 storage module - Iceberg data lake buckets with SSE-KMS (SEC-05)
# -----------------------------------------------------------------------------

module "s3" {
  source = "./modules/s3"

  environment        = var.environment
  bucket_name_prefix = var.bucket_name_prefix
}

# -----------------------------------------------------------------------------
# MinIO module - On-prem S3-compatible storage configuration
# -----------------------------------------------------------------------------

module "minio" {
  source = "./modules/minio"

  environment      = var.environment
  minio_endpoint   = var.minio_endpoint
  minio_access_key = var.minio_access_key
  minio_secret_key = var.minio_secret_key
  bucket_names     = var.minio_bucket_names
  namespace        = var.kubernetes_namespace
}

# -----------------------------------------------------------------------------
# Nessie catalog module - Iceberg REST catalog with TLS (SEC-06)
# -----------------------------------------------------------------------------

module "nessie" {
  source = "./modules/nessie"

  environment        = var.environment
  namespace          = var.kubernetes_namespace
  nessie_replicas    = var.nessie_replicas
  nessie_db_password = var.nessie_db_password

  # Wire S3 bucket from s3 module
  s3_bucket = module.s3.bucket_name
  s3_region = var.region

  # Wire MinIO configuration
  minio_endpoint   = var.minio_endpoint
  minio_bucket     = "lakehouse-data"
  minio_access_key = var.minio_access_key
  minio_secret_key = var.minio_secret_key
}

# -----------------------------------------------------------------------------
# Trino query engine module - Distributed SQL with LDAP auth (SEC-06)
# -----------------------------------------------------------------------------

module "trino" {
  source = "./modules/trino"

  environment   = var.environment
  namespace     = var.kubernetes_namespace
  trino_workers = var.trino_workers

  # Wire Nessie endpoint from nessie module
  nessie_endpoint = module.nessie.internal_endpoint

  # LDAP authentication
  ldap_url               = var.ldap_url
  ldap_user_bind_pattern = var.ldap_user_bind_pattern
  ldap_user_base_dn      = var.ldap_user_base_dn

  # TLS configuration
  tls_keystore_password = var.trino_tls_keystore_password

  # Access control
  access_control_rules = var.trino_access_control_rules
}
