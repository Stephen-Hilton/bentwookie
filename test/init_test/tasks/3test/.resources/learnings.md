# Testing Stage Learnings

This file contains learnings specific to the testing stage. Stage learnings supersede global learnings (except for interfaces).

## Key Learnings

- Use the project's existing test framework and patterns
- Mock external dependencies to keep tests fast and reliable
- Test both happy path and error cases
- Use meaningful test data that reflects real-world scenarios
- Group related tests together logically

## Testing Patterns

- Use fixtures for common test setup
- Prefer explicit assertions over implicit ones
- Test public interfaces, not private implementation details
- Use parameterized tests for similar test cases with different inputs

## Common Pitfalls to Avoid

- Don't write tests that depend on test execution order
- Don't test implementation details - test behavior
- Don't skip testing error cases
- Don't leave commented-out tests in the codebase

## Best Practices

- Aim for meaningful coverage, not just high percentages
- Keep test files organized and easy to navigate
- Clean up test data after tests complete
- Document why certain edge cases are being tested

---
*Add new learnings above this line. Deduplicate before task completion.*
