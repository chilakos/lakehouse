# Nessie Module Outputs

output "endpoint" {
  description = "Nessie catalog HTTPS endpoint (external)"
  value       = "https://nessie.${var.environment}.lakehouse.internal:19120/iceberg"
}

output "internal_endpoint" {
  description = "Nessie catalog HTTP endpoint (cluster-internal)"
  value       = "http://nessie-${var.environment}.${var.namespace}.svc.cluster.local:19120/iceberg"
}
