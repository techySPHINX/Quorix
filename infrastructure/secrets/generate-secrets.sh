#!/bin/bash

# =============================================================================
# EVENTLY SECRETS GENERATOR
# =============================================================================
# This script generates secure random values for all secrets needed by the application.
# Run this script to create a secrets.env file with randomly generated secure values.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
SECRETS_FILE="${SCRIPT_DIR}/secrets.env"
TEMPLATE_FILE="${SCRIPT_DIR}/secrets.env.template"

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

# Function to generate random string
generate_random_string() {
    local length=${1:-32}
    openssl rand -hex $((length/2))
}

# Function to generate secure password
generate_password() {
    local length=${1:-24}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to generate JWT secret
generate_jwt_secret() {
    openssl rand -base64 64 | tr -d "=+/" | cut -c1-64
}

# Function to generate encryption key (32 characters for AES-256)
generate_encryption_key() {
    openssl rand -hex 16
}

# Check if secrets file already exists
if [ -f "$SECRETS_FILE" ]; then
    log_warning "Secrets file already exists at $SECRETS_FILE"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Keeping existing secrets file."
        exit 0
    fi
fi

log_info "Generating new secrets file..."

# Copy template and replace placeholder values
cp "$TEMPLATE_FILE" "$SECRETS_FILE"

# Generate all the secrets
DB_PASSWORD=$(generate_password 32)
DB_ROOT_PASSWORD=$(generate_password 32)
REDIS_PASSWORD=$(generate_password 24)
SECRET_KEY=$(generate_random_string 64)
JWT_SECRET_KEY=$(generate_jwt_secret)
ENCRYPTION_KEY=$(generate_encryption_key)
GRAFANA_PASSWORD=$(generate_password 16)
PROMETHEUS_PASSWORD=$(generate_password 16)

# Replace placeholders in the secrets file
sed -i.bak \
    -e "s/YOUR_SECURE_DB_PASSWORD/$DB_PASSWORD/g" \
    -e "s/YOUR_SECURE_ROOT_PASSWORD/$DB_ROOT_PASSWORD/g" \
    -e "s/YOUR_REDIS_PASSWORD/$REDIS_PASSWORD/g" \
    -e "s/YOUR_SUPER_SECRET_KEY_HERE_USE_LONG_RANDOM_STRING/$SECRET_KEY/g" \
    -e "s/YOUR_JWT_SECRET_KEY_HERE/$JWT_SECRET_KEY/g" \
    -e "s/YOUR_ENCRYPTION_KEY_32_CHARS_LONG/$ENCRYPTION_KEY/g" \
    -e "s/YOUR_GRAFANA_PASSWORD/$GRAFANA_PASSWORD/g" \
    -e "s/YOUR_PROMETHEUS_PASSWORD/$PROMETHEUS_PASSWORD/g" \
    "$SECRETS_FILE"

# Remove backup file
rm "${SECRETS_FILE}.bak"

# Set proper permissions
chmod 600 "$SECRETS_FILE"

log_success "Secrets file generated successfully!"
log_info "Location: $SECRETS_FILE"
log_warning "Please update the following values manually:"
echo "  - SENDGRID_API_KEY"
echo "  - AWS credentials"
echo "  - SSL certificate ARN"
echo "  - Domain names"
echo "  - OAuth client secrets"
echo "  - Third-party API keys"
echo "  - Webhook URLs"

log_info "Generated secrets:"
log_success "✓ Database password: $DB_PASSWORD"
log_success "✓ Redis password: $REDIS_PASSWORD"
log_success "✓ Application secret key: ${SECRET_KEY:0:20}..."
log_success "✓ JWT secret: ${JWT_SECRET_KEY:0:20}..."
log_success "✓ Encryption key: ${ENCRYPTION_KEY:0:16}..."
log_success "✓ Grafana password: $GRAFANA_PASSWORD"
log_success "✓ Prometheus password: $PROMETHEUS_PASSWORD"

log_warning "IMPORTANT: Add secrets.env to your .gitignore file!"
log_warning "NEVER commit secrets.env to version control!"

# Check if .gitignore exists and add secrets.env if not present
GITIGNORE_FILE="${SCRIPT_DIR}/../../.gitignore"
if [ -f "$GITIGNORE_FILE" ]; then
    if ! grep -q "secrets.env" "$GITIGNORE_FILE"; then
        echo "" >> "$GITIGNORE_FILE"
        echo "# Secrets" >> "$GITIGNORE_FILE"
        echo "secrets.env" >> "$GITIGNORE_FILE"
        echo "infrastructure/secrets/secrets.env" >> "$GITIGNORE_FILE"
        log_success "Added secrets.env to .gitignore"
    fi
else
    log_warning ".gitignore file not found. Make sure to ignore secrets.env in version control!"
fi
