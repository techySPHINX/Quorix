# Evently Infrastructure Management Scripts

## Quick Start Commands

### Prerequisites Setup

```bash
# Install required tools (macOS)
brew install terraform kubectl awscli helm

# Install required tools (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y curl unzip
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Environment Setup

```bash
# Configure AWS credentials
aws configure

# Set up environment variables
export AWS_REGION=us-west-2
export ENVIRONMENT=development  # or production
export PROJECT_NAME=evently
```

## Deployment Commands

### 1. Development Environment

```bash
# Deploy everything
./infrastructure/deploy.sh development us-west-2 deploy

# Deploy only application updates
./infrastructure/deploy.sh development us-west-2 update

# Check health
./infrastructure/deploy.sh development us-west-2 health

# Cleanup environment
./infrastructure/deploy.sh development us-west-2 cleanup
```

### 2. Production Environment

```bash
# Deploy to production
./infrastructure/deploy.sh production us-west-2 deploy

# Production health check
./infrastructure/deploy.sh production us-west-2 health
```

### 3. Manual Terraform Commands

```bash
cd infrastructure/terraform

# Initialize and plan
terraform init
terraform workspace select development
terraform plan -var-file="terraform.development.tfvars"

# Apply changes
terraform apply -var-file="terraform.development.tfvars"

# View outputs
terraform output

# Destroy infrastructure
terraform destroy -var-file="terraform.development.tfvars"
```

### 4. Manual Kubernetes Commands

```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-west-2 --name evently-development-eks

# Apply manifests
kubectl apply -f infrastructure/kubernetes/

# Check status
kubectl get pods -n evently
kubectl get services -n evently
kubectl get ingress -n evently

# View logs
kubectl logs deployment/evently-api -n evently -f
kubectl logs deployment/evently-worker -n evently -f

# Scale deployments
kubectl scale deployment evently-api --replicas=3 -n evently
kubectl scale deployment evently-worker --replicas=2 -n evently
```

### 5. Docker Commands

```bash
# Build production image
docker build -f infrastructure/docker/Dockerfile.production -t evently:latest .

# Run locally with docker-compose
cd infrastructure/docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Monitoring and Debugging

### 1. Application Monitoring

```bash
# Get Grafana URL
kubectl get service prometheus-grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Port forward Grafana (if LoadBalancer not available)
kubectl port-forward service/prometheus-grafana 3000:80 -n monitoring

# Access Grafana: http://localhost:3000 (admin/admin123)
```

### 2. Application Logs

```bash
# API logs
kubectl logs -f deployment/evently-api -n evently

# Worker logs
kubectl logs -f deployment/evently-worker -n evently

# All pods logs
kubectl logs -f -l app=evently -n evently --all-containers=true
```

### 3. Database Operations

```bash
# Connect to PostgreSQL
kubectl run postgres-client --rm -it --image=postgres:15 -- psql -h DB_HOST -U evently_user -d evently

# Check Redis
kubectl run redis-client --rm -it --image=redis:7-alpine -- redis-cli -h REDIS_HOST ping
```

### 4. Debug Networking

```bash
# Test internal connectivity
kubectl run debug-pod --rm -it --image=nicolaka/netshoot -- /bin/bash

# Check DNS resolution
nslookup evently-api-service.evently.svc.cluster.local

# Test service connectivity
curl http://evently-api-service.evently.svc.cluster.local/health
```

## Environment Configuration

### 1. Development Settings

- **Instance Types**: t3.medium nodes
- **Database**: db.t3.micro PostgreSQL
- **Redis**: cache.t3.micro
- **Replicas**: 2 API, 2 Workers
- **Monitoring**: 7-day retention
- **Security**: Basic (no WAF)

### 2. Production Settings

- **Instance Types**: t3.large/t3.xlarge nodes
- **Database**: db.r6g.large PostgreSQL with Multi-AZ
- **Redis**: cache.r6g.large with clustering
- **Replicas**: 5 API, 3 Workers
- **Monitoring**: 30-day retention
- **Security**: Full WAF + TLS

## Troubleshooting

### Common Issues

#### 1. Infrastructure Deployment Fails

```bash
# Check Terraform state
terraform show

# Validate configuration
terraform validate

# Check AWS permissions
aws sts get-caller-identity
aws iam list-attached-user-policies --user-name YOUR_USER
```

#### 2. Pods Not Starting

```bash
# Check pod status
kubectl describe pods -n evently

# Check resource quotas
kubectl describe quota -n evently

# Check node resources
kubectl top nodes
kubectl describe nodes
```

#### 3. Application Not Accessible

```bash
# Check ingress status
kubectl describe ingress evently-ingress -n evently

# Check load balancer
kubectl get service -n evently

# Check security groups (AWS Console)
aws ec2 describe-security-groups --group-names evently-alb-sg
```

#### 4. Database Connection Issues

```bash
# Check database status
aws rds describe-db-instances --db-instance-identifier evently-development-db

# Test connectivity from pod
kubectl exec deployment/evently-api -n evently -- python -c "from app.database import engine; print('DB OK')"

# Check security groups
aws ec2 describe-security-groups --group-names evently-db-sg
```

#### 5. Performance Issues

```bash
# Check resource usage
kubectl top pods -n evently
kubectl top nodes

# Check HPA status
kubectl get hpa -n evently

# View detailed metrics in Grafana
# Dashboard: Kubernetes > Compute Resources > Namespace (Pods)
```

### Emergency Procedures

#### 1. Rollback Deployment

```bash
# Rollback to previous version
kubectl rollout undo deployment/evently-api -n evently
kubectl rollout undo deployment/evently-worker -n evently

# Check rollout status
kubectl rollout status deployment/evently-api -n evently
```

#### 2. Scale Down for Maintenance

```bash
# Scale to zero
kubectl scale deployment evently-api --replicas=0 -n evently
kubectl scale deployment evently-worker --replicas=0 -n evently

# Scale back up
kubectl scale deployment evently-api --replicas=2 -n evently
kubectl scale deployment evently-worker --replicas=2 -n evently
```

#### 3. Database Maintenance

```bash
# Create snapshot before maintenance
aws rds create-db-snapshot --db-instance-identifier evently-development-db --db-snapshot-identifier evently-maintenance-$(date +%Y%m%d)

# Apply maintenance
aws rds modify-db-instance --db-instance-identifier evently-development-db --apply-immediately
```

## Security Considerations

### 1. Secrets Management

- Database credentials stored in AWS Secrets Manager
- Redis password auto-generated
- API keys rotated regularly
- TLS certificates managed by ACM

### 2. Network Security

- Private subnets for databases
- Security groups with minimal access
- VPC endpoints for AWS services
- WAF protection in production

### 3. Access Control

- RBAC enabled on EKS cluster
- IAM roles for service accounts
- Least privilege principle
- Regular access reviews

## Cost Optimization

### 1. Development Environment

```bash
# Stop during off-hours
./infrastructure/deploy.sh development us-west-2 cleanup

# Use Spot instances (add to terraform.development.tfvars)
node_group_capacity_type = "SPOT"
```

### 2. Production Environment

```bash
# Monitor costs
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 --granularity MONTHLY --metrics BlendedCost

# Use Reserved Instances for predictable workloads
# Configure autoscaling for dynamic workloads
```

## Backup and Recovery

### 1. Database Backups

- Automated daily backups with 30-day retention
- Point-in-time recovery available
- Cross-region backup replication (production)

### 2. Application State

- Stateless application design
- Configuration stored in Git
- Secrets in AWS Secrets Manager

### 3. Disaster Recovery

```bash
# Cross-region replication setup
aws rds create-db-instance-read-replica --db-instance-identifier evently-prod-replica --source-db-instance-identifier evently-production-db --destination-region us-east-1

# Multi-region EKS setup
terraform workspace select dr
terraform apply -var-file="terraform.dr.tfvars"
```
