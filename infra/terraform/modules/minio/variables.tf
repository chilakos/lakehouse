# MinIO Module Variables

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "minio_endpoint" {
  description = "MinIO server endpoint URL"
  type        = string
}

variable "minio_access_key" {
  description = "MinIO access key for authentication"
  type        = string
  sensitive   = true
}

variable "minio_secret_key" {
  description = "MinIO secret key for authentication"
  type        = string
  sensitive   = true
}

variable "bucket_names" {
  description = "List of MinIO buckets to create"
  type        = list(string)
  default     = ["lakehouse-data", "lakehouse-onprem"]
}

variable "namespace" {
  description = "Kubernetes namespace for MinIO credentials secret"
  type        = string
  default     = "lakehouse"
}
