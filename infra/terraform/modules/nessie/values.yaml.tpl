# Nessie Helm Values - ${environment} environment
# Managed by Terraform -- do not edit manually

replicaCount: ${replicas}

# Version store configuration - JDBC with PostgreSQL
versionStoreType: JDBC

catalog:
  storage:
    # S3 warehouse (cloud)
    s3:
      defaultWarehouse: "s3://${s3_bucket}/warehouse"
      region: "${s3_region}"
    # MinIO warehouse (on-prem)
    %{ if minio_endpoint != "" }
    s3Named:
      onprem:
        endpoint: "${minio_endpoint}"
        region: "us-east-1"
        pathStyleAccess: true
        defaultWarehouse: "s3://${minio_bucket}/warehouse"
    %{ endif }

# PostgreSQL backend for Nessie metadata
jdbc:
  url: "jdbc:postgresql://nessie-postgresql-${environment}:5432/nessie"
  username: "nessie"
  password: "${db_password}"

postgresql:
  enabled: true
  auth:
    username: "nessie"
    password: "${db_password}"
    database: "nessie"
  primary:
    persistence:
      size: "10Gi"

# Quarkus TLS configuration (SEC-06: Encryption in Transit)
quarkus:
  http:
    ssl-port: 19120
    ssl:
      certificate:
        key-store-file: "/tls/tls.key"
        key-store-file-type: "PEM"
      certificate-files: "/tls/tls.crt"
      key-files: "/tls/tls.key"

# TLS certificate volume mount
extraVolumes:
  - name: tls-certs
    secret:
      secretName: "${tls_secret}"

extraVolumeMounts:
  - name: tls-certs
    mountPath: "/tls"
    readOnly: true

# Resource configuration
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"

# Health checks
livenessProbe:
  httpGet:
    path: /q/health/live
    port: 19120
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /q/health/ready
    port: 19120
  initialDelaySeconds: 15
  periodSeconds: 5

# Service configuration
service:
  type: ClusterIP
  port: 19120

# Pod disruption budget for HA
podDisruptionBudget:
  enabled: true
  minAvailable: 1
