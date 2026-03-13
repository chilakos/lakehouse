# Lakehouse Infrastructure - Root Module Composition
#
# This file composes all infrastructure modules for the lakehouse platform.
# Module implementations are stubs at this point (Plan 03 fills them in).

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

# Networking module - VPC, subnets, security groups
module "networking" {
  source = "./modules/networking"

  environment = var.environment
  region      = var.region
}

# S3 storage module - Iceberg data lake buckets
module "s3" {
  source = "./modules/s3"

  environment = var.environment
  s3_bucket   = var.s3_bucket
}

# MinIO module - On-prem S3-compatible storage configuration
module "minio" {
  source = "./modules/minio"

  environment    = var.environment
  minio_endpoint = var.minio_endpoint
}

# Nessie catalog module - Iceberg REST catalog
module "nessie" {
  source = "./modules/nessie"

  environment     = var.environment
  nessie_replicas = var.nessie_replicas
}

# Trino query engine module - Distributed SQL engine
module "trino" {
  source = "./modules/trino"

  environment   = var.environment
  trino_workers = var.trino_workers
}
