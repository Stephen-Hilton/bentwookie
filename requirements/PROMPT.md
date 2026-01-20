# Project BentWookie (bw)
Create a robust, intuative, and easy to use python terminal program / package to import into a python script, which will perform setup and implement functions required to run a "ralph wiggums" like AI coding loop.`bw`is more of a "wrapper" around the actual AI loop, which happens in a terminal window.  Instead, `bw` provides supporting functions required to make the loop effective.  

## Summary: User Experience
The high-level user experience should be:
- use the `bw --plan` wizard to quickly create and queue a new task.md in `1plan/`
- as the BW loop runs, the tasks are completed in priority order, automatically
- if tasks run out, BW can continue to refine testing and validation automatically 
- the `tasks/1plan/feature_name.md` file moves through the various stages by moving (`mv`) to different stage subfolders.
- once the file is 100% developed, tested, deployed, and validated, it is moved into `9done` which has no more steps (aka no `.resources/template.md`)
- to restart the process at any stage, simply move the file to that stage subdir

The typical loop will look like:
```bash
while :; do bw --next_prompt "loop name" --tasks "./bw/tasks" | claude ; done
```

Or in Python directly:
```python
import bentwookie as bw

bw.next_prompt()
```


## Build Instructions
I have completed the subdirs and files needed for the first stage: `tasks/1plan/`, which include `1plan/.resources/instructions.md` and `learnings.md` and `template.md`.  
Please extrapolate what `.resources` would be needed for all other stages (2dev, 3test, etc.)
Please generate the BentWookie (bw) application to be run locally

## Other notes: 
- I will register with pypi.org so users can `pip install bentwookie`, so also include any collateral required to upload to pypi.  
- ignore the `!paydaay` folder entirely
- please minimize files saved to the project root
- only when you're 100% done and tested, THEN refresh the README.md


## Feature Flags
Below are the feature flags available to the `bw` terminal command (which should match python functions 1:1):

- **init**: copies over the `tasks/` template folder/file structure to the provided location. 
    - usage: `bw --init ./project/rootdir`
    - usage: `import bentwookie as bw; bw.init('./project/rootdir')`

- **env**: sets the envfile path location. Once the `.env` file is found or created, any missing keys are appended, the path is saved to `tasks/global/settings.yaml` in the "envfile" key, and the `.env` is loaded. Future BentWookie needs of the data will look in the `tasks/global/settings.yaml` file for the correct `.env` file location. 
    - Defaults, used if `bw env` is never set, in the order below:
        - existing file: `./.bwenv`
        - existing file: `./.env`
        - create new file: `./.bwenv`
    - Expected keys include:
        - BW_LLM_PROVIDER: Anthropic, OpenAI, etc. (Default Anthropic)
        - BW_LLM_MODEL:  gpt-5.1-mini, claude-opus-4-5, etc. (default opus 4.5)
        - BW_LLM_API_KEY:  api key for the above provider/model
        - BW_PROJECT_CODE_ROOTPATH: root path where the code project starts
        - BW_TASKS_PATH: root where the`bw``tasks/` directory can be found (defaults to `CWD`)
        - etc. Others as needed
    - usage: `bw --env ./project/rootdir/.env`
    - usage: `import bentwookie as bw; bw.env('./project/rootdir/.env')`

- **logs**: sets the log output path and file pattern, with placeholders. Default is `./logs/bw{today}.log`. Time is based on the TASK start time (aka `bw --next_prompt`) so `{now}` would generate a new log file every iteration, while `{date}` would generate a one log file every day.  Missing directories are dynamically created at runtime.
Viable {options} include, with | aliases:
    - today | date: 'YYYYMMDD' 
    - now | timestamp: 'YYYYMMDD-hhmmdd'
    - hour: 'YYYYMMDD-hh'
    - loopname | loop | name: the "loop name" provided when the loop is started

In addition, log lines will include the loop name, allowing many loops to share one log file:
`{YYYYMMDD-hhmmss.ffffff}-{loop_name}.{function_name}: Message` 

- usage: `bw --logs ./project/rootdir/bwlogs/{loop}.{date}.log`
- usage: `import bentwookie as bw; bw.logs('./project/rootdir/bwlogs/{loop}.{date}.log')`

- **tasks**: sets the `tasks/` folder containing all stages and markdown files required to run BentWookie. This must include the `tasks/` folder itself.  If omitted, then will use CWD.  

- **test**: if this flag is included, `bw` will execute all other commands normally, but will NOT move the `task.md` to the next phase. 


## Functions
Below are functions available to the `bw` terminal command:

- **plan**: creates a new feature plan by name, saves the file, and hands it off to Claude Code Plan Mode. For detail on that process, see the "Appendix: Planning Wizard".  
    - usage: `bw --plan "My New Feature Name"`
    - usage: `import bentwookie as bw; bw.plan("My New Feature Name")`

- **next_prompt**:  Delivers the fully compiled prompt + context to the waiting Claude Code engine. Accepts a "loop name" which is only used for logging / identification.  For more detail on the process, see the "Appendix: BentWookie Loop".
    - usage: `while :; do bw --next_prompt "loop name" | claude ; done`
    - usage: 
        ```python
        import bentwookie as bw; 
        while True: 
            prompt = bw.next_prompt("loop name")
            run_outside_ai_code(prompt)
        ```
 

## Appendix: BentWookie Loop

The loop in a BentWookie Loop is actually managed outside of BentWookie itself. The expected execution model is in bash:
```bash
while :; do bw --next_prompt "loop name" --tasks "./bw/tasks" --logs "./bw/logs" --env "./bw/.env" | claude ; done
```
This does not create the prompt information, it simply grabs the next highest priority task, builds the prompt and returns to the output / stdout, which is then piped into claude code. 


### Loop Name
The "loop name" is only for logging or internal identification, there is no functional change. Any non-file-safe characters will be removed prior to the folder/file substitution. If no loop name is provided, a random 12-character alpha-numeric ID will be assigned.


### Workflow: 

When `next_prompt` is called, it executes the following supporting functions in sequence:
- `tasks = get_all_tasks()`  == all tasks
- `tasks = validate_tasks(tasks)` == all tasks ready for some action
- if `len(tasks) == 0` then call `whitespace_prompt()`
- else:
    - `task = tasks[0]`  == the highest priority single task ready for action
    - `return build_final_prompt(task, "{loop_name}")` == full string prompt


### Supporting Functions
While these functions can be called directly, they really exist to support the `next_prompt`  or `plan` aggregate functions.


## get_task( task_file:Path ) -> dict:
Accepts a Path to a task.md file, parses, validates, and updates data into a dict format.
Actions: 
- load the content of `task_file` 
- parse the frontmatter yaml into dict `task`
- parse all non-frontmatter text and add to `task['markdown']`
- update `task` values:
    - only if `last_update` is missing, set to `datetime.now()`
    - always set `task['file_paths']['task']` to `task_file.resolve()`
    - always set `task['file_paths']['tasks']` to `task_file.resolve().parent.parent`
    - always set `stage` to `task_file.parent.name` only if `task_file.parent.name` begins with a number, otherwise "Unknown"
- error if keys or values missing: `name`, `status`, `file_paths.project_root`, `markdown`
- if any other keys are missing, add them and set to None
- return the  `task` dict 



## save_task( task:dict|Path ) -> dict:
Accepts a task dictionary, or a Path load into a dict with `task = get_task(task)`.
Once we have a dict in all cases:
- restructure the dict into the format seen in `tasks/{stage}/.resources/template.md`, which is:
    - markdown file
    - frontmatter yaml starting at line 1
    - content in `task['markdown']` after yaml
- be sure to maintain the same order and spacing as the `tasks/{stage}/.resources/template.md` file
- create a bkup file, in case the save goes bad; rename the `Path(task['file_paths']['task'])` to `*.bkup`
- save the newly structured task.md file data, overwriting the `Path(task['file_paths']['task'])` file
- reload the `newtask = get_task( Path(task['file_paths']['task']) )` to a new dict, and compare the before/after for differences
- if no errors and all tests pass, remove the *.bkup file and return `newtask` dict
- if there WERE errors, roll back to the *.bkup file and return None



#### get_all_tasks()
Iterate over the subdirectories of `tasks/` and where the subdir begins with a number, then iterate over all markdown (`*.md`) files in those subdirs.  For each markdown file found, try to  `get_task( file )`.  If it doesn't error, add it to the list of tasks to return.  Log all successes and errors.

Returns a list of dicts (tasks).


### task_ready ( task:dict|Path ) -> bool
Accepts a task dictionary, or a Path load into a dict with `task = get_task(task)`.
Once we have a dict in all cases, return whether the supplied task is ready for processing, as a bool True/False.

Tasks are ready for next action when ANY of the below criteria are met:
- `task['status'].lower().startswith( 'ready' )`
- `task['status'].lower().startswith( 'in progress' ) AND datetime.now() < (datetime.fromisoformat(task['last_updated']) + timedelta(hours=24))` (timed out)
- `task['status'].lower().startswith( 'planning' )    AND datetime.now() < (datetime.fromisoformat(task['last_updated']) + timedelta(hours=4))` (timed out)


#### validate_tasks( all_tasks:list ) -> list

Accepts a list of tasks (usually all tasks) and prunes down to only those tasks that are ready for some next action.  It also sorts the list of dictionaries in priority order, so that `validate_tasks( get_all_tasks() )[0]` returns the highest priority task in the list (aka what to do next).

Tasks are ready for next action when `task_ready( task )` returns True

The order of the tasks are determined by:
- `stage`, descending
- `priority`, descending

For example, `3test/` tasks before `2dev`, and `2dev` tasks before `1plan`.  Within each stage, priority 8 goes before 5, which goes before 2.

Return the filtered and sorted list of dicts.



#### get_next_stage( task:dict|Path ) -> str

Accepts a task dictionary, or a Path load into a dict with `task = get_task(task)`.
Once we have a dict in all cases:
- get all subdirectories of `Path( task.task['file_paths']['tasks'] )` that start with a number, and add to a list called `stages`
- Sort `stages`.  Result should look something like ['1plan','2dev','3test','4deploy','5validate','9done']
- Remove any element from `stages` that appears before `task.stage`, including `task.stage` itself
- Return `stages[0]` as a string; this should be the next stage after the current stage
- if `stages` is empty (aka we are at the end), return None




#### move_stage( task:dict|Path, new_stage:str=None ) -> dict

Accepts a task dictionary, or a Path load into a dict with `task = get_task(task)`.
Also accepts a `new_stage` string, defaulting to `get_next_stage(task)` if omitted. 
Once we have a dict in all cases:
- define `new_task_file` as `Path( str(task['file_paths']['task']).replace( task['stage'], new_stage ))`
- MOVE the file `task['file_paths']['task']` to `new_task_file`
- execute and `return save_task( get_task( new_task_file ) )` to refresh all location-dynamic data

usage: `bw move_stage --task "tasks/{stage}/task_file.md"`


#### update_status( task:dict|Path, new_status:str ) -> dict

Accepts a task dictionary, or a Path load into a dict with `task = get_task(task)`.
Also accepts a `new_status` string.
Once we have a dict in all cases:
- update the `status` key with the new value
- execute and return `save_task( task )` to refresh all location-dynamic data

usage: `bw update_status --task "tasks/{stage}/task_file.md" --new_status "Ready"`


#### whitespace_prompt() -> str
In the event that there are NO valid tasks that can be run, this function is called to return a "whitespace" prompt.
This can be anything - maintenace the log files, or review code stylings, or re-validating at random, or just add a joke to the log file. 
In all cases, the whitespace prompt should end with a `time.sleep(600)` to just keep from overwhelming the system, without breaking the loop.
- define a set of whitespace_functions to create, for instance:
    - log file maintenance
    - learning file maintenance
    - randomly select tests to bolster and re-run 
    - randomly select validations to bolster and re-run 
    - build a report on performance
    - make recommendations on future enhancements
    - perform web research on similar projects
    - add jokes to the log file
    - just do nothing
    - etc. 
- `time.sleep(600)`
- Return the prompt to run.

The whitespace_functions can be coded to be deterministic, but remeber the output of this function is a prompt, so AI can be engaged to perform fuzzy maintenance as well.
If the whitespace_function is 100% deterministic, return 'do nothing' as the prompt.



#### build_final_prompt( task:dict|Path, loop_name ) -> str

Accepts a task dictionary, or a Path load into a dict with `task = get_task(task)`.
Also accepts a `loop_name` string, defaulting to random 12 alphanum characters.
Once we have a dict in all cases:
- confirm task status (removes race conditions):
    - update `status` to "planning implementation phase - {loop_name}" replacing loop_name
    - update `last_updated` to now()
    - `save_task(task)`
    - sleep for a random number of milliseconds, between 1 and 2000 (between 1ms and 2s)
    - `task = get_task( Path(task['file_paths']['task']) )`
    - check `status` to make sure it still equals "planning implementation phase - {loop_name}" replacing loop_name
        - If changed, return 'do nothing' and exit; conflict between loops avoided
- load the content of markdown file `tasks/{task['stage']}/.resources/instructions.md` into a string called `instructions`
- move task to next stage with `task = move_stage( task )` 
- do find/replace of "{key_placeholder}" with `task['value']`
    - for each key:value in dictionary `task` (and sub-dictionaries):
        - find/replace any {key_placeholder} with corresponding `task['value']` in string `instructions`, in place
        - find/replace any {key_placeholder} with corresponding `task['value']` in string `task['markdown']`, in place
    - multiple dict levels are delimited by periods, i.e., "{file_paths.task}" placeholder is replaced with `task['file_paths']['task']`
    - e.g., in the string `... this markdown file: '{file_paths.task}'` the substring "{file_paths.task}" will be replaced with `task['file_paths']['task']`, resulting in `... this markdown file: './tasks/1plan/New Feature ABC.md'`
- in `task['markdown']` find "{instructions}" and replace with the markdown string `instructions`
- load the content of markdown file `tasks/{task['stage']}/.resources/learnings.md` into a string called `learnings`
- in `task['markdown']` find "{learnings}" and replace with the markdown string `learnings`
- save and refresh with `task = save_task (task)`

Finally, load and return the string content of the markdown file `Path(task['file_paths']['task'])`, which should now be the completed full prompt, with all placeholders substituted. 



## Appendix: Planning Wizard

This list of questions are designed to help get the user started quickly, and ensure the output of the claude code planning process adheres to `bw` data requirements. The wizard is designed to be brief, with common choices presented and defaulted, to help make this process fast.

Multiple choice questions should always look up their list of viable responses from the `tasks/global/settings.yaml` file, but keep and display only the latest 9 responses, in last-use order, meaning option #1 is always the responses you selected last time.  If there are more than 9 options, allow the user to press 'm' for more, and display the entire list, in alphabetic order. 

The last option in the list should alway be "Other", and if selected allows users to enter a very brief (<50 word) name for a new option, which should then get saved to that `settings.yaml` file, making it available to all future wizard settings. 

The multiple question options shown below are for example only - always pull latest from `tasks/global/settings.yaml`.

Navigation buttons should include: left/right arrow for moving to the prev/next question, and 'Enter' key always saves the answer to the current question, and brings up the next question. For multiple choice questions, the down arrow is an alias for 'm' and displays all options for a multiple choice question, and pressing any number key (0-9) will select that option and move on to the next question (implicit 'Enter').  Every Enter, whether implicit or explicit, should save the response, including re-ordering the `settings.yaml` so the last-selected option is on top.  Thus, if the user select option #5 for Q3, #2 for Q4, then the left-arrow to return to Q3, option #5 is now the default option #1.

Unless otherwise noted, questions should default to the last answer given.  This last-state is stored in the `settings.yaml` file under the `last_selected` object. 

Because some of the questions are escaped depending on earlier responses, do not number the questions. The headers below are for development clarity only.


### Q1
Confirm the name of the name of your change: {default: parameter provided}

**Internal Notes:**
Answer to this question becomes the name of the new `1plan/feature_name.md` file, stripped of any filename-unsafe characters.  It also appears verbatim in the frontmatter yaml file, on the very first line: `name: feature_name`
It is NOT saved to the `global/settings.yaml`.


### Q1.1
Confirm the location of the source code to modify:

**Internal Notes:**
If no default exists or is empty, default to `./`
Answer saved to the new `1plan/feature_name.md` file in the frontmatter yaml section under `task['file_paths']['project_root']`.
It is also saved to the last_selected value updated in `global/settings.yaml`.


### Q2
Is this request a...
1. new feature
2. feature enhancement
3. bug-fix
4. Other

**Internal Notes:**
Answer saved to the new `1plan/feature_name.md` file in the frontmatter yaml section under `task['status']`.
It is also saved to the last_selected value updated in `global/settings.yaml`.

If the selection is "bug-fix" then skip all "infrastructure" questions.  


### Q3
Project phase is...
1. MVP
2. V1.0
3. POC
4. Other

**Internal Notes:**
Answer saved to the new `1plan/feature_name.md` file in the frontmatter yaml section under `task['project_phase']`.
It is also saved to the last_selected value updated in `global/settings.yaml`.


### Q4
Between 1 and 10, what is the priority of this request? 
(1 = lowest/optional, 10 = highest /critical)

**Internal Notes:**
Answer saved to the new `1plan/feature_name.md` file in the frontmatter yaml section under `task['priority']`.
It is also saved to the last_selected value updated in `global/settings.yaml`.


### Q5
Infrastructure:  What COMPUTE stack do you want?
1. AWS Lambda
2. AWS EC2
3. AWS Serverless
4. AWS ECS 
5. Local Container
6. Local Code Only
7. Don't Care
8. Other

**Internal Notes:**
Answer saved to the new `1plan/feature_name.md` file in the frontmatter yaml section under `task['infrastructure']['compute']`.
It is also saved to the last_selected value updated in `global/settings.yaml`.


### Q6
Infrastructure:  What STORAGE stack do you want?
1. AWS AuroraDB
2. AWS DynamoDB
3. AWS S3 Bucket
4. Local File System
5. Local Container File System
7. Don't Care
8. Other

**Internal Notes:**
Answer saved to the new `1plan/feature_name.md` file in the frontmatter yaml section under `task['infrastructure']['storage']`.
It is also saved to the last_selected value updated in `global/settings.yaml`.



### Q7
Infrastructure:  What QUEUE stack do you want?
1. None (push only)
2. AWS Kinesis
3. AWS MSK (Kafka)
4. AWS EC2 Kafka / K8
5. AWS SQS
6. AWS EventBridge
7. AWS Step Functions
8. Local Kafka  
9. Don't Care
0. Other

**Internal Notes:**
Answer saved to the new `1plan/feature_name.md` file in the frontmatter yaml section under `task['infrastructure']['queue']`.
It is also saved to the last_selected value updated in `global/settings.yaml`.



### Q8
Infrastructure:  What ACCESS path do you want?
1. AWS API Gateway (secure)
2. AWS API Gateway (public)
3. AWS Direct Lambda Connect
4. Direct Compute Connection
5. Pulls from Queue
6. Don't Care
0. Other

**Internal Notes:**
Answer saved to the new `1plan/feature_name.md` file in the frontmatter yaml section under `task['infrastructure']['access']`.
It is also saved to the last_selected value updated in `global/settings.yaml`.

At this point, the `1plan/name.md` file should be created and all options now updated.


### Q9
Last Step!  Type a few sentances describing this request.  
For example, "There is a bug in the current feature X, whereby it always returns 1 more than appropriate."

FYI, this information will be handed off to the Claude Code Planning Agent.

**Internal Notes:**
Answer saved to the new `1plan/feature_name.md` file in the markdown section, replacing the placeholder text: "{user_request}".
This does NOT get saved in `global/settings.yaml`.


### Confirmation
Let's verify everything looks right!  
Below is what you selected - Press Enter to Accept.  Or, you can go back and change answers with the left-arrow.

- Name:     Some Feature Name
- Type:     New Feature
- Phase:    MVP
- Priority: 5 (out of 10)
- Code Found at: ((.env: BW_CODE_PROJECT_ROOTPATH))
- Infrastructure Preferences: ((if not bugfix))
  - Compute: AWS Lambda
  - Storage: AWS AuroraDB
  - Queue:   AWS Kinesis
  - Access:  Pulls from Queue
- Instructions: 
> There is a bug in the current feature X, whereby it always returns 1 more than appropriate.


### Next Steps
Congratulations! You've completed the new request setup, and it has been added to the BentWookie task queue!

If you have a BW loop already running, nothing more to do!  Simply monitor and wait for the job to be completed.
 
If you need to start a new BentWookie loop:
```bash
while :; do bw --next_prompt "loop name" | claude ; done
```

Thanks for playing!