# Networking Module Outputs

output "nessie_sg_id" {
  description = "Security group ID for Nessie catalog service"
  value       = aws_security_group.nessie.id
}

output "trino_sg_id" {
  description = "Security group ID for Trino query engine"
  value       = aws_security_group.trino.id
}

output "postgres_sg_id" {
  description = "Security group ID for PostgreSQL (Nessie metadata store)"
  value       = aws_security_group.postgres.id
}
