#!/bin/bash

# Evently Infrastructure Deployment Script
# Automates the complete deployment process for AWS + Kubernetes

set -e  # Exit on any error

# Configuration
ENVIRONMENT=${1:-development}
AWS_REGION=${2:-us-west-2}
PROJECT_NAME="evently"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local tools=("terraform" "kubectl" "aws" "helm" "docker")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if ! command -v $tool &> /dev/null; then
            missing_tools+=($tool)
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' or set environment variables."
        exit 1
    fi
    
    log_success "All prerequisites met."
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_info "Deploying infrastructure for environment: $ENVIRONMENT"
    
    cd infrastructure/terraform
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Select workspace or create if it doesn't exist
    if ! terraform workspace select $ENVIRONMENT 2>/dev/null; then
        log_info "Creating new workspace: $ENVIRONMENT"
        terraform workspace new $ENVIRONMENT
    fi
    
    # Plan deployment
    log_info "Planning Terraform deployment..."
    if ! terraform plan -var-file="terraform.${ENVIRONMENT}.tfvars" -out=tfplan; then
        log_error "Terraform plan failed"
        exit 1
    fi
    
    # Apply deployment
    log_info "Applying Terraform configuration..."
    if terraform apply tfplan; then
        log_success "Infrastructure deployed successfully"
    else
        log_error "Infrastructure deployment failed"
        exit 1
    fi
    
    # Save outputs for later use
    terraform output -json > ../outputs.json
    
    cd - > /dev/null
}

# Configure kubectl for EKS cluster
configure_kubectl() {
    log_info "Configuring kubectl for EKS cluster..."
    
    local cluster_name="${PROJECT_NAME}-${ENVIRONMENT}-eks"
    
    if aws eks update-kubeconfig --region $AWS_REGION --name $cluster_name; then
        log_success "kubectl configured for cluster: $cluster_name"
    else
        log_error "Failed to configure kubectl"
        exit 1
    fi
    
    # Verify cluster connectivity
    if kubectl cluster-info &> /dev/null; then
        log_success "Successfully connected to Kubernetes cluster"
    else
        log_error "Failed to connect to Kubernetes cluster"
        exit 1
    fi
}

# Install AWS Load Balancer Controller
install_alb_controller() {
    log_info "Installing AWS Load Balancer Controller..."
    
    local cluster_name="${PROJECT_NAME}-${ENVIRONMENT}-eks"
    local service_account_name="aws-load-balancer-controller"
    
    # Add EKS Helm repository
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    
    # Install AWS Load Balancer Controller
    if helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName=$cluster_name \
        --set serviceAccount.create=false \
        --set serviceAccount.name=$service_account_name; then
        log_success "AWS Load Balancer Controller installed"
    else
        log_warning "AWS Load Balancer Controller installation failed or already exists"
    fi
}

# Deploy monitoring stack
deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    # Add Prometheus Helm repository
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Create monitoring namespace
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    
    # Install Prometheus and Grafana
    if helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        -n monitoring \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --set prometheus.prometheusSpec.retention=30d \
        --set grafana.adminPassword="admin123" \
        --set grafana.service.type=LoadBalancer; then
        log_success "Monitoring stack deployed"
    else
        log_warning "Monitoring stack deployment failed or already exists"
    fi
}

# Deploy application to Kubernetes
deploy_application() {
    log_info "Deploying Evently application to Kubernetes..."
    
    cd infrastructure/kubernetes
    
    # Apply Kubernetes manifests
    local manifests=("evently-api.yaml" "evently-workers.yaml" "evently-ingress.yaml")
    
    for manifest in "${manifests[@]}"; do
        log_info "Applying $manifest..."
        if kubectl apply -f $manifest; then
            log_success "$manifest applied successfully"
        else
            log_error "Failed to apply $manifest"
            exit 1
        fi
    done
    
    cd - > /dev/null
    
    # Wait for deployments to be ready
    log_info "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/evently-api -n evently
    kubectl wait --for=condition=available --timeout=300s deployment/evently-worker -n evently
    
    log_success "Application deployed successfully"
}

# Update application secrets
update_secrets() {
    log_info "Updating application secrets..."
    
    # Read Terraform outputs
    local outputs_file="infrastructure/outputs.json"
    if [ ! -f "$outputs_file" ]; then
        log_error "Terraform outputs file not found. Please run infrastructure deployment first."
        exit 1
    fi
    
    # Extract connection information from Terraform outputs
    local db_host=$(jq -r '.connection_info.value.database.host' $outputs_file)
    local redis_host=$(jq -r '.connection_info.value.redis.host' $outputs_file)
    
    # Update ConfigMap with actual values
    kubectl patch configmap evently-config -n evently --type merge -p="{\"data\":{\"DB_HOST\":\"$db_host\",\"REDIS_HOST\":\"$redis_host\"}}"
    
    log_success "Secrets updated successfully"
}

# Display deployment information
show_deployment_info() {
    log_info "Deployment Information:"
    echo ""
    
    # Get load balancer URL
    local ingress_url=$(kubectl get ingress evently-ingress -n evently -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "Pending...")
    
    # Get service endpoints
    echo "🌐 Application Endpoints:"
    echo "   API: https://$ingress_url"
    echo "   Flower: https://flower.$ingress_url"
    echo ""
    
    # Show pod status
    echo "📊 Pod Status:"
    kubectl get pods -n evently
    echo ""
    
    # Show service status
    echo "🔌 Service Status:"
    kubectl get services -n evently
    echo ""
    
    # Show ingress status
    echo "🚪 Ingress Status:"
    kubectl get ingress -n evently
    echo ""
    
    # Monitoring information
    echo "📈 Monitoring:"
    local grafana_ip=$(kubectl get service prometheus-grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending...")
    echo "   Grafana: http://$grafana_ip (admin/admin123)"
    echo ""
    
    log_success "Deployment completed successfully!"
}

# Cleanup function
cleanup() {
    log_warning "Cleaning up resources..."
    
    # Remove Kubernetes resources
    kubectl delete namespace evently --ignore-not-found=true
    kubectl delete namespace monitoring --ignore-not-found=true
    
    # Destroy Terraform infrastructure
    cd infrastructure/terraform
    terraform destroy -var-file="terraform.${ENVIRONMENT}.tfvars" -auto-approve
    cd - > /dev/null
    
    log_success "Cleanup completed"
}

# Health check function
health_check() {
    log_info "Running health checks..."
    
    # Check API health
    local api_url="http://$(kubectl get service evently-api-service -n evently -o jsonpath='{.spec.clusterIP}')"
    if kubectl run health-check --image=curlimages/curl --restart=Never --rm -i --tty -- curl -f "$api_url/health"; then
        log_success "API health check passed"
    else
        log_warning "API health check failed"
    fi
    
    # Check database connectivity
    if kubectl exec deployment/evently-api -n evently -- python -c "from app.database import engine; print('Database connection OK')"; then
        log_success "Database connectivity check passed"
    else
        log_warning "Database connectivity check failed"
    fi
    
    # Check Redis connectivity
    if kubectl exec deployment/evently-api -n evently -- python -c "from app.redis import redis_client; redis_client.ping(); print('Redis connection OK')"; then
        log_success "Redis connectivity check passed"
    else
        log_warning "Redis connectivity check failed"
    fi
}

# Main execution
main() {
    log_info "Starting Evently deployment for environment: $ENVIRONMENT"
    
    case "${3:-deploy}" in
        "deploy")
            check_prerequisites
            deploy_infrastructure
            configure_kubectl
            install_alb_controller
            deploy_monitoring
            update_secrets
            deploy_application
            show_deployment_info
            ;;
        "cleanup")
            cleanup
            ;;
        "health")
            health_check
            ;;
        "update")
            deploy_application
            show_deployment_info
            ;;
        *)
            echo "Usage: $0 <environment> <region> <action>"
            echo "Actions: deploy, cleanup, health, update"
            echo "Example: $0 development us-west-2 deploy"
            exit 1
            ;;
    esac
}

# Trap to cleanup on script exit
trap 'log_error "Deployment interrupted"' INT TERM

# Run main function
main "$@"
