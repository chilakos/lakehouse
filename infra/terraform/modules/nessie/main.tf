# Nessie Catalog Module - Iceberg REST Catalog Deployment via Helm
#
# Deploys Nessie as the centralized Iceberg REST catalog with:
# - PostgreSQL backend for metadata storage (JDBC)
# - TLS/HTTPS on the API endpoint via cert-manager (SEC-06)
# - Configurable replicas per environment (full isolation)
# - S3 and MinIO warehouse configuration

terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

# -----------------------------------------------------------------------------
# Nessie Helm Release
# -----------------------------------------------------------------------------

resource "helm_release" "nessie" {
  name       = "nessie-${var.environment}"
  namespace  = var.namespace
  repository = "https://charts.projectnessie.org"
  chart      = "nessie"
  version    = var.nessie_chart_version

  create_namespace = true
  wait             = true
  timeout          = 600

  values = [
    templatefile("${path.module}/values.yaml.tpl", {
      environment    = var.environment
      replicas       = var.nessie_replicas
      db_password    = var.nessie_db_password
      s3_bucket      = var.s3_bucket
      s3_region      = var.s3_region
      minio_endpoint = var.minio_endpoint
      minio_bucket   = var.minio_bucket
      tls_secret     = var.tls_secret_name
    })
  ]
}

# -----------------------------------------------------------------------------
# cert-manager Certificate for Nessie TLS (SEC-06)
# -----------------------------------------------------------------------------

resource "kubernetes_manifest" "nessie_certificate" {
  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "Certificate"
    metadata = {
      name      = "nessie-tls-${var.environment}"
      namespace = var.namespace
    }
    spec = {
      secretName = var.tls_secret_name
      issuerRef = {
        name = "letsencrypt-${var.environment}"
        kind = "ClusterIssuer"
      }
      dnsNames = [
        "nessie.${var.environment}.lakehouse.internal",
        "nessie-${var.environment}.${var.namespace}.svc.cluster.local",
      ]
    }
  }
}
