# S3 Module Variables

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "bucket_name_prefix" {
  description = "Prefix for S3 bucket names (bucket = prefix-environment-data)"
  type        = string
  default     = "lakehouse"
}

variable "kms_key_deletion_window" {
  description = "Number of days before KMS key is deleted after scheduling (7-30)"
  type        = number
  default     = 30
  validation {
    condition     = var.kms_key_deletion_window >= 7 && var.kms_key_deletion_window <= 30
    error_message = "KMS key deletion window must be between 7 and 30 days."
  }
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
