# Development Environment Configuration
environment = "development"
aws_region  = "us-west-2"

# VPC Configuration
vpc_cidr                = "10.0.0.0/16"
private_subnet_cidrs    = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnet_cidrs     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
database_subnet_cidrs   = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]
cache_subnet_cidrs      = ["10.0.251.0/24", "10.0.252.0/24", "10.0.253.0/24"]

# Database Configuration (smaller for dev)
db_instance_class           = "db.t3.micro"
db_allocated_storage        = 20
db_max_allocated_storage    = 100
db_backup_retention_period  = 1

# Redis Configuration (smaller for dev)
redis_node_type        = "cache.t3.micro"
redis_num_cache_nodes  = 1

# EKS Configuration (smaller for dev)
eks_cluster_version       = "1.28"
eks_node_instance_types   = ["t3.small"]
eks_node_min_size        = 1
eks_node_max_size        = 3
eks_node_desired_size    = 2

# Application Configuration
min_replicas              = 1
max_replicas              = 5
target_cpu_utilization   = 80

# Monitoring and Logging
log_retention_days = 7
enable_monitoring  = true
enable_logging     = true
enable_alerting    = false

# Security
enable_waf = false

# Cost Optimization
enable_spot_instances     = false
spot_instance_percentage  = 0

# Feature Flags
feature_flags = {
  enable_blue_green_deployment = false
  enable_canary_deployment     = false
  enable_chaos_engineering     = false
  enable_cost_optimization     = true
  enable_security_scanning     = false
}
