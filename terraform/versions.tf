terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.95, < 6.0"
    }
  }

  # State is stored locally by default (fine for a single-person project).
  # For a team, use a remote backend instead — create the bucket first, then:
  #
  # backend "s3" {
  #   bucket       = "<your-unique-tfstate-bucket>"
  #   key          = "deskflow/terraform.tfstate"
  #   region       = "ap-southeast-2"
  #   use_lockfile = true
  #   encrypt      = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}
