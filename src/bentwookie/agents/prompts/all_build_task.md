# Build Task: {task_type} — {cmp_name}

## Component Description
{cmp_desc}

## Component Specification
{cmp_spec}
{conn_section}
{test_section}
## Instructions

You are a {role_name}.
Your task is to **{task_type}** the component "{cmp_name}".

- Follow the specification exactly.
- Write runnable tests alongside your implementation.
- Do not make architectural decisions — the design is locked.
- If you discover a conflict with the spec, flag it immediately.

When you are done, output the safe word: `{safe_word}`
If you encounter an error you cannot resolve, output: TASK_FAILED: <reason>
