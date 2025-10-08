# Environment-specific configuration for Development
environment = "development"
region     = "us-west-2"

# Networking
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-west-2a", "us-west-2b"]

# EKS Configuration
eks_cluster_version = "1.28"
node_group_instance_types = ["t3.medium"]
node_group_desired_size = 2
node_group_max_size = 5
node_group_min_size = 1

# Database Configuration
db_instance_class = "db.t3.micro"
db_allocated_storage = 20
db_max_allocated_storage = 100
db_backup_retention_period = 7
db_backup_window = "03:00-04:00"
db_maintenance_window = "sun:04:00-sun:05:00"
db_deletion_protection = false

# Redis Configuration
redis_node_type = "cache.t3.micro"
redis_num_cache_nodes = 1
redis_parameter_group_name = "default.redis7"
redis_engine_version = "7.0"

# Application Configuration
app_name = "evently"
app_version = "latest"
api_replica_count = 2
worker_replica_count = 2

# Monitoring
enable_monitoring = true
prometheus_retention_days = 7

# Security
enable_waf = false  # Disabled for development
ssl_certificate_arn = ""  # Use self-signed for development

# Scaling
enable_autoscaling = true
cpu_threshold = 70
memory_threshold = 80

# Logging
cloudwatch_log_retention_days = 7

# Tags
tags = {
  Environment = "development"
  Project     = "evently"
  Owner       = "development-team"
  CostCenter  = "dev"
}
