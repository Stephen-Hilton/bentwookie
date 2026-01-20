# Validation Stage Learnings

This file contains learnings specific to the validation stage. Stage learnings supersede global learnings (except for interfaces).

## Key Learnings

- Validate from the user's perspective, not just technical correctness
- Include both positive and negative test cases
- Check edge cases that might not have been covered in testing
- Verify logging and monitoring are providing useful data
- Document any discrepancies between expected and actual behavior

## Validation Patterns

### Functional Validation
- Use realistic test data
- Test the complete user workflow, not just individual features
- Verify error messages are helpful and accurate

### Performance Validation
- Establish baseline metrics before validation
- Test under expected load conditions
- Monitor resource usage during validation

### Security Validation
- Verify authentication and authorization work correctly
- Check for common security vulnerabilities
- Confirm sensitive data is handled appropriately

## Common Pitfalls to Avoid

- Don't skip validation just because tests passed
- Don't validate only the happy path
- Don't ignore minor issues - document them all
- Don't rush validation for urgent deployments

## Best Practices

- Create a validation checklist for consistency
- Include stakeholders in validation when possible
- Keep validation evidence for audit purposes
- Update acceptance criteria based on learnings

---
*Add new learnings above this line. Deduplicate before task completion.*
