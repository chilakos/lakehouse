# Trino Module - Distributed SQL Query Engine Deployment via Helm
#
# Deploys Trino with:
# - HTTPS on coordinator (port 8443) with TLS keystore (SEC-06)
# - Iceberg catalog via REST catalog type pointing to Nessie
# - LDAP authentication for user access control
# - File-based access control rules (rules.json)
# - Configurable worker count per environment (full isolation)

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
# Trino Helm Release
# -----------------------------------------------------------------------------

resource "helm_release" "trino" {
  name       = "trino-${var.environment}"
  namespace  = var.namespace
  repository = "https://trinodb.github.io/charts"
  chart      = "trino"
  version    = var.trino_chart_version

  create_namespace = true
  wait             = true
  timeout          = 600

  values = [
    templatefile("${path.module}/values.yaml.tpl", {
      environment          = var.environment
      workers              = var.trino_workers
      coordinator_memory   = var.coordinator_memory
      worker_memory        = var.worker_memory
      nessie_endpoint      = var.nessie_endpoint
      ldap_url             = var.ldap_url
      ldap_user_bind       = var.ldap_user_bind_pattern
      ldap_user_base_dn    = var.ldap_user_base_dn
      tls_keystore_path    = var.tls_keystore_path
      tls_keystore_pass    = var.tls_keystore_password
      access_control_rules = var.access_control_rules
    })
  ]
}

# -----------------------------------------------------------------------------
# Trino Access Control ConfigMap
# -----------------------------------------------------------------------------

resource "kubernetes_config_map" "trino_access_rules" {
  metadata {
    name      = "trino-access-rules-${var.environment}"
    namespace = var.namespace

    labels = {
      "app.kubernetes.io/name"       = "trino"
      "app.kubernetes.io/component"  = "access-control"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  data = {
    "rules.json" = var.access_control_rules
  }
}

# -----------------------------------------------------------------------------
# Trino Resource Groups ConfigMap (ADR-004 — workload isolation)
# -----------------------------------------------------------------------------

resource "kubernetes_config_map" "trino_resource_groups" {
  metadata {
    name      = "trino-resource-groups-${var.environment}"
    namespace = var.namespace

    labels = {
      "app.kubernetes.io/name"       = "trino"
      "app.kubernetes.io/component"  = "resource-groups"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  data = {
    "resource-groups.properties" = "resource-groups.config-file=/etc/trino/resource-groups/rules.json"
    "rules.json"                 = var.resource_group_rules
  }
}

# -----------------------------------------------------------------------------
# cert-manager Certificate for Trino TLS (SEC-06)
# -----------------------------------------------------------------------------

resource "kubernetes_manifest" "trino_certificate" {
  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "Certificate"
    metadata = {
      name      = "trino-tls-${var.environment}"
      namespace = var.namespace
    }
    spec = {
      secretName = "trino-tls-${var.environment}"
      issuerRef = {
        name = "letsencrypt-${var.environment}"
        kind = "ClusterIssuer"
      }
      dnsNames = [
        "trino.${var.environment}.lakehouse.internal",
        "trino-${var.environment}.${var.namespace}.svc.cluster.local",
      ]
      keystores = {
        jks = {
          create = true
          passwordSecretRef = {
            name = "trino-keystore-password-${var.environment}"
            key  = "password"
          }
        }
      }
    }
  }
}
