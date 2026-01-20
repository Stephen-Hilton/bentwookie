# Testing Stage Instructions

You are now in the **Testing Stage** of the BentWookie workflow.

## Your Mission
Create and execute comprehensive tests for the implementation completed in the development stage.

## Context
- **Task Name**: {name}
- **Change Type**: {change_type}
- **Project Phase**: {project_phase}
- **Priority**: {priority}
- **Source Code Location**: {file_paths.project_root}

## Before You Begin
1. Read all markdown files in `tasks/global/*.md` to understand project standards
2. Review the implementation that was completed in the development stage
3. Understand the testing patterns used in the project

## Testing Guidelines

### Types of Tests to Consider
1. **Unit Tests**: Test individual functions and methods in isolation
2. **Integration Tests**: Test component interactions
3. **Edge Cases**: Test boundary conditions and error scenarios
4. **Regression Tests**: Ensure existing functionality isn't broken

### Test Quality Standards
- Tests should be deterministic (no flaky tests)
- Tests should be independent of each other
- Test names should clearly describe what is being tested
- Each test should verify one specific behavior

### Infrastructure Testing
If applicable, test infrastructure integrations:
- Compute: {infrastructure.compute}
- Storage: {infrastructure.storage}
- Queue: {infrastructure.queue}
- Access: {infrastructure.access}

## Your Tasks
1. Write comprehensive unit tests for new code
2. Add integration tests where appropriate
3. Test error handling and edge cases
4. Run the full test suite and ensure all tests pass
5. Document test coverage and any gaps

## Success Criteria
- [ ] All new code has unit test coverage
- [ ] Integration tests cover component interactions
- [ ] Edge cases and error scenarios are tested
- [ ] All tests pass consistently
- [ ] No regressions in existing functionality

## Upon Completion
1. Document any learnings in the Learnings section
2. Note any errors or test failures in the frontmatter `errors` array
3. Update the task status to "Ready" when testing is complete
4. Include a summary of test results

## Important Notes
- Do NOT directly edit the YAML frontmatter (except status updates)
- If tests reveal bugs, document them but fix in this stage if minor
- For major bugs, add to errors and they will be addressed appropriately
