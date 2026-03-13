# S3 Module Outputs

output "bucket_name" {
  description = "Name of the S3 bucket for Iceberg data"
  value       = aws_s3_bucket.lakehouse_data.id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket for Iceberg data"
  value       = aws_s3_bucket.lakehouse_data.arn
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for S3 encryption"
  value       = aws_kms_key.s3_encryption.arn
}

output "kms_key_id" {
  description = "ID of the KMS key used for S3 encryption"
  value       = aws_kms_key.s3_encryption.key_id
}

output "iam_policy_arn" {
  description = "ARN of the IAM policy granting access to the S3 bucket and KMS key"
  value       = aws_iam_policy.lakehouse_data_access.arn
}
