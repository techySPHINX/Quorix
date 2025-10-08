# =============================================================================

# GITHUB SECRETS SETUP GUIDE

# =============================================================================

# This document explains how to set up GitHub Secrets for the CI/CD pipeline.

# These secrets are required for automated deployment to AWS and other services.

## Required GitHub Secrets

To set up GitHub Secrets, go to your repository → Settings → Secrets and variables → Actions

### AWS Deployment Secrets

```
AWS_ACCESS_KEY_ID          - AWS access key for deployment
AWS_SECRET_ACCESS_KEY      - AWS secret key for deployment
AWS_REGION                 - AWS region (e.g., us-west-2)
AWS_ACCOUNT_ID            - Your AWS account ID
```

### Database Secrets

```
DATABASE_URL              - Full database connection string
DB_PASSWORD               - Database user password
```

### Application Secrets

```
SECRET_KEY                - Application secret key (64+ characters)
JWT_SECRET_KEY            - JWT signing secret (64+ characters)
ENCRYPTION_KEY            - AES encryption key (32 characters)
```

### Email Service Secrets

```
SENDGRID_API_KEY          - SendGrid API key for emails
SENDGRID_FROM_EMAIL       - From email address
```

### Redis Secrets

```
REDIS_URL                 - Redis connection URL
REDIS_PASSWORD            - Redis password
```

### SSL Certificate

```
SSL_CERTIFICATE_ARN       - AWS ACM certificate ARN
```

### Monitoring Secrets

```
GRAFANA_ADMIN_PASSWORD    - Grafana admin password
PROMETHEUS_PASSWORD       - Prometheus basic auth password
```

### Notification Secrets (Optional)

```
SLACK_WEBHOOK_URL         - Slack webhook for notifications
DISCORD_WEBHOOK_URL       - Discord webhook for notifications
SENTRY_DSN               - Sentry error tracking DSN
```

### Domain Configuration

```
DOMAIN_NAME              - Primary domain (e.g., yourdomain.com)
API_DOMAIN               - API subdomain (e.g., api.yourdomain.com)
```

## Setting Up Secrets

### Option 1: Manual Setup

1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret name and value from the list above

### Option 2: Using GitHub CLI

```bash
# Install GitHub CLI: https://cli.github.com/

# Login to GitHub
gh auth login

# Set secrets (replace values with actual secrets)
gh secret set AWS_ACCESS_KEY_ID --body "YOUR_AWS_ACCESS_KEY"
gh secret set AWS_SECRET_ACCESS_KEY --body "YOUR_AWS_SECRET_ACCESS_KEY"
gh secret set AWS_REGION --body "us-west-2"
gh secret set AWS_ACCOUNT_ID --body "123456789012"

gh secret set DATABASE_URL --body "postgresql://user:pass@host:5432/db"
gh secret set DB_PASSWORD --body "your_secure_db_password"

gh secret set SECRET_KEY --body "your_64_character_secret_key_here"
gh secret set JWT_SECRET_KEY --body "your_64_character_jwt_secret_here"
gh secret set ENCRYPTION_KEY --body "your_32_character_encryption_key"

gh secret set SENDGRID_API_KEY --body "SG.your_sendgrid_api_key"
gh secret set SENDGRID_FROM_EMAIL --body "noreply@yourdomain.com"

gh secret set REDIS_URL --body "redis://localhost:6379"
gh secret set REDIS_PASSWORD --body "your_redis_password"

gh secret set SSL_CERTIFICATE_ARN --body "arn:aws:acm:region:account:certificate/id"

gh secret set GRAFANA_ADMIN_PASSWORD --body "your_grafana_password"
gh secret set PROMETHEUS_PASSWORD --body "your_prometheus_password"

gh secret set DOMAIN_NAME --body "yourdomain.com"
gh secret set API_DOMAIN --body "api.yourdomain.com"

# Optional notification secrets
gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
gh secret set SENTRY_DSN --body "https://your-sentry-dsn@sentry.io/project-id"
```

### Option 3: Bulk Import from File

```bash
# Create a secrets file (DO NOT commit this file!)
cat > github-secrets.txt << EOF
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
AWS_REGION=us-west-2
AWS_ACCOUNT_ID=123456789012
DATABASE_URL=postgresql://user:pass@host:5432/db
DB_PASSWORD=your_secure_db_password
SECRET_KEY=your_64_character_secret_key_here
JWT_SECRET_KEY=your_64_character_jwt_secret_here
ENCRYPTION_KEY=your_32_character_encryption_key
SENDGRID_API_KEY=SG.your_sendgrid_api_key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password
SSL_CERTIFICATE_ARN=arn:aws:acm:region:account:certificate/id
GRAFANA_ADMIN_PASSWORD=your_grafana_password
PROMETHEUS_PASSWORD=your_prometheus_password
DOMAIN_NAME=yourdomain.com
API_DOMAIN=api.yourdomain.com
EOF

# Import secrets from file
while IFS='=' read -r key value; do
    if [[ ! $key =~ ^#.* ]] && [[ -n $key ]]; then
        echo "Setting secret: $key"
        gh secret set "$key" --body "$value"
    fi
done < github-secrets.txt

# Remove the secrets file for security
rm github-secrets.txt
```

## Security Best Practices

### 1. Secret Rotation

- Rotate secrets regularly (every 90 days)
- Use different secrets for different environments
- Monitor secret usage and access

### 2. Least Privilege Access

- Create dedicated AWS IAM users for GitHub Actions
- Grant minimal required permissions
- Use temporary credentials where possible

### 3. Environment Separation

- Use different secrets for development, staging, and production
- Use GitHub Environments for additional protection
- Require reviews for production deployments

### 4. Monitoring and Auditing

- Monitor AWS CloudTrail for secret usage
- Set up alerts for unauthorized access
- Regular security audits of secrets

## Environment Setup

### Development Environment

```bash
# Copy the template and generate secrets
cp infrastructure/secrets/secrets.env.template infrastructure/secrets/secrets.env

# Run the secrets generator
chmod +x infrastructure/secrets/generate-secrets.sh
./infrastructure/secrets/generate-secrets.sh

# Load secrets in your development environment
source infrastructure/secrets/secrets.env
```

### Production Environment

Production secrets are managed through:

1. GitHub Secrets (for CI/CD)
2. AWS Secrets Manager (for runtime)
3. Kubernetes Secrets (for pod access)

## Troubleshooting

### Common Issues

1. **Secret not found**: Ensure secret name matches exactly (case-sensitive)
2. **AWS permissions**: Verify IAM user has required permissions
3. **Database connection**: Check database URL format and credentials
4. **SSL certificate**: Ensure certificate is in the correct AWS region

### Validation Script

```bash
# Check if all required secrets are set
required_secrets=(
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "DATABASE_URL"
    "SECRET_KEY"
    "JWT_SECRET_KEY"
    "SENDGRID_API_KEY"
)

for secret in "${required_secrets[@]}"; do
    if gh secret list | grep -q "$secret"; then
        echo "✓ $secret is set"
    else
        echo "✗ $secret is missing"
    fi
done
```

## Next Steps

After setting up secrets:

1. Update terraform variables with your actual values
2. Configure your domain DNS settings
3. Request SSL certificates through AWS ACM
4. Test the deployment pipeline
5. Set up monitoring and alerting

Remember: Never commit secrets to version control! Always use environment variables or secret management systems.
