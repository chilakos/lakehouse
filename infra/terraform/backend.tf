terraform {
  required_version = ">= 1.7.0"

  # Backend configuration uses partial configuration.
  # Actual values are provided via -backend-config flags or .tfbackend files
  # per environment (e.g., terraform init -backend-config=environments/dev/backend.tfbackend).
  backend "s3" {
    # bucket         = "lakehouse-terraform-state"
    # key            = "lakehouse/dev/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "lakehouse-terraform-locks"
    encrypt = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}
