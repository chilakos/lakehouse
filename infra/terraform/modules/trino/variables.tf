# Trino Module Variables

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "namespace" {
  description = "Kubernetes namespace for Trino deployment"
  type        = string
  default     = "lakehouse"
}

variable "trino_workers" {
  description = "Number of Trino worker nodes"
  type        = number
  default     = 2
}

variable "trino_chart_version" {
  description = "Trino Helm chart version"
  type        = string
  default     = "0.35.0"
}

variable "coordinator_memory" {
  description = "Memory allocation for Trino coordinator (e.g., 8GB)"
  type        = string
  default     = "8GB"
}

variable "worker_memory" {
  description = "Memory allocation for Trino workers (e.g., 16GB)"
  type        = string
  default     = "16GB"
}

variable "nessie_endpoint" {
  description = "Nessie catalog REST endpoint URL (e.g., http://nessie:19120/iceberg)"
  type        = string
}

# LDAP authentication configuration
variable "ldap_url" {
  description = "LDAP server URL for authentication (e.g., ldaps://ldap.example.com:636)"
  type        = string
  default     = ""
}

variable "ldap_user_bind_pattern" {
  description = "LDAP user bind pattern (e.g., uid=$${USER},ou=people,dc=example,dc=com)"
  type        = string
  default     = ""
}

variable "ldap_user_base_dn" {
  description = "LDAP user base DN for searches (e.g., ou=people,dc=example,dc=com)"
  type        = string
  default     = ""
}

# TLS configuration
variable "tls_keystore_path" {
  description = "Path to TLS keystore file inside container"
  type        = string
  default     = "/tls/keystore.jks"
}

variable "tls_keystore_password" {
  description = "Password for TLS keystore"
  type        = string
  sensitive   = true
  default     = ""
}

# Access control
variable "access_control_rules" {
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
