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

variable "resource_group_rules" {
  description = "JSON string with Trino resource group definitions (ADR-004)"
  type        = string
  default     = <<-EOT
    {
      "rootGroups": [
        {
          "name": "engineering",
          "softMemoryLimit": "60%",
          "maxQueued": 100,
          "hardConcurrencyLimit": 20,
          "schedulingPolicy": "fair",
          "subGroups": [
            { "name": "etl_pipelines", "softMemoryLimit": "40%", "hardConcurrencyLimit": 15, "schedulingWeight": 3, "runningTimeLimit": "4h" },
            { "name": "soda_quality",  "softMemoryLimit": "15%", "hardConcurrencyLimit": 5,  "runningTimeLimit": "30m" },
            { "name": "schema_ops",    "softMemoryLimit": "5%",  "hardConcurrencyLimit": 3,  "runningTimeLimit": "10m" }
          ]
        },
        {
          "name": "bi",
          "softMemoryLimit": "35%",
          "maxQueued": 200,
          "hardConcurrencyLimit": 30,
          "schedulingPolicy": "weighted_fair",
          "subGroups": [
            { "name": "cube_semantic", "softMemoryLimit": "20%", "hardConcurrencyLimit": 20, "runningTimeLimit": "5m" },
            { "name": "power_bi",      "softMemoryLimit": "10%", "hardConcurrencyLimit": 15, "runningTimeLimit": "10m" },
            { "name": "tableau",       "softMemoryLimit": "5%",  "hardConcurrencyLimit": 10, "runningTimeLimit": "10m" }
          ]
        },
        { "name": "ai_agents", "softMemoryLimit": "5%", "maxQueued": 50, "hardConcurrencyLimit": 5, "runningTimeLimit": "2m" }
      ],
      "selectors": [
        { "group": "engineering.etl_pipelines", "user": "svc_etl_pipeline|svc_airflow|svc_spark" },
        { "group": "engineering.soda_quality",  "user": "svc_soda" },
        { "group": "engineering.schema_ops",    "source": "schema-migration|ddl-runner" },
        { "group": "bi.cube_semantic",          "source": "cube" },
        { "group": "bi.power_bi",               "source": "PowerBI|power-bi" },
        { "group": "bi.tableau",                "source": "Tableau|tableau" },
        { "group": "ai_agents",                 "user": "svc_borealis|svc_rbc_assist|svc_fastapi_ai" },
        { "group": "engineering.etl_pipelines", "user": ".*" }
      ]
    }
  EOT
}
