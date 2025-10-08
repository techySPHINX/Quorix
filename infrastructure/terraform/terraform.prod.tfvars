# Production Environment Configuration
environment = "production"
aws_region  = "us-west-2"

# VPC Configuration
vpc_cidr                = "10.0.0.0/16"
private_subnet_cidrs    = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnet_cidrs     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
database_subnet_cidrs   = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]
cache_subnet_cidrs      = ["10.0.251.0/24", "10.0.252.0/24", "10.0.253.0/24"]

# Database Configuration (production-ready)
db_instance_class           = "db.r6g.xlarge"
db_allocated_storage        = 500
db_max_allocated_storage    = 2000
db_backup_retention_period  = 30

# Redis Configuration (production-ready)
redis_node_type        = "cache.r6g.xlarge"
redis_num_cache_nodes  = 3

# EKS Configuration (production-ready)
eks_cluster_version       = "1.28"
eks_node_instance_types   = ["m5.xlarge", "m5.2xlarge"]
eks_node_min_size        = 3
eks_node_max_size        = 20
eks_node_desired_size    = 6

# Application Configuration
min_replicas              = 3
max_replicas              = 50
target_cpu_utilization   = 70

# Monitoring and Logging
log_retention_days = 90
enable_monitoring  = true
enable_logging     = true
enable_alerting    = true

# Security
enable_waf = true

# Cost Optimization
enable_spot_instances     = true
spot_instance_percentage  = 30

# Domain Configuration
domain_name           = "evently.yourdomain.com"
create_route53_zone   = true

# Feature Flags
feature_flags = {
  enable_blue_green_deployment = true
  enable_canary_deployment     = true
  enable_chaos_engineering     = false
  enable_cost_optimization     = true
  enable_security_scanning     = true
}

# Environment-specific overrides
environment_config = {
  log_retention_days = 90
}
