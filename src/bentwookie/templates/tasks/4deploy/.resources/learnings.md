# Deployment Stage Learnings

This file contains learnings specific to the deployment stage. Stage learnings supersede global learnings (except for interfaces).

## Key Learnings

- Always verify the target environment before deployment
- Use infrastructure-as-code when possible for reproducibility
- Keep deployment scripts idempotent
- Monitor deployment progress and be ready to rollback
- Document all environment-specific configurations

## AWS Deployment Patterns

### Lambda Deployments
- Package dependencies in layers for reusability
- Set appropriate memory and timeout values
- Configure VPC settings if accessing private resources

### Infrastructure Setup
- Use CloudFormation or Terraform for infrastructure
- Tag all resources appropriately
- Configure proper IAM roles with least privilege

## Common Pitfalls to Avoid

- Don't deploy without testing in a staging environment first
- Don't hardcode secrets - use Parameter Store or Secrets Manager
- Don't skip rollback planning
- Don't ignore deployment logs and alerts

## Best Practices

- Use blue-green or canary deployments for critical services
- Maintain deployment runbooks
- Set up automated rollback triggers
- Keep deployment artifacts versioned

---
*Add new learnings above this line. Deduplicate before task completion.*
