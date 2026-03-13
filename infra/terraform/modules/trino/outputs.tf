# Trino Module Outputs

output "endpoint" {
  description = "Trino coordinator HTTPS endpoint"
  value       = "https://trino.${var.environment}.lakehouse.internal:8443"
}

output "coordinator_service" {
  description = "Trino coordinator Kubernetes service name"
  value       = "trino-${var.environment}.${var.namespace}.svc.cluster.local"
}
