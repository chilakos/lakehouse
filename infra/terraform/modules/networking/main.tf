# Networking Module - Security Groups for Lakehouse Services
#
# Defines least-privilege security groups for Nessie, Trino, and PostgreSQL
# with controlled ingress/egress rules for service-to-service communication.
#
# Cross-SG references use standalone aws_security_group_rule resources
# to avoid circular dependency between security groups.

# -----------------------------------------------------------------------------
# Nessie Security Group
# -----------------------------------------------------------------------------

resource "aws_security_group" "nessie" {
  name_prefix = "lakehouse-nessie-${var.environment}-"
  description = "Security group for Nessie catalog service (${var.environment})"
  vpc_id      = var.vpc_id

  # Nessie API (19120) from authorized CIDRs (ETL workloads)
  ingress {
    description = "Nessie REST API from authorized CIDRs (ETL workloads)"
    from_port   = 19120
    to_port     = 19120
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  # HTTPS outbound for S3 access
  egress {
    description = "HTTPS outbound for S3 and external services"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # MinIO access for on-prem storage
  egress {
    description = "MinIO on-prem storage"
    from_port   = 9000
    to_port     = 9000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  tags = merge(var.tags, {
    Name        = "lakehouse-nessie-${var.environment}"
    Environment = var.environment
    Service     = "nessie"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Nessie ingress from Trino (cross-SG, standalone rule to avoid cycle)
resource "aws_security_group_rule" "nessie_from_trino" {
  type                     = "ingress"
  description              = "Nessie REST API from Trino"
  from_port                = 19120
  to_port                  = 19120
  protocol                 = "tcp"
  security_group_id        = aws_security_group.nessie.id
  source_security_group_id = aws_security_group.trino.id
}

# Nessie egress to PostgreSQL (cross-SG, standalone rule to avoid cycle)
resource "aws_security_group_rule" "nessie_to_postgres" {
  type                     = "egress"
  description              = "PostgreSQL for Nessie metadata"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.nessie.id
  source_security_group_id = aws_security_group.postgres.id
}

# -----------------------------------------------------------------------------
# Trino Security Group
# -----------------------------------------------------------------------------

resource "aws_security_group" "trino" {
  name_prefix = "lakehouse-trino-${var.environment}-"
  description = "Security group for Trino query engine (${var.environment})"
  vpc_id      = var.vpc_id

  # Trino coordinator HTTPS (8443) from authorized CIDRs
  ingress {
    description = "Trino coordinator HTTPS from authorized CIDRs"
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  # HTTPS outbound for S3 access
  egress {
    description = "HTTPS outbound for S3 and external services"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # MinIO access for on-prem storage
  egress {
    description = "MinIO on-prem storage"
    from_port   = 9000
    to_port     = 9000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  tags = merge(var.tags, {
    Name        = "lakehouse-trino-${var.environment}"
    Environment = var.environment
    Service     = "trino"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Trino egress to Nessie (cross-SG, standalone rule to avoid cycle)
resource "aws_security_group_rule" "trino_to_nessie" {
  type                     = "egress"
  description              = "Nessie catalog API"
  from_port                = 19120
  to_port                  = 19120
  protocol                 = "tcp"
  security_group_id        = aws_security_group.trino.id
  source_security_group_id = aws_security_group.nessie.id
}

# -----------------------------------------------------------------------------
# PostgreSQL Security Group (Nessie metadata backing store)
# -----------------------------------------------------------------------------

resource "aws_security_group" "postgres" {
  name_prefix = "lakehouse-postgres-${var.environment}-"
  description = "Security group for PostgreSQL (Nessie metadata) (${var.environment})"
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name        = "lakehouse-postgres-${var.environment}"
    Environment = var.environment
    Service     = "postgresql"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# PostgreSQL ingress from Nessie (cross-SG, standalone rule to avoid cycle)
resource "aws_security_group_rule" "postgres_from_nessie" {
  type                     = "ingress"
  description              = "PostgreSQL from Nessie"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.postgres.id
  source_security_group_id = aws_security_group.nessie.id
}
