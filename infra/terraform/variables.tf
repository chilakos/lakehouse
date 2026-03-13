variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "nessie_replicas" {
  description = "Number of Nessie catalog server replicas"
  type        = number
  default     = 1
}

variable "trino_workers" {
  description = "Number of Trino worker nodes"
  type        = number
  default     = 1
}

variable "s3_bucket" {
  description = "S3 bucket name for Iceberg data lake storage"
  type        = string
}

variable "minio_endpoint" {
  description = "MinIO endpoint URL for on-prem S3-compatible storage"
  type        = string
  default     = "http://localhost:9000"
}

variable "domain" {
  description = "Base domain name for service endpoints"
  type        = string
  default     = "lakehouse.internal"
}

variable "state_bucket" {
  description = "S3 bucket for Terraform remote state"
  type        = string
  default     = "lakehouse-terraform-state"
}

variable "state_lock_table" {
  description = "DynamoDB table for Terraform state locking"
  type        = string
  default     = "lakehouse-terraform-locks"
}
