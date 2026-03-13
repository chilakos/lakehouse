output "nessie_endpoint" {
  description = "Nessie catalog REST API endpoint"
  value       = module.nessie.endpoint
}

output "trino_endpoint" {
  description = "Trino query engine endpoint"
  value       = module.trino.endpoint
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket for Iceberg data lake storage"
  value       = module.s3.bucket_arn
}
