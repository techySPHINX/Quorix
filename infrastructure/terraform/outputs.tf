# Terraform Outputs for Evently Infrastructure

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

output "database_subnets" {
  description = "List of IDs of database subnets"
  value       = module.vpc.database_subnets
}

# EKS Outputs
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ids attached to the cluster control plane"
  value       = module.eks.cluster_security_group_id
}

output "cluster_iam_role_name" {
  description = "IAM role name associated with EKS cluster"
  value       = module.eks.cluster_iam_role_name
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.cluster_certificate_authority_data
}

output "cluster_primary_security_group_id" {
  description = "Cluster security group that was created by Amazon EKS for the cluster"
  value       = module.eks.cluster_primary_security_group_id
}

output "node_groups" {
  description = "EKS node groups"
  value       = module.eks.eks_managed_node_groups
}

output "oidc_provider_arn" {
  description = "The ARN of the OIDC Provider if one is created"
  value       = module.eks.oidc_provider_arn
}

# Database Outputs
output "db_instance_address" {
  description = "RDS instance hostname"
  value       = aws_db_instance.evently.address
  sensitive   = true
}

output "db_instance_arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.evently.arn
}

output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.evently.endpoint
  sensitive   = true
}

output "db_instance_hosted_zone_id" {
  description = "RDS instance hosted zone ID"
  value       = aws_db_instance.evently.hosted_zone_id
}

output "db_instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.evently.id
}

output "db_instance_resource_id" {
  description = "RDS instance resource ID"
  value       = aws_db_instance.evently.resource_id
}

output "db_instance_status" {
  description = "RDS instance status"
  value       = aws_db_instance.evently.status
}

output "db_instance_name" {
  description = "RDS instance name"
  value       = aws_db_instance.evently.db_name
}

output "db_instance_username" {
  description = "RDS instance root username"
  value       = aws_db_instance.evently.username
  sensitive   = true
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = aws_db_instance.evently.port
}

# Redis Outputs
output "redis_cluster_address" {
  description = "Redis cluster address"
  value       = aws_elasticache_replication_group.evently.primary_endpoint_address
  sensitive   = true
}

output "redis_cluster_id" {
  description = "Redis cluster ID"
  value       = aws_elasticache_replication_group.evently.id
}

output "redis_cluster_port" {
  description = "Redis cluster port"
  value       = aws_elasticache_replication_group.evently.port
}

output "redis_cluster_reader_endpoint_address" {
  description = "Redis cluster reader endpoint"
  value       = aws_elasticache_replication_group.evently.reader_endpoint_address
  sensitive   = true
}

# Load Balancer Outputs
output "load_balancer_arn" {
  description = "Load balancer ARN"
  value       = aws_lb.evently.arn
}

output "load_balancer_dns_name" {
  description = "Load balancer DNS name"
  value       = aws_lb.evently.dns_name
}

output "load_balancer_hosted_zone_id" {
  description = "Load balancer hosted zone ID"
  value       = aws_lb.evently.zone_id
}

# Certificate Outputs
output "acm_certificate_arn" {
  description = "ARN of the certificate"
  value       = var.domain_name != "" ? aws_acm_certificate.evently[0].arn : null
}

output "acm_certificate_domain_validation_options" {
  description = "Certificate domain validation options"
  value       = var.domain_name != "" ? aws_acm_certificate.evently[0].domain_validation_options : null
}

# Route53 Outputs
output "route53_zone_arn" {
  description = "Route53 zone ARN"
  value       = var.create_route53_zone && var.domain_name != "" ? aws_route53_zone.evently[0].arn : null
}

output "route53_zone_id" {
  description = "Route53 zone ID"
  value       = var.create_route53_zone && var.domain_name != "" ? aws_route53_zone.evently[0].zone_id : null
}

output "route53_name_servers" {
  description = "Route53 name servers"
  value       = var.create_route53_zone && var.domain_name != "" ? aws_route53_zone.evently[0].name_servers : null
}

# S3 Outputs
output "s3_bucket_id" {
  description = "S3 bucket ID"
  value       = aws_s3_bucket.evently_assets.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.evently_assets.arn
}

output "s3_bucket_domain_name" {
  description = "S3 bucket domain name"
  value       = aws_s3_bucket.evently_assets.bucket_domain_name
}

output "s3_bucket_regional_domain_name" {
  description = "S3 bucket regional domain name"
  value       = aws_s3_bucket.evently_assets.bucket_regional_domain_name
}

# CloudWatch Outputs
output "cloudwatch_log_group_arn" {
  description = "CloudWatch log group ARN"
  value       = aws_cloudwatch_log_group.evently.arn
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.evently.name
}

# Security Group Outputs
output "security_group_alb_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "security_group_eks_cluster_id" {
  description = "EKS cluster security group ID"
  value       = aws_security_group.eks_cluster.id
}

output "security_group_rds_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "security_group_redis_id" {
  description = "Redis security group ID"
  value       = aws_security_group.redis.id
}

# IAM Outputs
output "eks_admin_role_arn" {
  description = "EKS admin role ARN"
  value       = aws_iam_role.eks_admin.arn
}

output "rds_monitoring_role_arn" {
  description = "RDS monitoring role ARN"
  value       = aws_iam_role.rds_monitoring.arn
}

# Parameter Store Outputs
output "ssm_parameter_db_password_name" {
  description = "SSM parameter name for database password"
  value       = aws_ssm_parameter.db_password.name
}

output "ssm_parameter_redis_auth_token_name" {
  description = "SSM parameter name for Redis auth token"
  value       = aws_ssm_parameter.redis_auth_token.name
}

output "ssm_parameter_secret_key_name" {
  description = "SSM parameter name for application secret key"
  value       = aws_ssm_parameter.secret_key.name
}

# Connection Information
output "connection_info" {
  description = "Connection information for applications"
  value = {
    database = {
      host     = aws_db_instance.evently.address
      port     = aws_db_instance.evently.port
      name     = aws_db_instance.evently.db_name
      username = aws_db_instance.evently.username
    }
    redis = {
      host = aws_elasticache_replication_group.evently.primary_endpoint_address
      port = aws_elasticache_replication_group.evently.port
    }
    kubernetes = {
      cluster_name     = module.eks.cluster_id
      cluster_endpoint = module.eks.cluster_endpoint
      cluster_ca_cert  = module.eks.cluster_certificate_authority_data
    }
    load_balancer = {
      dns_name = aws_lb.evently.dns_name
      zone_id  = aws_lb.evently.zone_id
    }
  }
  sensitive = true
}

# Environment Information
output "environment_info" {
  description = "Environment configuration information"
  value = {
    environment     = var.environment
    project_name    = var.project_name
    aws_region      = var.aws_region
    vpc_cidr        = var.vpc_cidr
    domain_name     = var.domain_name
    timestamp       = timestamp()
  }
}

# Resource Counts
output "resource_summary" {
  description = "Summary of created resources"
  value = {
    vpc_subnets = {
      private  = length(module.vpc.private_subnets)
      public   = length(module.vpc.public_subnets)
      database = length(module.vpc.database_subnets)
    }
    eks = {
      cluster_version = var.eks_cluster_version
      node_groups     = length(module.eks.eks_managed_node_groups)
    }
    database = {
      engine         = aws_db_instance.evently.engine
      engine_version = aws_db_instance.evently.engine_version
      instance_class = aws_db_instance.evently.instance_class
    }
    redis = {
      engine_version    = aws_elasticache_replication_group.evently.engine_version
      node_type        = aws_elasticache_replication_group.evently.node_type
      num_cache_clusters = aws_elasticache_replication_group.evently.num_cache_clusters
    }
  }
}
