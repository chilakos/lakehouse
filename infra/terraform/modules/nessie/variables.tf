# Nessie Module Variables

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "namespace" {
  description = "Kubernetes namespace for Nessie deployment"
  type        = string
  default     = "lakehouse"
}

variable "nessie_replicas" {
  description = "Number of Nessie server replicas"
  type        = number
  default     = 2
}

variable "nessie_chart_version" {
  description = "Nessie Helm chart version"
  type        = string
  default     = "0.107.4"
}

variable "nessie_db_password" {
  description = "Password for Nessie PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "s3_bucket" {
  description = "S3 bucket name for Iceberg data warehouse"
  type        = string
}

variable "s3_region" {
  description = "AWS region for S3 bucket"
  type        = string
  default     = "us-east-1"
}

variable "minio_endpoint" {
  description = "MinIO endpoint URL for on-prem storage"
  type        = string
  default     = ""
}

variable "minio_bucket" {
  description = "MinIO bucket name for on-prem Iceberg data"
  type        = string
  default     = "lakehouse-data"
}

variable "minio_access_key" {
  description = "MinIO access key for on-prem storage"
  type        = string
  sensitive   = true
  default     = ""
}

variable "minio_secret_key" {
  description = "MinIO secret key for on-prem storage"
  type        = string
  sensitive   = true
  default     = ""
}

variable "tls_secret_name" {
  description = "Kubernetes secret name for TLS certificate (cert-manager)"
  type        = string
  default     = "nessie-tls"
}
