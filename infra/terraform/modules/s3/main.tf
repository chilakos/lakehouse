# S3 Storage Module - Iceberg Data Lake Buckets with SSE-KMS Encryption
#
# Provides encrypted S3 storage for Iceberg table data with KMS key rotation,
# versioning, public access blocking, and IAM policies for Nessie/Trino access.

# -----------------------------------------------------------------------------
# KMS Key for S3 Encryption (SEC-05: Encryption at Rest)
# -----------------------------------------------------------------------------

resource "aws_kms_key" "s3_encryption" {
  description             = "KMS key for lakehouse S3 bucket encryption (${var.environment})"
  enable_key_rotation     = true
  deletion_window_in_days = var.kms_key_deletion_window

  tags = merge(var.tags, {
    Name    = "lakehouse-s3-kms-${var.environment}"
    Purpose = "s3-encryption"
  })
}

resource "aws_kms_alias" "s3_encryption" {
  name          = "alias/lakehouse-s3-${var.environment}"
  target_key_id = aws_kms_key.s3_encryption.key_id
}

# -----------------------------------------------------------------------------
# S3 Bucket for Iceberg Data
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "lakehouse_data" {
  bucket = "${var.bucket_name_prefix}-${var.environment}-data"

  tags = merge(var.tags, {
    Name        = "${var.bucket_name_prefix}-${var.environment}-data"
    Environment = var.environment
    Purpose     = "iceberg-data-lake"
  })
}

# SSE-KMS encryption configuration (SEC-05)
resource "aws_s3_bucket_server_side_encryption_configuration" "lakehouse_data" {
  bucket = aws_s3_bucket.lakehouse_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_encryption.arn
    }
    bucket_key_enabled = true
  }
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "lakehouse_data" {
  bucket = aws_s3_bucket.lakehouse_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "lakehouse_data" {
  bucket = aws_s3_bucket.lakehouse_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rule: clean up incomplete multipart uploads
resource "aws_s3_bucket_lifecycle_configuration" "lakehouse_data" {
  bucket = aws_s3_bucket.lakehouse_data.id

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# -----------------------------------------------------------------------------
# IAM Policy for Nessie and Trino Service Accounts
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "lakehouse_data_access" {
  statement {
    sid    = "AllowListBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [aws_s3_bucket.lakehouse_data.arn]
  }

  statement {
    sid    = "AllowObjectOperations"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:GetObjectVersion",
    ]
    resources = ["${aws_s3_bucket.lakehouse_data.arn}/*"]
  }

  statement {
    sid    = "AllowKMSDecrypt"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = [aws_kms_key.s3_encryption.arn]
  }
}

resource "aws_iam_policy" "lakehouse_data_access" {
  name        = "lakehouse-data-access-${var.environment}"
  description = "Allow Nessie and Trino to access lakehouse S3 bucket and KMS key (${var.environment})"
  policy      = data.aws_iam_policy_document.lakehouse_data_access.json

  tags = merge(var.tags, {
    Environment = var.environment
  })
}
