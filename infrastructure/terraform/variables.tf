# Terraform Variables for Evently Infrastructure

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "development"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "evently"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "database_subnet_cidrs" {
  description = "Database subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]
}

variable "cache_subnet_cidrs" {
  description = "Cache subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.251.0/24", "10.0.252.0/24", "10.0.253.0/24"]
}

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "RDS max allocated storage in GB"
  type        = number
  default     = 1000
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "evently"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "evently_user"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_backup_retention_period" {
  description = "Database backup retention period in days"
  type        = number
  default     = 7
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 2
}

variable "redis_auth_token" {
  description = "Redis AUTH token"
  type        = string
  sensitive   = true
}

# EKS Configuration
variable "eks_cluster_version" {
  description = "EKS cluster version"
  type        = string
  default     = "1.28"
}

variable "eks_node_instance_types" {
  description = "EKS node instance types"
  type        = list(string)
  default     = ["t3.large"]
}

variable "eks_node_min_size" {
  description = "EKS node group minimum size"
  type        = number
  default     = 2
}

variable "eks_node_max_size" {
  description = "EKS node group maximum size"
  type        = number
  default     = 10
}

variable "eks_node_desired_size" {
  description = "EKS node group desired size"
  type        = number
  default     = 3
}

# Domain Configuration
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

variable "create_route53_zone" {
  description = "Whether to create Route53 hosted zone"
  type        = bool
  default     = false
}

# Application Configuration
variable "app_secret_key" {
  description = "Application secret key"
  type        = string
  sensitive   = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable comprehensive monitoring stack"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Enable centralized logging"
  type        = bool
  default     = true
}

variable "enable_alerting" {
  description = "Enable alerting and notifications"
  type        = bool
  default     = true
}

# Backup Configuration
variable "enable_automated_backups" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_schedule" {
  description = "Backup schedule (cron expression)"
  type        = string
  default     = "0 2 * * *"  # Daily at 2 AM
}

# Security Configuration
variable "enable_waf" {
  description = "Enable AWS WAF"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Scaling Configuration
variable "enable_autoscaling" {
  description = "Enable auto-scaling"
  type        = bool
  default     = true
}

variable "min_replicas" {
  description = "Minimum number of application replicas"
  type        = number
  default     = 2
}

variable "max_replicas" {
  description = "Maximum number of application replicas"
  type        = number
  default     = 20
}

variable "target_cpu_utilization" {
  description = "Target CPU utilization for auto-scaling"
  type        = number
  default     = 70
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization"
  type        = bool
  default     = false
}

variable "spot_instance_percentage" {
  description = "Percentage of spot instances (0-100)"
  type        = number
  default     = 30
  
  validation {
    condition     = var.spot_instance_percentage >= 0 && var.spot_instance_percentage <= 100
    error_message = "Spot instance percentage must be between 0 and 100."
  }
}

# Environment-specific overrides
variable "environment_config" {
  description = "Environment-specific configuration overrides"
  type = object({
    db_instance_class    = optional(string)
    redis_node_type     = optional(string)
    eks_node_instance_types = optional(list(string))
    min_replicas        = optional(number)
    max_replicas        = optional(number)
    log_retention_days  = optional(number)
  })
  default = {}
}

# Feature flags
variable "feature_flags" {
  description = "Feature flags for experimental features"
  type = object({
    enable_blue_green_deployment = optional(bool, false)
    enable_canary_deployment     = optional(bool, false)
    enable_chaos_engineering     = optional(bool, false)
    enable_cost_optimization     = optional(bool, true)
    enable_security_scanning     = optional(bool, true)
  })
  default = {}
}

# Sensitive Variables (passed via environment or GitHub secrets)
variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "app_secret_key" {
  description = "Application secret key"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "encryption_key" {
  description = "Encryption key for sensitive data"
  type        = string
  sensitive   = true
  default     = ""
}

variable "sendgrid_api_key" {
  description = "SendGrid API key for email services"
  type        = string
  sensitive   = true
  default     = ""
}

variable "sendgrid_from_email" {
  description = "SendGrid from email address"
  type        = string
  default     = "noreply@yourdomain.com"
}

variable "domain_name" {
  description = "Primary domain name"
  type        = string
  default     = "yourdomain.com"
}

variable "api_domain" {
  description = "API subdomain"
  type        = string
  default     = "api.yourdomain.com"
}

variable "ssl_certificate_arn" {
  description = "AWS ACM SSL certificate ARN"
  type        = string
  default     = ""
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
  default     = "admin123"
}

variable "prometheus_password" {
  description = "Prometheus basic auth password"
  type        = string
  sensitive   = true
  default     = ""
}
