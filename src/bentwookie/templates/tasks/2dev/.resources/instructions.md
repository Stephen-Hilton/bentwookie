# Development Stage Instructions

You are now in the **Development Stage** of the BentWookie workflow.

## Your Mission
Implement the feature or fix described in this task according to the implementation plan created during the planning stage.

## Context
- **Task Name**: {name}
- **Change Type**: {change_type}
- **Project Phase**: {project_phase}
- **Priority**: {priority}
- **Source Code Location**: {file_paths.project_root}

## Before You Begin
1. Read all markdown files in `tasks/global/*.md` to understand project standards
2. Review the implementation plan in the "Implementation Plan" section below
3. Understand the existing codebase structure and patterns

## Development Guidelines

### Code Quality
- Follow existing code patterns and conventions in the project
- Write clean, readable, self-documenting code
- Add comments only where logic is non-obvious
- Follow the project's naming conventions

### Infrastructure Requirements
- Compute: {infrastructure.compute}
- Storage: {infrastructure.storage}
- Queue: {infrastructure.queue}
- Access: {infrastructure.access}

### Standard Data Format
Always use the Standard Data Format (SDF) for inter-component data passing as defined in `tasks/global/interfaces.md`.

## Your Tasks
1. Implement the feature/fix according to the plan
2. Ensure code follows project standards
3. Add appropriate error handling
4. Update any relevant documentation inline
5. Prepare the code for testing

## Success Criteria
- [ ] Feature/fix is fully implemented
- [ ] Code follows project conventions
- [ ] No linting or type errors
- [ ] Error handling is in place
- [ ] Code is ready for testing

## Upon Completion
1. Document any learnings in the Learnings section
2. Note any errors encountered in the frontmatter `errors` array
3. Update the task status to "Ready" when development is complete

## Important Notes
- Do NOT directly edit the YAML frontmatter (except status updates)
- Do NOT ask for continuation - complete the implementation in this session
- Focus on the specific task defined; avoid scope creep
