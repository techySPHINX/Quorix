# Evently Infrastructure - AWS Deployment
# Production-ready Terraform configuration for scalable event management platform

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }

  backend "s3" {
    # Configure this with your actual S3 bucket details
    # bucket = "your-terraform-state-bucket"
    # key    = "evently/terraform.tfstate"
    # region = "us-west-2"
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Evently"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "DevOps"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local values
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  azs         = slice(data.aws_availability_zones.available.names, 0, 3)
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# VPC Configuration
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "${local.name_prefix}-vpc"
  cidr = var.vpc_cidr
  
  azs             = local.azs
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs
  
  enable_nat_gateway = true
  enable_vpn_gateway = false
  enable_dns_hostnames = true
  enable_dns_support = true
  
  # Database subnets
  database_subnets = var.database_subnet_cidrs
  create_database_subnet_group = true
  
  # ElastiCache subnets
  elasticache_subnets = var.cache_subnet_cidrs
  create_elasticache_subnet_group = true
  
  tags = local.common_tags
}

# Security Groups
resource "aws_security_group" "alb" {
  name_prefix = "${local.name_prefix}-alb-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alb-sg"
  })
}

resource "aws_security_group" "eks_cluster" {
  name_prefix = "${local.name_prefix}-eks-cluster-"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-eks-cluster-sg"
  })
}

resource "aws_security_group" "rds" {
  name_prefix = "${local.name_prefix}-rds-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_cluster.id]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds-sg"
  })
}

resource "aws_security_group" "redis" {
  name_prefix = "${local.name_prefix}-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Redis"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_cluster.id]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis-sg"
  })
}

# RDS PostgreSQL Database
resource "aws_db_subnet_group" "evently" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = module.vpc.database_subnets

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-subnet-group"
  })
}

resource "aws_db_parameter_group" "evently" {
  family = "postgres15"
  name   = "${local.name_prefix}-db-params"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_duration"
    value = "1"
  }

  parameter {
    name  = "log_lock_waits"
    value = "1"
  }

  tags = local.common_tags
}

resource "aws_db_instance" "evently" {
  identifier = "${local.name_prefix}-postgres"

  # Engine options
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.db_instance_class

  # Storage
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database configuration
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  # Network & Security
  db_subnet_group_name   = aws_db_subnet_group.evently.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Backup & Maintenance
  backup_retention_period = var.db_backup_retention_period
  backup_window          = "07:00-09:00"
  maintenance_window     = "Sun:09:00-Sun:11:00"
  
  # Monitoring & Performance
  parameter_group_name   = aws_db_parameter_group.evently.name
  monitoring_interval    = 60
  monitoring_role_arn   = aws_iam_role.rds_monitoring.arn
  performance_insights_enabled = true

  # Deletion protection
  deletion_protection = var.environment == "production" ? true : false
  skip_final_snapshot = var.environment != "production"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres"
  })
}

# RDS Monitoring Role
resource "aws_iam_role" "rds_monitoring" {
  name = "${local.name_prefix}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "evently" {
  name       = "${local.name_prefix}-cache-subnet"
  subnet_ids = module.vpc.elasticache_subnets

  tags = local.common_tags
}

resource "aws_elasticache_parameter_group" "evently" {
  family = "redis7.x"
  name   = "${local.name_prefix}-cache-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = local.common_tags
}

resource "aws_elasticache_replication_group" "evently" {
  replication_group_id       = "${local.name_prefix}-redis"
  description                = "Redis cluster for Evently application"

  node_type                  = var.redis_node_type
  port                       = 6379
  parameter_group_name       = aws_elasticache_parameter_group.evently.name

  num_cache_clusters         = var.redis_num_cache_nodes
  engine_version             = "7.0"

  subnet_group_name          = aws_elasticache_subnet_group.evently.name
  security_group_ids         = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token

  # Backup
  snapshot_retention_limit = 5
  snapshot_window         = "06:00-08:00"

  # Maintenance
  maintenance_window = "sun:08:00-sun:09:00"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis"
  })
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"

  cluster_name    = "${local.name_prefix}-eks"
  cluster_version = var.eks_cluster_version

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true
  cluster_endpoint_private_access = true

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    main = {
      name = "${local.name_prefix}-nodes"

      instance_types = var.eks_node_instance_types
      capacity_type  = "ON_DEMAND"

      min_size     = var.eks_node_min_size
      max_size     = var.eks_node_max_size
      desired_size = var.eks_node_desired_size

      ami_type = "AL2_x86_64"
      
      # Disk
      disk_size = 50
      
      # Network
      subnet_ids = module.vpc.private_subnets
      
      # Labels
      labels = {
        Environment = var.environment
        NodeGroup   = "main"
      }

      # Taints
      taints = {}

      tags = merge(local.common_tags, {
        Name = "${local.name_prefix}-worker-nodes"
      })
    }
  }

  # aws-auth configmap
  manage_aws_auth_configmap = true

  aws_auth_roles = [
    {
      rolearn  = aws_iam_role.eks_admin.arn
      username = "eks-admin"
      groups   = ["system:masters"]
    },
  ]

  tags = local.common_tags
}

# EKS Admin Role
resource "aws_iam_role" "eks_admin" {
  name = "${local.name_prefix}-eks-admin"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Application Load Balancer
resource "aws_lb" "evently" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = var.environment == "production" ? true : false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alb"
  })
}

# ACM Certificate
resource "aws_acm_certificate" "evently" {
  count = var.domain_name != "" ? 1 : 0

  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = [
    "*.${var.domain_name}"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cert"
  })
}

# Route53 Zone (if managing DNS)
resource "aws_route53_zone" "evently" {
  count = var.create_route53_zone && var.domain_name != "" ? 1 : 0

  name = var.domain_name

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-zone"
  })
}

# S3 Bucket for static assets/logs
resource "aws_s3_bucket" "evently_assets" {
  bucket = "${local.name_prefix}-assets-${random_string.bucket_suffix.result}"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-assets"
  })
}

resource "aws_s3_bucket_versioning" "evently_assets" {
  bucket = aws_s3_bucket.evently_assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evently_assets" {
  bucket = aws_s3_bucket.evently_assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "evently_assets" {
  bucket = aws_s3_bucket.evently_assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# CloudWatch Log Group for application logs
resource "aws_cloudwatch_log_group" "evently" {
  name              = "/aws/eks/${local.name_prefix}/evently"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-logs"
  })
}

# Parameter Store for secrets
resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.project_name}/${var.environment}/database/password"
  type  = "SecureString"
  value = var.db_password

  tags = local.common_tags
}

resource "aws_ssm_parameter" "redis_auth_token" {
  name  = "/${var.project_name}/${var.environment}/redis/auth_token"
  type  = "SecureString"
  value = var.redis_auth_token

  tags = local.common_tags
}

resource "aws_ssm_parameter" "secret_key" {
  name  = "/${var.project_name}/${var.environment}/app/secret_key"
  type  = "SecureString"
  value = var.app_secret_key

  tags = local.common_tags
}
