# Verification Phase

You are verifying the deployed changes work correctly in the target environment.

## Project Context
- **Project**: {project_name}
- **Version**: {project_version}
- **Phase**: {project_phase}

## Request Details
- **Request**: {request_name}
- **Type**: {request_type}
- **Description**: {request_prompt}

## Your Task

Verify the deployment was successful and the feature works as expected:

1. **Smoke Tests**
   - Verify the application starts correctly
   - Check basic functionality
   - Ensure no critical errors

2. **Feature Verification**
   - Test the specific feature that was implemented
   - Verify it works in the deployed environment
   - Check integration with other components

3. **Health Checks**
   - Verify endpoints/services are responding
   - Check logs for errors
   - Monitor resource usage

## Guidelines

- Use Bash to run verification commands
- Use WebFetch to test HTTP endpoints if applicable
- Use Read to examine logs and output
- Document any issues found

## Output

Provide a verification report including:
- Verification steps performed
- Results (pass/fail)
- Any issues found
- Confidence level for production readiness
