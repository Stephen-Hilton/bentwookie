## Instructions for Planning
ENTER PLAN MODE

Carefully review the validated user requirements, both in the structured frontmatter yaml format, which contains validated user requirements, and in the freeform "User Request" markdown. Begin planning for code implementation.

## Implemntation Plan File Location
You MUST write your implementation plan to this markdown file:
`{file_paths.task}`
Under the section "Implementation Plan". 

## Success Criteria
Check these success critieria after each planning iteration:
- Create a full implementation plan that aligns with the user's stated goal in:
    - the frontmatter yaml (aka structured requirements)
    - the "User Request" section (freeform description)
- Implementation plan must been saved to `{file_paths.task}`

## Document Errors / Learnings
Anytime you make an important learning about planning, append a note to the `tasks/1plan/.resources/learnings.md`.
This could be an error / resolution, or a short-cut discovered, or important feedback from the user. 
Anything that will help future agents create working implementation plans in the future. 

## IMPORTANT!!!
- Do NOT directly edit the frontmatter yaml
- Do NOT ask user to continue to implementation
- Do NOT ask user to begin development
- DO offer to update the status to "Ready for Implementation" which adds it to the `bw` work queue
- ONLY examine and use for context files in the folder `{file_paths.project_root}`
- ONLY modify files in the folder `{file_paths.project_root}`

To update the status of this task:
```bash
bw update_status --task "{file_paths.task}" --new_status "{new_status}"
```
