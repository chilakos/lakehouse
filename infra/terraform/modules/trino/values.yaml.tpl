# Trino Helm Values - ${environment} environment
# Managed by Terraform -- do not edit manually

server:
  workers: ${workers}

  coordinatorExtraConfig: |
    http-server.https.enabled=true
    http-server.https.port=8443
    http-server.https.keystore.path=${tls_keystore_path}
    http-server.https.keystore.key=${tls_keystore_pass}

  config:
    query:
      maxMemory: "${worker_memory}"
      maxMemoryPerNode: "${coordinator_memory}"

  jvm:
    maxHeapSize: "${coordinator_memory}"
    gcMethod:
      type: "UseG1GC"
      g1:
        heapRegionSize: "32M"

# Iceberg catalog via REST catalog type pointing to Nessie
additionalCatalogs:
  iceberg: |
    connector.name=iceberg
    iceberg.catalog.type=rest
    iceberg.rest-catalog.uri=${nessie_endpoint}
    iceberg.rest-catalog.prefix=main
    iceberg.rest-catalog.warehouse=lakehouse

# LDAP authentication (SEC-01, SEC-02)
%{ if ldap_url != "" }
serverConfig:
  authenticationType: "PASSWORD"

additionalConfigFiles:
  password-authenticator.properties: |
    password-authenticator.name=ldap
    ldap.url=${ldap_url}
    ldap.user-bind-pattern=${ldap_user_bind}
    ldap.user-base-dn=${ldap_user_base_dn}
    ldap.ssl.truststore.path=/tls/truststore.jks
%{ endif }

# File-based access control
accessControl:
  type: "configFile"
  refreshPeriod: "60s"
  configFile: "/etc/trino/access-control/rules.json"

# TLS certificate volume mounts
extraVolumes:
  - name: tls-certs
    secret:
      secretName: "trino-tls-${environment}"
  - name: access-rules
    configMap:
      name: "trino-access-rules-${environment}"

extraVolumeMounts:
  - name: tls-certs
    mountPath: "/tls"
    readOnly: true
  - name: access-rules
    mountPath: "/etc/trino/access-control"
    readOnly: true

# Coordinator resources
coordinator:
  resources:
    requests:
      memory: "${coordinator_memory}"
      cpu: "1000m"
    limits:
      memory: "${coordinator_memory}"
      cpu: "4000m"

# Worker resources
worker:
  resources:
    requests:
      memory: "${worker_memory}"
      cpu: "2000m"
    limits:
      memory: "${worker_memory}"
      cpu: "8000m"

# Service configuration
service:
  type: ClusterIP
  port: 8443
