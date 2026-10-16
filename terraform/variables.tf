variable "region" {
  description = "AWS region for all resources."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Prefix used for resource names and tags."
  type        = string
  default     = "deskflow"
}

variable "environment" {
  description = "Environment tag (dev, staging, prod)."
  type        = string
  default     = "dev"
}

# ---------------------------------------------------------------- network

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones (one public + one private subnet in each)."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "EKS needs subnets in at least two AZs; use 2 or 3."
  }
}

# ---------------------------------------------------------------- cluster

variable "cluster_version" {
  description = "Kubernetes version. Pick one in EKS *standard* support to avoid extended-support fees."
  type        = string
  default     = "1.35"
}

variable "node_instance_types" {
  description = "Instance types for the managed node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Desired worker nodes. 3 × t3.medium fits the app + Prometheus/Grafana + ingress."
  type        = number
  default     = 3
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 4
}

variable "cluster_admin_arns" {
  description = "Extra IAM user/role ARNs to grant cluster-admin (the identity running terraform is always admin)."
  type        = list(string)
  default     = []
}

# ---------------------------------------------------------------- CI/CD

variable "github_repository" {
  description = "GitHub repo allowed to deploy via OIDC, as \"owner/repo\". Empty disables the deploy role."
  type        = string
  default     = ""
}

variable "create_github_oidc_provider" {
  description = "Create the GitHub OIDC identity provider. Set false if your AWS account already has one."
  type        = bool
  default     = true
}
