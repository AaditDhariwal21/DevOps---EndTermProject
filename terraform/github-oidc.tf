# ============================================================================
# GitHub Actions → AWS without stored access keys.
#
# GitHub issues a short-lived OIDC token to the workflow; AWS trusts it only for
# this repository's main branch / production environment and hands back
# temporary credentials for the deploy role, which is cluster-admin on EKS.
# ============================================================================

locals {
  github_enabled  = var.github_repository != ""
  github_oidc_url = "token.actions.githubusercontent.com"
  github_oidc_arn = local.github_enabled ? (
    var.create_github_oidc_provider
    ? aws_iam_openid_connect_provider.github[0].arn
    : data.aws_iam_openid_connect_provider.github[0].arn
  ) : null
}

resource "aws_iam_openid_connect_provider" "github" {
  count = local.github_enabled && var.create_github_oidc_provider ? 1 : 0

  url            = "https://${local.github_oidc_url}"
  client_id_list = ["sts.amazonaws.com"]
  # AWS validates GitHub's certificate itself; thumbprints are kept for older provider versions.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

data "aws_iam_openid_connect_provider" "github" {
  count = local.github_enabled && !var.create_github_oidc_provider ? 1 : 0
  url   = "https://${local.github_oidc_url}"
}

data "aws_iam_policy_document" "github_assume" {
  count = local.github_enabled ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc_url}:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Only the main branch, or jobs bound to the "production" environment, may deploy.
    condition {
      test     = "StringLike"
      variable = "${local.github_oidc_url}:sub"
      values = [
        "repo:${var.github_repository}:ref:refs/heads/main",
        "repo:${var.github_repository}:environment:production",
      ]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  count = local.github_enabled ? 1 : 0

  name               = "${var.project_name}-github-deploy"
  description        = "Assumed by GitHub Actions (${var.github_repository}) to deploy to EKS"
  assume_role_policy = data.aws_iam_policy_document.github_assume[0].json
}

# Just enough AWS API access for `aws eks update-kubeconfig`; Kubernetes
# permissions come from the EKS access entry in main.tf.
resource "aws_iam_role_policy" "github_deploy_eks" {
  count = local.github_enabled ? 1 : 0

  name = "describe-eks-cluster"
  role = aws_iam_role.github_deploy[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["eks:DescribeCluster"]
      Resource = module.eks.cluster_arn
    }]
  })
}
