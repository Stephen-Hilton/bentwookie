# Deployment Stage Instructions

You are now in the **Deployment Stage** of the BentWookie workflow.

## Your Mission
Deploy the tested implementation to the appropriate environment according to the infrastructure requirements.

## Context
- **Task Name**: {name}
- **Change Type**: {change_type}
- **Project Phase**: {project_phase}
- **Priority**: {priority}
- **Source Code Location**: {file_paths.project_root}

## Before You Begin
1. Read all markdown files in `tasks/global/*.md` to understand deployment standards
2. Verify all tests passed in the previous stage
3. Review infrastructure requirements for this task

## Infrastructure Configuration
- **Compute**: {infrastructure.compute}
- **Storage**: {infrastructure.storage}
- **Queue**: {infrastructure.queue}
- **Access**: {infrastructure.access}

## Deployment Guidelines

### Pre-Deployment Checklist
- [ ] All tests pass
- [ ] Code has been reviewed (if applicable)
- [ ] Dependencies are properly specified
- [ ] Configuration is environment-appropriate
- [ ] Rollback plan is understood

### Deployment Steps
1. **Prepare** - Package code and dependencies
2. **Configure** - Set up environment-specific configuration
3. **Deploy** - Deploy to target infrastructure
4. **Verify** - Confirm deployment was successful
5. **Document** - Record deployment details

### Environment Considerations
- Use appropriate credentials for the target environment
- Follow least-privilege principles
- Enable appropriate logging and monitoring
- Configure health checks if applicable

## Your Tasks
1. Package the implementation for deployment
2. Configure deployment settings
3. Execute the deployment
4. Verify the deployment was successful
5. Document the deployment process and any issues

## Success Criteria
- [ ] Code is properly packaged
- [ ] Deployment completes without errors
- [ ] Service/feature is accessible in target environment
- [ ] Logs and monitoring are configured
- [ ] Documentation is updated

## Upon Completion
1. Document any learnings in the Learnings section
2. Note any deployment errors in the frontmatter `errors` array
3. Update the task status to "Ready" when deployment is complete
4. Include deployment verification results

## Important Notes
- Do NOT directly edit the YAML frontmatter (except status updates)
- If deployment fails, document the error and attempt remediation
- For rollback scenarios, document the steps taken
