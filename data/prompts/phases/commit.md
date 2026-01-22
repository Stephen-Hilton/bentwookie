# Commit Phase

**Project**: {project_name} (v{project_version})
**Request**: {request_name}
**Type**: {request_type}

## Objective

Create a meaningful git commit for the changes made in this request.

## Instructions

1. **Review Changes**:
   - Use `git status` to see all modified, added, and deleted files
   - Use `git diff` to review the actual changes
   - Note: The working directory is: `{code_dir}`

2. **Generate Commit Message**:
   - Write a clear, concise commit message that follows best practices
   - Format:
     ```
     <type>: <short summary (50 chars or less)>

     <optional detailed description>

     Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
     ```
   - Types: feat, fix, docs, style, refactor, test, chore
   - Reference the request: "{request_name}"

3. **Create Commit and Push**:
   - Stage all relevant changes with `git add <files>`
   - Create commit with meaningful message
   - Push to remote: `git push origin <branch>`
   - Handle push failures gracefully (log warning, don't fail phase)

4. **Report**:
   - Output the commit hash
   - Output the commit message
   - List files included in commit

## Important Notes

- If no changes are detected (clean working directory), skip commit creation
- If git repository is not initialized, skip with warning
- Use HEREDOC for commit messages to handle multi-line properly:
  ```bash
  git commit -m "$(cat <<'EOF'
  Your commit message here
  EOF
  )"
  ```
- After commit, push to remote with `git push origin <branch>`
- If push fails (conflicts, no remote, etc.), log warning but don't fail phase
- Detect if branch has upstream tracking; if not, use `git push -u origin <branch>`

## Current State

**Code Directory**: {code_dir}
**Branch Mode**: {branch_mode}
**Target Branch**: {target_branch}
