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

# Networking variables
variable "vpc_id" {
  description = "VPC ID for security group creation"
  type        = string
  default     = ""
}

variable "allowed_cidrs" {
  description = "CIDR blocks allowed to access lakehouse services"
  type        = list(string)
  default     = []
}

# S3 module variables
variable "bucket_name_prefix" {
  description = "Prefix for S3 bucket names"
  type        = string
  default     = "lakehouse"
}

# MinIO module variables
variable "minio_access_key" {
  description = "MinIO access key for authentication"
  type        = string
  sensitive   = true
  default     = ""
}

variable "minio_secret_key" {
  description = "MinIO secret key for authentication"
  type        = string
  sensitive   = true
  default     = ""
}

variable "minio_bucket_names" {
  description = "List of MinIO buckets to create"
  type        = list(string)
  default     = ["lakehouse-data", "lakehouse-onprem"]
}

# Kubernetes variables
variable "kubernetes_namespace" {
  description = "Kubernetes namespace for lakehouse services"
  type        = string
  default     = "lakehouse"
}

# Nessie module variables
variable "nessie_db_password" {
  description = "Password for Nessie PostgreSQL database"
  type        = string
  sensitive   = true
  default     = ""
}

# Trino module variables
variable "ldap_url" {
  description = "LDAP server URL for Trino authentication"
  type        = string
  default     = ""
}

variable "ldap_user_bind_pattern" {
  description = "LDAP user bind pattern for Trino authentication"
  type        = string
  default     = ""
}

variable "ldap_user_base_dn" {
  description = "LDAP user base DN for Trino authentication"
  type        = string
  default     = ""
}

variable "trino_tls_keystore_password" {
  description = "Password for Trino TLS keystore"
  type        = string
  sensitive   = true
  default     = ""
}

variable "trino_access_control_rules" {
  description = "JSON string with Trino file-based access control rules"
  type        = string
  default     = <<-EOT
    {
      "catalogs": [
        {
          "allow": "all"
        }
      ]
    }
  EOT
}
