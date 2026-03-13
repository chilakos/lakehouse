# MinIO Module - On-Prem S3-Compatible Storage Configuration
#
# This module does NOT deploy MinIO (the team already operates it).
# It configures buckets via the mc CLI and creates Kubernetes secrets
# for Nessie and Trino to consume MinIO credentials.

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

# -----------------------------------------------------------------------------
# MinIO Bucket Configuration via mc CLI
# -----------------------------------------------------------------------------

resource "null_resource" "minio_buckets" {
  for_each = toset(var.bucket_names)

  triggers = {
    bucket   = each.value
    endpoint = var.minio_endpoint
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Configure mc alias for MinIO
      mc alias set lakehouse ${var.minio_endpoint} ${var.minio_access_key} ${var.minio_secret_key} --api S3v4

      # Create bucket if it doesn't exist
      mc mb --ignore-existing lakehouse/${each.value}

      # Enable versioning on the bucket
      mc version enable lakehouse/${each.value}

      # Set encryption policy (SSE-S3 for on-prem MinIO)
      mc encrypt set sse-s3 lakehouse/${each.value}
    EOT
  }
}

# -----------------------------------------------------------------------------
# Kubernetes Secret for MinIO Credentials
# -----------------------------------------------------------------------------

resource "kubernetes_secret" "minio_credentials" {
  metadata {
    name      = "minio-credentials"
    namespace = var.namespace

    labels = {
      "app.kubernetes.io/name"       = "minio"
      "app.kubernetes.io/component"  = "storage"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  data = {
    MINIO_ENDPOINT   = var.minio_endpoint
    MINIO_ACCESS_KEY = var.minio_access_key
    MINIO_SECRET_KEY = var.minio_secret_key
  }

  type = "Opaque"
}
