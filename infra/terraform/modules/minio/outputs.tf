# MinIO Module Outputs

output "minio_endpoint" {
  description = "MinIO server endpoint URL"
  value       = var.minio_endpoint
}

output "bucket_names" {
  description = "List of configured MinIO bucket names"
  value       = var.bucket_names
}

output "credentials_secret_name" {
  description = "Name of the Kubernetes secret containing MinIO credentials"
  value       = kubernetes_secret.minio_credentials.metadata[0].name
}
