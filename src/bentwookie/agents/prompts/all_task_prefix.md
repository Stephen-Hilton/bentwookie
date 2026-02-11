# !!IMPORTANT!!
- This is designed to run as an autonomous activity, do not stop to ask the user questions.
- Only when ALL tasks are complete, output the safe word: `{safe_word}`
- Do NOT output the safe word until you are genuinely finished.

# Creating Follow-Up Tasks
To add tasks to the AI Swarm Task Queue, include a section like:
TASK_QUEUE_START
agent_type: ca
instructions: |
  Build the auth module...
---
agent_type: ta
instructions: |
  Test the auth module...
TASK_QUEUE_END

Valid agent_type values: ea (Enterprise Architect), ba (Business Architect), se (Service Engineer), ca (Coding Agent), ta (Testing Agent)

Optional fields per task: priority (1-10, default 5), component (component name)

# Task Instructions:
