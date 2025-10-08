# Evently Infrastructure Deployment Guide

This directory contains comprehensive infrastructure-as-code and deployment configurations for the Evently platform, supporting production-ready deployments on AWS, Kubernetes, and Docker.

## 🏗️ Infrastructure Overview

### Components

- **Terraform**: AWS infrastructure provisioning
- **Kubernetes**: Container orchestration and application deployment
- **Docker**: Containerization and local development
- **Monitoring**: Prometheus, Grafana, and observability stack

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │   Load Balancer │    │      CDN        │
│   Load Balancer │◄───┤     (ALB)       │◄───┤   (CloudFront)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  EKS Cluster    │    │   PostgreSQL    │    │      Redis      │
│  (Kubernetes)   │◄───┤     (RDS)       │    │  (ElastiCache)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Pods      │    │  Worker Pods    │    │   Beat/Flower   │
│  (FastAPI)      │    │   (Celery)      │    │     Pods        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Terraform** >= 1.0
3. **kubectl** configured
4. **Docker** and Docker Compose
5. **Helm** (for Kubernetes addons)

### 1. Local Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/evently.git
cd evently

# Start local development stack
cd infrastructure/docker
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f evently-api
```

### 2. AWS Infrastructure Deployment

```bash
# Navigate to Terraform directory
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Plan deployment (development)
terraform plan -var-file="terraform.dev.tfvars"

# Apply infrastructure
terraform apply -var-file="terraform.dev.tfvars"

# Get cluster credentials
aws eks update-kubeconfig --region us-west-2 --name evently-development-eks
```

### 3. Kubernetes Application Deployment

```bash
# Deploy to Kubernetes
cd infrastructure/kubernetes

# Create namespace and deploy
kubectl apply -f evently-api.yaml
kubectl apply -f evently-workers.yaml
kubectl apply -f evently-ingress.yaml

# Check deployment status
kubectl get pods -n evently
kubectl get services -n evently
kubectl get ingress -n evently
```

## 📁 Directory Structure

```
infrastructure/
├── terraform/           # AWS infrastructure as code
│   ├── main.tf          # Main Terraform configuration
│   ├── variables.tf     # Input variables
│   ├── outputs.tf       # Output values
│   ├── terraform.dev.tfvars   # Development environment
│   └── terraform.prod.tfvars  # Production environment
├── kubernetes/          # Kubernetes manifests
│   ├── evently-api.yaml      # API deployment and services
│   ├── evently-workers.yaml  # Celery workers and beat
│   └── evently-ingress.yaml  # Ingress and networking
└── docker/             # Docker configurations
    ├── Dockerfile.production # Multi-stage production Dockerfile
    └── docker-compose.yml    # Local development stack
```

## ⚙️ Configuration

### Environment Variables

#### Required Secrets

```bash
# Database
DB_PASSWORD="your-secure-database-password"

# Redis
REDIS_PASSWORD="your-secure-redis-password"

# Application
SECRET_KEY="your-super-secret-application-key"
SENDGRID_API_KEY="your-sendgrid-api-key"

# Celery
CELERY_FLOWER_PASSWORD="your-flower-password"
```

#### Application Settings

```bash
# Database Configuration
DB_HOST="your-database-host"
DB_PORT="5432"
DB_NAME="evently"
DB_USER="evently_user"

# Redis Configuration
REDIS_HOST="your-redis-host"
REDIS_PORT="6379"
REDIS_DB="0"

# Email Configuration
SENDGRID_FROM_EMAIL="noreply@yourdomain.com"
SENDGRID_FROM_NAME="Evently Platform"

# Security Configuration
BACKEND_CORS_ORIGINS="https://yourdomain.com"
ALLOWED_HOSTS="yourdomain.com,api.yourdomain.com"
```

## 🏭 Production Deployment

### 1. Infrastructure Provisioning

```bash
# Production infrastructure
cd infrastructure/terraform

# Initialize with production backend
terraform init -backend-config="bucket=your-terraform-state-bucket"

# Plan production deployment
terraform plan -var-file="terraform.prod.tfvars"

# Apply with approval
terraform apply -var-file="terraform.prod.tfvars"
```

### 2. SSL/TLS Configuration

```bash
# Update ACM certificate ARN in terraform.prod.tfvars
domain_name = "evently.yourdomain.com"
create_route53_zone = true

# Update Kubernetes ingress with certificate
kubectl apply -f evently-ingress.yaml
```

### 3. Monitoring Setup

```bash
# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=evently-production-eks
```

## 🔍 Monitoring & Observability

### Metrics Collection

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **CloudWatch**: AWS infrastructure monitoring
- **ELK Stack**: Centralized logging (optional)

### Key Metrics

- API response times and error rates
- Database connection pool utilization
- Redis cache hit/miss ratios
- Celery task execution metrics
- Kubernetes pod and node metrics

### Access Points

- **API**: `https://api.evently.yourdomain.com`
- **Flower**: `https://flower.evently.yourdomain.com`
- **Grafana**: `https://grafana.evently.yourdomain.com`
- **Prometheus**: `https://prometheus.evently.yourdomain.com`

## 🔒 Security

### Network Security

- Private subnets for application and database layers
- Security groups with minimal required access
- WAF protection for public endpoints
- VPC Flow Logs for network monitoring

### Application Security

- TLS encryption in transit
- Encryption at rest for databases
- Secrets management via AWS Parameter Store
- Non-root container execution
- Read-only root filesystems

### Access Control

- IAM roles with least privilege
- Kubernetes RBAC
- Network policies for pod-to-pod communication
- Regular security scanning and updates

## 📊 Scaling

### Auto-scaling Configuration

- **Horizontal Pod Autoscaler**: CPU and memory-based scaling
- **Cluster Autoscaler**: Node-level scaling
- **Database**: Read replicas for read-heavy workloads
- **Cache**: Redis clustering for high availability

### Performance Optimization

- Connection pooling for database and Redis
- CDN for static asset delivery
- Gzip compression
- HTTP/2 support
- Caching strategies at multiple layers

## 🚨 Disaster Recovery

### Backup Strategy

- **Database**: Automated daily backups with 30-day retention
- **Redis**: Snapshot backups for cache reconstruction
- **Application**: Stateless design for easy recovery
- **Infrastructure**: Terraform state backup

### Recovery Procedures

1. **Database Recovery**: Point-in-time restore from RDS backups
2. **Application Recovery**: Redeploy from container registry
3. **Infrastructure Recovery**: Terraform re-apply from state
4. **DNS Failover**: Route53 health checks and failover

## 🔧 Troubleshooting

### Common Issues

#### Pod Startup Issues

```bash
# Check pod status
kubectl get pods -n evently

# Describe pod for events
kubectl describe pod <pod-name> -n evently

# Check logs
kubectl logs <pod-name> -n evently -f
```

#### Database Connection Issues

```bash
# Test database connectivity
kubectl exec -it <pod-name> -n evently -- pg_isready -h $DB_HOST -p $DB_PORT

# Check database logs
aws rds describe-db-log-files --db-instance-identifier evently-production-postgres
```

#### Redis Connection Issues

```bash
# Test Redis connectivity
kubectl exec -it <pod-name> -n evently -- redis-cli -h $REDIS_HOST -p $REDIS_PORT ping

# Check ElastiCache logs in CloudWatch
```

### Health Check Endpoints

- **API Health**: `GET /health`
- **API Readiness**: `GET /health/ready`
- **Metrics**: `GET /metrics`

## 📈 Cost Optimization

### AWS Cost Management

- **Spot Instances**: For non-critical workloads
- **Reserved Instances**: For predictable workloads
- **Auto-scaling**: Scale down during low usage
- **Resource Tagging**: Track costs by environment/team

### Resource Optimization

- **Right-sizing**: Regular review of instance sizes
- **Storage Optimization**: Use appropriate storage classes
- **Network Optimization**: Minimize cross-AZ traffic
- **Monitoring**: Cost alerts and budgets

## 🤝 Contributing

### Infrastructure Changes

1. Update Terraform configurations
2. Test in development environment
3. Create pull request with detailed changes
4. Apply via CI/CD pipeline after approval

### Application Deployment

1. Update Kubernetes manifests
2. Test deployment in staging
3. Rolling update to production
4. Monitor metrics and rollback if needed

## 📞 Support

### Documentation

- [AWS EKS User Guide](https://docs.aws.amazon.com/eks/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)

### Monitoring Dashboards

- **Application**: Grafana dashboards for API metrics
- **Infrastructure**: CloudWatch dashboards for AWS resources
- **Logs**: Centralized logging with search capabilities

### Emergency Contacts

- **On-call Engineer**: Use PagerDuty or similar
- **DevOps Team**: infrastructure@yourdomain.com
- **Security Team**: security@yourdomain.com
