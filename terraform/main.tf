data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

locals {
  cluster_name = "${var.project_name}-eks"
  azs          = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ============================================================================
# VPC
#   10.0.0.0/16
#   ├── public  10.0.48.0/24, 10.0.49.0/24   → internet gateway (load balancers, NAT)
#   └── private 10.0.0.0/20,  10.0.16.0/20   → NAT gateway     (worker nodes, pods)
# ============================================================================
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.21"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  private_subnets = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets  = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, i + 48)]

  enable_nat_gateway   = true
  single_nat_gateway   = true # one NAT to keep classroom costs down (prod: one per AZ)
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Tags that tell Kubernetes where to place internet-facing / internal load balancers.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

# ============================================================================
# EKS cluster + managed node group
# ============================================================================
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.37"

  cluster_name    = local.cluster_name
  cluster_version = var.cluster_version

  # Public API endpoint so kubectl/GitHub Actions can reach it; nodes stay private.
  cluster_endpoint_public_access = true

  # Avoid surprise extended-support billing when a version ages out.
  cluster_upgrade_policy = {
    support_type = "STANDARD"
  }

  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_addons = {
    coredns    = {}
    kube-proxy = {}
    vpc-cni = {
      before_compute = true
    }
    eks-pod-identity-agent = {
      before_compute = true
    }
    # Needed for PersistentVolumeClaims (PostgreSQL data) backed by EBS.
    aws-ebs-csi-driver = {}
  }

  eks_managed_node_groups = {
    general = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      # Lets the EBS CSI driver (running on the nodes) create/attach volumes.
      iam_role_additional_policies = {
        AmazonEBSCSIDriverPolicy = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
      }

      labels = {
        workload = "general"
      }
    }
  }

  access_entries = merge(
    {
      for arn in var.cluster_admin_arns : replace(arn, "/[^a-zA-Z0-9]/", "-") => {
        principal_arn = arn
        policy_associations = {
          admin = {
            policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
            access_scope = { type = "cluster" }
          }
        }
      }
    },
    local.github_enabled ? {
      github-deploy = {
        principal_arn = aws_iam_role.github_deploy[0].arn
        policy_associations = {
          admin = {
            policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
            access_scope = { type = "cluster" }
          }
        }
      }
    } : {}
  )
}
