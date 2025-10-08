# 🚀 Evently Production Deployment Guide

This guide provides step-by-step instructions for deploying Evently to production using AWS, Kubernetes, and CI/CD pipelines.

## 📋 Prerequisites

### Required Tools

- AWS CLI v2
- kubectl
- Terraform >= 1.5
- Docker
- Helm 3.x
- GitHub CLI (optional, for secrets management)

### Required Accounts

- AWS Account with admin permissions
- GitHub repository with Actions enabled
- SendGrid account for email services
- Domain name with DNS control

## 🔐 Security Setup

### 1. Generate Secrets

```bash
# Navigate to secrets directory
cd infrastructure/secrets

# Generate secure random secrets
chmod +x generate-secrets.sh
./generate-secrets.sh

# Review generated secrets
cat secrets.env
```

### 2. Configure GitHub Secrets

#### Option A: Using GitHub CLI

```bash
# Install GitHub CLI and login
gh auth login

# Set all required secrets (replace with actual values)
gh secret set AWS_ACCESS_KEY_ID --body "YOUR_AWS_ACCESS_KEY"
gh secret set AWS_SECRET_ACCESS_KEY --body "YOUR_AWS_SECRET_ACCESS_KEY"
gh secret set AWS_REGION --body "us-west-2"
gh secret set AWS_ACCOUNT_ID --body "123456789012"

# Database secrets
gh secret set DATABASE_URL --body "postgresql://evently_user:$(grep DB_PASSWORD secrets.env | cut -d'=' -f2)@localhost:5432/evently"
gh secret set DB_PASSWORD --body "$(grep DB_PASSWORD secrets.env | cut -d'=' -f2)"

# Application secrets
gh secret set SECRET_KEY --body "$(grep SECRET_KEY secrets.env | cut -d'=' -f2)"
gh secret set JWT_SECRET_KEY --body "$(grep JWT_SECRET_KEY secrets.env | cut -d'=' -f2)"
gh secret set ENCRYPTION_KEY --body "$(grep ENCRYPTION_KEY secrets.env | cut -d'=' -f2)"

# Email configuration
gh secret set SENDGRID_API_KEY --body "YOUR_SENDGRID_API_KEY"
gh secret set SENDGRID_FROM_EMAIL --body "noreply@yourdomain.com"

# Redis configuration
gh secret set REDIS_URL --body "redis://localhost:6379"
gh secret set REDIS_PASSWORD --body "$(grep REDIS_PASSWORD secrets.env | cut -d'=' -f2)"

# Domain and SSL
gh secret set DOMAIN_NAME --body "yourdomain.com"
gh secret set API_DOMAIN --body "api.yourdomain.com"
gh secret set SSL_CERTIFICATE_ARN --body "arn:aws:acm:us-west-2:ACCOUNT:certificate/ID"

# Monitoring
gh secret set GRAFANA_ADMIN_PASSWORD --body "$(grep GRAFANA_PASSWORD secrets.env | cut -d'=' -f2)"
gh secret set PROMETHEUS_PASSWORD --body "$(grep PROMETHEUS_PASSWORD secrets.env | cut -d'=' -f2)"

# Optional notifications
gh secret set SLACK_WEBHOOK_URL --body "YOUR_SLACK_WEBHOOK_URL"
```

#### Option B: Manual Setup

1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Add each secret from the list in `infrastructure/secrets/GITHUB_SECRETS_SETUP.md`

### 3. AWS IAM Setup

Create a dedicated IAM user for GitHub Actions:

```bash
# Create IAM user
aws iam create-user --user-name github-actions-evently

# Attach necessary policies
aws iam attach-user-policy --user-name github-actions-evently --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
aws iam attach-user-policy --user-name github-actions-evently --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
aws iam attach-user-policy --user-name github-actions-evently --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
aws iam attach-user-policy --user-name github-actions-evently --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
aws iam attach-user-policy --user-name github-actions-evently --policy-arn arn:aws:iam::aws:policy/AmazonRDSFullAccess
aws iam attach-user-policy --user-name github-actions-evently --policy-arn arn:aws:iam::aws:policy/ElastiCacheFullAccess

# Create access keys
aws iam create-access-key --user-name github-actions-evently
```

## 🏗️ Infrastructure Deployment

### 1. Manual Infrastructure Setup (First Time)

For the initial setup, deploy infrastructure manually:

```bash
# Navigate to terraform directory
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Create production workspace
terraform workspace new production

# Plan deployment
terraform plan -var-file="terraform.production.tfvars"

# Apply infrastructure
terraform apply -var-file="terraform.production.tfvars"

# Save outputs
terraform output -json > ../outputs.json
```

### 2. Configure kubectl

```bash
# Update kubeconfig for EKS cluster
aws eks update-kubeconfig --region us-west-2 --name evently-production-eks

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### 3. Install Required Kubernetes Components

```bash
# Install AWS Load Balancer Controller
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.1/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json

# Create service account
eksctl create iamserviceaccount \
  --cluster=evently-production-eks \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --role-name "AmazonEKSLoadBalancerControllerRole" \
  --attach-policy-arn=arn:aws:iam::ACCOUNT-ID:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Install controller via Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=evently-production-eks \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

### 4. SSL Certificate Setup

```bash
# Request certificate via AWS ACM
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names *.yourdomain.com \
  --validation-method DNS \
  --region us-west-2

# Note the certificate ARN and add it to GitHub secrets
```

## 🚀 Application Deployment

### 1. Automated Deployment (Recommended)

Push to the main branch to trigger automatic deployment:

```bash
git add .
git commit -m "feat: production deployment setup"
git push origin main
```

The CI/CD pipeline will:

1. Run tests and security scans
2. Build and push Docker images
3. Deploy infrastructure via Terraform
4. Deploy application to Kubernetes
5. Run health checks
6. Send notifications

### 2. Manual Deployment

If you need to deploy manually:

```bash
# Build and push Docker image
docker build -f infrastructure/docker/Dockerfile.production -t evently/api:latest .
docker tag evently/api:latest YOUR_ECR_REGISTRY/evently:latest
docker push YOUR_ECR_REGISTRY/evently:latest

# Deploy to Kubernetes
cd infrastructure/kubernetes

# Create namespace
kubectl create namespace evently

# Create secrets
kubectl create secret generic evently-secrets \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  --from-literal=ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  --from-literal=SENDGRID_API_KEY="$SENDGRID_API_KEY" \
  --from-literal=SENDGRID_FROM_EMAIL="$SENDGRID_FROM_EMAIL" \
  --namespace=evently

# Apply manifests
kubectl apply -f evently-api.yaml
kubectl apply -f evently-workers.yaml
kubectl apply -f evently-ingress.yaml
```

## 📊 Monitoring Setup

### 1. Install Prometheus and Grafana

```bash
# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Create monitoring namespace
kubectl create namespace monitoring

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.retention=30d \
  --set grafana.adminPassword="$GRAFANA_ADMIN_PASSWORD"
```

### 2. Access Monitoring Dashboards

```bash
# Port forward to access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Access at http://localhost:3000
# Username: admin
# Password: [your-grafana-password]
```

## 🌐 DNS Configuration

Configure your domain DNS to point to the load balancer:

```bash
# Get load balancer hostname
kubectl get ingress evently-ingress -n evently -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Create DNS records:
# A/AAAA record: yourdomain.com → load-balancer-hostname
# CNAME record: api.yourdomain.com → load-balancer-hostname
# CNAME record: *.yourdomain.com → load-balancer-hostname
```

## ✅ Health Checks and Verification

### 1. Application Health

```bash
# Check pod status
kubectl get pods -n evently

# Check logs
kubectl logs -f deployment/evently-api -n evently

# Test API endpoint
curl -f https://api.yourdomain.com/health
```

### 2. Database Health

```bash
# Check RDS status
aws rds describe-db-instances --db-instance-identifier evently-production-db

# Test database connection from pod
kubectl exec -it deployment/evently-api -n evently -- python -c "
from app.database import engine
print('Database connection:', engine.url)
"
```

### 3. Redis Health

```bash
# Check ElastiCache status
aws elasticache describe-cache-clusters --cache-cluster-id evently-production-redis

# Test Redis connection
kubectl exec -it deployment/evently-api -n evently -- python -c "
from app.redis import redis_client
print('Redis ping:', redis_client.ping())
"
```

## 🔄 Updates and Maintenance

### Rolling Updates

```bash
# Update application
git push origin main  # Triggers automatic deployment

# Manual update
kubectl set image deployment/evently-api evently-api=YOUR_ECR_REGISTRY/evently:new-tag -n evently
kubectl rollout status deployment/evently-api -n evently
```

### Scaling

```bash
# Scale API pods
kubectl scale deployment evently-api --replicas=5 -n evently

# Scale worker pods
kubectl scale deployment evently-worker --replicas=3 -n evently
```

### Backup and Recovery

```bash
# Database backup
aws rds create-db-snapshot \
  --db-instance-identifier evently-production-db \
  --db-snapshot-identifier evently-backup-$(date +%Y%m%d-%H%M%S)

# Redis backup (automatic via ElastiCache)
aws elasticache create-snapshot \
  --cache-cluster-id evently-production-redis \
  --snapshot-name evently-redis-backup-$(date +%Y%m%d-%H%M%S)
```

## 🚨 Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**

   ```bash
   kubectl describe pod POD_NAME -n evently
   kubectl logs POD_NAME -n evently --previous
   ```

2. **Database Connection Issues**

   ```bash
   # Check security groups
   aws ec2 describe-security-groups --group-ids sg-xxx

   # Test connectivity
   kubectl run debug --image=postgres:15 --rm -it -- psql $DATABASE_URL
   ```

3. **Load Balancer Issues**

   ```bash
   # Check ALB status
   aws elbv2 describe-load-balancers

   # Check target groups
   aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:...
   ```

4. **Certificate Issues**

   ```bash
   # Check certificate status
   aws acm describe-certificate --certificate-arn YOUR_CERT_ARN

   # Validate DNS records
   dig yourdomain.com
   ```

### Emergency Procedures

1. **Rollback Deployment**

   ```bash
   kubectl rollout undo deployment/evently-api -n evently
   kubectl rollout undo deployment/evently-worker -n evently
   ```

2. **Scale Down for Maintenance**

   ```bash
   kubectl scale deployment evently-api --replicas=0 -n evently
   kubectl scale deployment evently-worker --replicas=0 -n evently
   ```

3. **Emergency Database Restore**
   ```bash
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier evently-production-db-restored \
     --db-snapshot-identifier evently-backup-YYYYMMDD-HHMMSS
   ```

## 📚 Additional Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Prometheus Monitoring](https://prometheus.io/docs/)

## 🤝 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review application logs
3. Check monitoring dashboards
4. Create an issue in the repository

---

**Security Note**: Always follow the principle of least privilege and regularly rotate secrets and access keys.
