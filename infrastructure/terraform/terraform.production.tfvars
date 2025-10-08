# Environment-specific configuration for Production
environment = "production"
region     = "us-west-2"

# Networking
vpc_cidr = "10.1.0.0/16"
availability_zones = ["us-west-2a", "us-west-2b", "us-west-2c"]

# EKS Configuration
eks_cluster_version = "1.28"
node_group_instance_types = ["t3.large", "t3.xlarge"]
node_group_desired_size = 3
node_group_max_size = 10
node_group_min_size = 3

# Database Configuration
db_instance_class = "db.r6g.large"
db_allocated_storage = 100
db_max_allocated_storage = 1000
db_backup_retention_period = 30
db_backup_window = "03:00-04:00"
db_maintenance_window = "sun:04:00-sun:05:00"
db_deletion_protection = true

# Redis Configuration
redis_node_type = "cache.r6g.large"
redis_num_cache_nodes = 2
redis_parameter_group_name = "default.redis7"
redis_engine_version = "7.0"

# Application Configuration
app_name = "evently"
app_version = "v1.0.0"
api_replica_count = 5
worker_replica_count = 3

# Monitoring
enable_monitoring = true
prometheus_retention_days = 30

# Security
enable_waf = true
ssl_certificate_arn = "arn:aws:acm:us-west-2:ACCOUNT-ID:certificate/CERTIFICATE-ID"

# Scaling
enable_autoscaling = true
cpu_threshold = 60
memory_threshold = 70

# Logging
cloudwatch_log_retention_days = 90

# Tags
tags = {
  Environment = "production"
  Project     = "evently"
  Owner       = "platform-team"
  CostCenter  = "prod"
}
