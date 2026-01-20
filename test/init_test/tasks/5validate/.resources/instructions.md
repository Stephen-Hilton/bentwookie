# Validation Stage Instructions

You are now in the **Validation Stage** of the BentWookie workflow.

## Your Mission
Validate that the deployed implementation meets all requirements and functions correctly in the production environment.

## Context
- **Task Name**: {name}
- **Change Type**: {change_type}
- **Project Phase**: {project_phase}
- **Priority**: {priority}
- **Source Code Location**: {file_paths.project_root}

## Before You Begin
1. Read all markdown files in `tasks/global/*.md` to understand validation standards
2. Confirm deployment completed successfully in the previous stage
3. Review the original requirements and acceptance criteria

## Validation Guidelines

### Validation Types
1. **Functional Validation** - Verify the feature works as specified
2. **Performance Validation** - Check response times and resource usage
3. **Security Validation** - Verify security controls are in place
4. **Integration Validation** - Confirm interactions with other systems

### Acceptance Criteria Review
Verify against the original user request:
- Does the implementation address the stated problem?
- Are all specified features working?
- Are there any unintended side effects?

## Infrastructure Validation
Validate infrastructure components are functioning:
- **Compute**: {infrastructure.compute}
- **Storage**: {infrastructure.storage}
- **Queue**: {infrastructure.queue}
- **Access**: {infrastructure.access}

## Your Tasks
1. Execute functional validation tests
2. Verify performance meets requirements
3. Confirm security controls are active
4. Test integration points with other systems
5. Document validation results

## Success Criteria
- [ ] All functional requirements are met
- [ ] Performance is within acceptable limits
- [ ] Security controls verified
- [ ] No regressions in existing functionality
- [ ] Documentation is complete

## Upon Completion
1. Document any learnings in the Learnings section
2. Note any validation failures in the frontmatter `errors` array
3. Update the task status to "Complete" when validation passes
4. Provide a summary of validation results

## Final Steps
If validation passes:
- The task will be moved to `9done`
- Update any final documentation
- Celebrate the successful completion!

If validation fails:
- Document the failures clearly
- The task may need to return to an earlier stage

## Important Notes
- Do NOT directly edit the YAML frontmatter (except status updates)
- Be thorough - this is the last check before completion
- Include evidence of validation (logs, screenshots, etc.) where helpful
