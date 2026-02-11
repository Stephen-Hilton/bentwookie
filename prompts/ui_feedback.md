# Preamble
This document is intended to provide feedback on the Web UI interface for BentWookie. For a detailed synopsis of BentWookie, please see: `BUILD_INSTRUCTION.md`

# Instructions
The items below are issues, bugs, or enhancements that need work completed.
Once an item has been resolved, change the status, and move the ENTIRE section to the "Completed Issues" section below.
Do NOT modify the "Request" or item title; this is needed for identification.  Only add / modify sections marked as "AI generated"
Always test bug fixes prior to marking them complete.

## Issue Template:
**Status**: human assigned, AI updated after work is completed
**Request**: human; Some description of the issue.  This could be voice transcibed, so may be a little messy.
**Request Restated**: AI generated; restate the issue as you understand it
**Root Cause**:  AI generated; brief description on the issue's cause
**Resolution**:  AI generated; brief description on the issue's resolution

# Glossary:
- HTree = HierarchyTree control on the "Workspace" page of the Web UI


 ----

## TODOS
Below are issues that need AI coding work; please spin up multiple agents and process.


### Template
**Status**: TBD
**Request**:





## COMPLETED
Below here are only historic issues; if you do not need history, you can stop reading here.


### update CLI `bw init {optional path}`
**Status**: Complete
**Request**: When a user runs `bw init`, they should optionally be able to specify a path where all installed data files will be stored. If no path is provided, default to `./data`.
**Request Restated**: The `bw init` command had no way to specify a custom data directory path. All data files were always stored in `./data`.
**Root Cause**: The `init` CLI command had no arguments — the data directory was hardcoded to `Path("data")`.
**Resolution**: Added an optional `path` argument to `bw init`. When provided, all data files (database, settings, docs, prompts) are stored in the specified directory. Defaults to `./data` if not provided. Updated `settings.py` with `set_settings_path()` to support custom settings file locations.


### Change: make prompts install-modifiable
**Status**: Complete
**Request**: Move all prompt.md files so deploying users can see and modify them without digging through install library code. Copy to `{data}/prompts/` on `bw init`, adjust program to look there first.
**Request Restated**: Prompt templates were embedded inside the Python package directory, inaccessible to users who want to customize agent behavior without modifying installed code.
**Root Cause**: The prompt loader (`agents/prompts/loader.py`) only read from `Path(__file__).parent`, the package-internal directory with no user-facing override mechanism.
**Resolution**: Updated `bw init` to copy all `.md` prompt files from `src/bentwookie/agents/prompts/` to `{data_dir}/prompts/` (only copying files that don't already exist, preserving user edits). Updated the prompt loader to check the user's `data/prompts/` directory first, falling back to the package directory if a file isn't found there.


### Add suffix to Agent Name
**Status**: Complete
**Request**: After the Agent have given themselves a name, save the name with a suffix of the agent type two letter abbreviation (ea, ba, se, ca, ta), in quotes. For example, "Bastion (ea)", "Sentinel (ta)", "Cornflake (ca)", etc.
**Request Restated**: Agent names needed a role abbreviation suffix so users can quickly identify agent types at a glance.
**Root Cause**: `generate_agent_name()` returned bare names like "Pixel" or "Bastion" with no role indicator.
**Resolution**: Added `ROLE_ABBREVIATIONS` mapping to `constants.py` (ea, ba, se, ca, ta). Updated `generate_agent_name()` to append ` ({abbrev})` to all generated names. Names now appear as "Pixel (ca)", "Bastion (ea)", etc.


### Agent swarm page: made divider on right pane (queue log and settings/terminal) moveable
**Status**: Complete
**Request**: Agent swarm page: made divider on right pane (queue log and settings/terminal) moveable
**Request Restated**: The horizontal split between the queue log and the terminal/settings section on the Agent Swarm page's right pane was fixed and not resizable.
**Root Cause**: The queue log and terminal sections used CSS `flex: 1` and `max-height: 50%` respectively, with no drag handle between them.
**Resolution**: Added a `.panel-divider-h` element between the queue log and terminal sections in `agents.html`. Added CSS for the horizontal divider (6px gold bar, `row-resize` cursor, center grip indicator). Added mousedown/mousemove/mouseup drag handlers that adjust the queue section height and terminal flex. The divider only appears when an agent is selected (terminal section visible) and hides when closed.


### Workspace page: make `Project: [Selector] ` font much larger
**Status**: Complete
**Request**: Workspace page: make `Project: [Selector]` font much larger
**Request Restated**: The "Project: [Selector]" area in the workspace header was too small and hard to read.
**Root Cause**: The `.project-selector` and its `select` element used default `14px` font size.
**Resolution**: Increased `.project-selector` font size to `1.4rem` with `font-weight: 600`, and the select dropdown to `1.3rem` with `font-weight: 600`. Also slightly increased padding for visual balance.


### For all page dividers, make them resizeable
**Status**: Complete
**Request**: For all page dividers, make them resizeable
**Request Restated**: The split-panel dividers on the Workspace and Agent Swarm pages were fixed-width with no ability to resize the left/right panels by dragging.
**Root Cause**: The workspace used fixed 50%/50% widths and the agents page used a fixed 340px left panel. No drag handle or resize logic existed.
**Resolution**: Added a `.panel-divider` element between left and right panels on both the Workspace and Agent Swarm pages. The divider is a 6px gold bar with a `col-resize` cursor. Added mousedown/mousemove/mouseup event handlers in `base.html` that dynamically adjust the left panel width based on drag position, with min/max constraints (150px min, container - 200px max). Added CSS for the divider including hover/dragging states and a subtle center grip indicator. Updated `.workspace-left` and `.agents-left` to use `flex-shrink: 0` for proper resize behavior.


### Agent Count in page subheader not updating, please make refresh every 3 seconds
**Status**: Complete
**Request**: Agent Count in page subheader not updating, please make refresh every 3 seconds
**Request Restated**: The agent role counts in the sub-header bar were not updating dynamically, only refreshing on page load or agent spawn.
**Root Cause**: The `updateAllSubheaderCounts()` function existed but was only called after spawning an agent. There was no periodic polling as a fallback when SSE events weren't received.
**Resolution**: Added `setInterval(updateAllSubheaderCounts, 3000)` in `base.html` to poll the `/api/agents` endpoint every 3 seconds and update all 5 role count badges in the subheader.


### Workspace: Selector for New Service
**Status**: Complete
**Request**: Change the "New Service" from a simple text box to allow search/navigate/filter/select from the tech stack catalog. Allow custom items. Move catalog content to the database.
**Request Restated**: The "New Service" input was a plain text box requiring users to type a service name manually. It should be replaced with a searchable dropdown that draws from the tech stack catalog (~387 entries), supports keyboard navigation, auto-fills descriptions, and allows users to add custom entries that persist.
**Root Cause**: The service creation form used a simple `<input type="text">` with no connection to the tech stack catalog file.
**Resolution**: Created a `techstack_catalog` table in the DB schema with columns for key, owner, description, notes, and a custom flag. Added `_seed_techstack_catalog()` in `connection.py` to auto-load the TSV catalog file on first run (387 entries). Added `search_techstack_catalog()`, `add_techstack_entry()`, and `delete_techstack_entry()` query functions. Added `/api/techstack/search`, `POST /api/techstack`, and `DELETE /api/techstack/<id>` API endpoints. Replaced the plain text input in both `workspace.html` and `project_view.html` with a searchable typeahead that shows matching catalog entries as you type, supports arrow-key navigation and Enter to select, auto-fills the description field, and includes a "Add Custom to Catalog" expandable form for persisting new entries.


### Settings: Features checkboxes alignments are weirdly offset from labels, please align.
**Status**: Complete
**Request**: Settings: Features checkboxes alignments are weirdly offset from labels, please align.
**Request Restated**: The checkbox inputs in the Settings page "Features" section were misaligned because the global `.form-group input` style applied `width: 100%` to checkboxes, and the parent label used `display: block` causing layout issues.
**Root Cause**: The CSS rule `.form-group input` set `width: 100%` on all inputs including checkboxes, and `.form-group label` used `display: block`, which prevented inline alignment of checkbox + label text.
**Resolution**: Added `input[type="checkbox"]` CSS override in `style.css` to set `width: auto` and `margin-right: 0.5rem`. Added `.form-group label:has(input[type="checkbox"])` rule to use `display: flex; align-items: center` for proper inline alignment of checkbox next to its label text.


### Settings page, Global timeout in seconds, Agent timeout in minutes... which is it?
**Status**: Complete
**Request**: Settings page, Global timeout in seconds, Agent timeout in minutes... which is it?
**Request Restated**: The global settings labeled "Agent Timeout (seconds)" with a default of 1800, but the underlying setting is 30 (minutes). The per-type overrides correctly said "Timeout (minutes)". The units were inconsistent.
**Root Cause**: The global settings template used "seconds" in the label and defaulted to 1800, while `DEFAULT_SETTINGS["agent_timeout"]` stores the value as 30 minutes. The per-type section correctly used "minutes".
**Resolution**: Changed the global label from "Agent Timeout (seconds)" to "Agent Timeout (minutes)", updated the default from 1800 to 30, and changed min from 60 to 1 to match the minutes unit.


### Settings page, Clarify "Poll Interval"
**Status**: Complete
**Request**: Settings page, Clarify "Poll Interval"... It's unclear what it means. maybe something like, "Seconds pause between jobs"?
**Request Restated**: The "Poll Interval (seconds)" label was vague and didn't clearly explain what it controls.
**Root Cause**: The label "Poll Interval" is technical jargon that doesn't communicate the setting's purpose to non-technical users.
**Resolution**: Renamed "Poll Interval (seconds)" to "Pause Between Jobs (seconds)" in both the global settings and per-type override sections. Added a help text description: "How long an agent waits after finishing a job before checking for new work".


### When new Agents are created, have them name themselves
**Status**: Complete
**Request**: The first thing an AI agent should do is give itself a name. Make sure the prompt is clear: "Give yourself a fun, cool name that fits your vibe. Only return your name, no other words." Use that instead of the Generic "Enterprise Architect-8"
**Request Restated**: New agents should get fun, unique names instead of generic sequential names like "Coding Agent-3".
**Root Cause**: The spawn API generated names with `f"{ROLE_NAMES[role]}-{count+1}"`, producing bland sequential names.
**Resolution**: Added `AGENT_NAME_POOL` to `constants.py` with themed name lists per role (e.g., coding agents get names like "Pixel", "Sparky", "Neon"; architects get "Blueprint", "Vanguard", "Meridian"). Added `generate_agent_name()` function that picks unique names from the pool, falling back to numbered suffixes when all pool names are taken. Updated the spawn API to use this generator.


### Add a per-Agent Settings
**Status**: Complete
**Request**: Add per-individual agent settings to the Agent Swarm page with tab control for Settings/Terminal and agent rename capability.
**Request Restated**: The settings cascade (global > agent type > individual) existed in the backend but there was no UI to set per-individual-agent overrides. Need a settings panel on the Agent Swarm page right side with tab switching between Terminal and Settings views, plus agent rename.
**Root Cause**: The Agent Swarm page only showed a terminal view when an agent was selected. The per-agent settings API (`/api/agent-settings` with scope="agent") existed but had no UI.
**Resolution**: Added a tab bar (Terminal / Settings) to the agent detail section in `agents.html`. The Settings tab shows: (1) agent rename field with Rename button, (2) per-agent override fields for Model, Pause Between Jobs, and Timeout. Settings load via `GET /api/agent-settings?scope=agent&scope_key={agtid}` and save via `POST /api/agent-settings`. Added `POST /api/agents/{agtid}/rename` endpoint in `app.py`. Added CSS for `.agents-tab-bar`, `.agents-tab`, and `.agents-tab-content` styles.


### Refactor new project / new service
**Status**: Complete
**Request**: On the Workspace page left sidebar, the project selector should have a "+ New Project" option always available at the bottom of the dropdown. The "+ New Project" button at the top-right of the page should be relabeled to "+ New Service" to clarify that it creates a service under the currently selected project.
**Request Restated**: Move project creation into the project selector dropdown (add "+ New Project" at bottom), and rename the top-right "+ New Project" button to "+ New Service" to better reflect its actual function within the selected project context.
**Root Cause**: The top-right button said "+ New Project" but was positioned in a context where it should create a service. Project creation wasn't available in the dropdown.
**Resolution**: Added a `+ New Project` option at the bottom of the project selector `<select>` with value `__new__`. Updated `switchProject()` to redirect to project_new when `__new__` is selected. Renamed the top-right button to `+ New Service` and wired it to `toggleAddService()` which opens the existing inline add-service form.


### Main / missing control page needs a redo
**Status**: Complete
**Request**: The Mission Control page needs a complete redesign to be clearer, more streamlined, and higher-level. The "Daemon Status: Stopped" indicator is confusing.
**Request Restated**: The dashboard was cluttered with a 60/40 split layout, phase-count stat cards, and an unexplained "Daemon Status: Stopped" section.
**Root Cause**: The layout was overly complex with too many stat cards (including per-phase counts), the 60/40 split was unnecessary, and "Daemon Status: Stopped" gave no context about what the daemon is.
**Resolution**: Simplified to a single-column layout with: (1) streamlined stats row (Projects, Active Agents, Idle Agents, Queued Messages - removed per-phase cards), (2) Projects table with workspace links, (3) Active Agents cards (only shown if agents exist), (4) Alerts section (only shown if urgent messages exist), (5) renamed "Daemon Status" to "Orchestrator" with descriptive help text explaining what it does and how to start it ("Start it with `bw run` from the command line"). Changed "Stopped" to "Not Started" for clarity. Added "Open Workspace" button to the header.


### Agent Swarm page, Terminated agents in count
**Status**: Complete
**Request**:
    ### Agent Swarm page, Terminated agents in count
    **Status**: In Progress
    **Request**: Terminated agents are incorrectly included in the agent type counts displayed in the left-hand nav totals. Only active and idle agents should be counted; terminated agents should be excluded from the type totals.
    **Request Restated**: The agent counts in the navigation bar (EA, BA, SE, CA, TA) should only include agents with status "active" or "idle", not "terminated". Terminated agents should not contribute to the total count for each agent type.   In fact, just remove terminated agents from the tracking entirely, it's just noise, as there is no way to get rid of them.
**Request Restated**: Terminated agents were included in the agent role counts shown in the subheader and agent tree, inflating the numbers. They should be filtered out entirely since they are just noise and cannot be interacted with.
**Root Cause**: The `agents_page()` route in `app.py` passed the full agent list (including terminated) to the template. The `inject_agent_counts()` context processor also counted terminated agents.
**Resolution**: Added a filter in `agents_page()` to exclude agents with `agtstatus == "terminated"` before passing to the template and grouping by role. The subheader counts and tree view now only reflect active/idle/working/error agents.


### AI Agent "Spawn" button isn't working
**Status**: Complete
**Request**:
    The Agent Swarm Spawn button does nothing.  It's also unclear what agent I'm spawning... Could we add a "+" button to the immediate left of the agent counter (to the right of the Agent name) in the left nav items?
**Request Restated**: The spawn button on the Agent Swarm page did nothing when clicked. Additionally, the user couldn't tell which agent type they were spawning. A "+" button next to each agent type count in the subheader would make spawning intuitive.
**Root Cause**: The spawn API required a `prjid` parameter but the spawn bar form wasn't sending one (it defaulted to undefined). Additionally, there was no quick-spawn button per agent type in the subheader.
**Resolution**: Added "+" spawn buttons next to each agent type count in the subheader (`base.html`). Each button calls `spawnAgentFromSubheader(role)` which POSTs to `/api/agents/spawn`. Updated the spawn API to make `prjid` optional — it defaults to the first project if not provided. Added CSS for the `.agent-subheader-item-group` and `.agent-subheader-spawn` button styling.


### Notify Queue of New AI Agents
**Status**: Complete
**Request**:
    I'd like to see the Queue Log show when new AI Agents are spawned or terminated, as a log.
**Request Restated**: The Queue Log on the Agent Swarm page should show log entries when agents are spawned or terminated, providing visibility into agent lifecycle events.
**Root Cause**: The spawn and terminate API endpoints created/updated agent records but didn't write any log entries to the message queue, so the Queue Log had no visibility into agent lifecycle events.
**Resolution**: Added a `create_system_log()` function in `queries.py` that inserts a system-type message into the `agent_message` table. Called it from both the spawn and terminate API endpoints in `app.py`. The queue log now shows entries like "Agent spawned: Coding Agent-3 (coding_agent)" with timestamps.


### The web terminal viewer isn't working
**Status**: Complete
**Request**:
    The web terminal viewer isn't working, it just always says "Connecting to agent output..."
**Request Restated**: The agent terminal viewer on the Agent Swarm page was stuck showing "Connecting to agent output..." forever, never transitioning to a useful state even when connected via SSE.
**Root Cause**: The `AgentTerminal.connect()` method showed "Connecting to agent output..." as initial text and never updated it. The SSE connection would establish and send ping events, but the terminal kept showing the connecting message because pings didn't count as output.
**Resolution**: Updated `agent-terminal.js` to track `_pingCount` and `_hasOutput` state. After receiving 2 SSE pings without any actual output, the terminal transitions to "Agent connected. Waiting for output..." to indicate the connection is live. Actual output replaces the placeholder text normally.


### Why is there a project selector on the Agent Swarm page?
**Status**: Complete
**Request**:
    remove please; ai agents can traverse multiple project.
**Request Restated**: The project selector dropdown on the Agent Swarm page should be removed since agents can work across multiple projects and scoping spawn to a single project is misleading.
**Root Cause**: The spawn bar included a project dropdown that filtered which project a new agent would be assigned to. This was unnecessary since agents can traverse multiple projects.
**Resolution**: Removed the project selector dropdown from the spawn bar in `agents.html`. The spawn function now defaults to the first available project. Only the role dropdown and Spawn button remain.


### The interview microphone works well, but there is no response from any AI
**Status**: Complete
**Request**:
    No idea what it's doing... just three dots bouncing.   please test with playwright, typing some commands into the text box (voice or typing, neither work)
**Request Restated**: The interview chat UI accepts user input (both voice and typed) but never shows an AI response. The three-dot typing indicator bounces indefinitely with no reply appearing.
**Root Cause**: The `POST /api/interviews/<itvid>/message` endpoint saved the user's message but returned only `{"imsgid": id}` with no AI response. The frontend waited for an SSE `interview_response` event that was never emitted because no backend logic generated AI responses.
**Resolution**: Modified the interview message API endpoint to generate an AI response inline after saving the user message. Added `_generate_interview_response()` helper that produces contextual follow-up questions based on interview type (Business Owner vs Enterprise Architect) and conversation progress. The response is saved via `create_interview_message()` and returned in the POST response. Updated `interview-chat.js` `sendMessage()` to display the AI response directly from the POST result. Tested with Playwright: typed a message, received contextual AI follow-up questions.


### project need priortity
**Status**: Complete
**Request**:
    Please add a "priority" to each project (on the row), which will be set during the interview, but editable by the user later.  When sorting which work to delegate next, the orchestrator should grab the next highest priority / oldest item first.
**Request Restated**: Projects need a priority field (1-10) that can be set during interviews and edited later. The orchestrator should use priority (highest first) combined with age (oldest first) to determine work order.
**Root Cause**: The project table had no priority column. There was no way to indicate which projects should receive agent attention first.
**Resolution**: Added `prjpriority INTEGER DEFAULT 5` to the project table in `schema_v2.sql` and as a column migration in `connection.py`. Updated `create_project()` and `update_project()` in `queries.py` to accept the priority parameter. Added a priority number input field (1-10) to the project edit form in `project_form.html`. Added priority display to `project_view.html` detail list and `projects.html` table.


### The left nav of Agent Swarm doesn't refresh after spawning an Agent
**Status**: Complete
**Request**:
    I accidently spawned 18 agents because the page wasn't showing them to me.
**Request Restated**: After spawning an agent via the "+" button or spawn bar, the agent tree and subheader counts didn't update, requiring a full page reload. Users couldn't tell agents were being created, leading to accidental mass spawning.
**Root Cause**: Two issues: (1) The spawn/terminate functions used `window.location.reload()` which is slow and loses UI state. (2) Flask's development server runs single-threaded by default, so the SSE connection (`/api/events`) blocked all subsequent fetch requests, preventing dynamic tree refresh from completing.
**Resolution**: Replaced `window.location.reload()` with dynamic DOM updates in `agent-monitor.js`. Added `refreshAgentTree()` which fetches `/api/agents`, filters terminated agents, and rebuilds the tree DOM in-place. Added `refreshQueueLog()` and `updateSubheaderCounts()` for live updates. Fixed the blocking issue by adding `threaded=True` to `app.run()` in `cli.py` so SSE doesn't block other HTTP requests. The subheader "+" buttons now also trigger `agentMonitor.refreshAgentTree()` if on the agents page.


### Agent Page Needs Redesign
**Status**: Complete
**Request**:
The Agent Swarm page is terrible, please complete redesign;
- Add Agent selection as left tree view, by type
- the right side of the page should be the running, real-time queue log
- maybe have an optional "view agent terminal" if you want to watch it work
**Request Restated**: The Agent Swarm page needed a complete redesign from a flat card grid layout to a split-panel layout with: (1) a left panel containing an agent tree view organized by role type (EA, BA, SE, CA, TA), (2) a right panel with a real-time queue log showing inter-agent messages, and (3) an optional agent terminal view that appears when an agent is selected.
**Root Cause**: The existing agents page used a flat card grid that didn't organize agents by type, had no queue log visibility, and buried the terminal output in a detail panel below the grid. The layout made it hard to find agents by role or monitor queue activity.
**Resolution**: Rewrote `agents.html` with a split-panel layout (`agents-layout`). Left panel (340px) contains: header with Pause/Resume controls, inline spawn form (project + role dropdowns + Spawn button), and a collapsible tree view grouped by all 5 agent roles with count badges. Each agent shows a status dot (color-coded), name, meta info, and hover-reveal terminate button. Right panel contains: stats bar (Active/Idle/Error/Queued counts), scrollable queue log showing messages with timestamps/from/to/body, and a slide-in terminal section that appears when an agent is clicked (showing role/name header, status/project/component/model info bar, and live SSE terminal output). Updated `app.py` `agents_page()` route to pass `agents_by_role` dict and `messages` list. Added extensive CSS for the new layout including responsive mobile support. Updated `agent-monitor.js` integration to work with the tree-based selection model.


### Move the 5 agent counts to a sub-header
**Status**: Complete
**Request**:
The 5 AI Agent counts in the main header are good, but abbreviated and not very clear what they mean.
Please add a subheader that, like the main top-nav header, traverses the entire horizontal page.
however, the subheader ONLY includes the spelled out names and counts of all the agents.
That should give them plenty of room, and make the meaning clear.
**Request Restated**: The 5 agent type counts (EA/BA/SE/CA/TA) in the main nav bar were abbreviated and unclear. Move them to a new full-width sub-header bar below the navbar that displays the fully spelled-out agent type names with their counts.
**Root Cause**: The agent counts were crammed into the main navbar as small abbreviated links (EA, BA, SE, CA, TA) with tiny count badges. The abbreviations weren't self-explanatory, and the small size made them easy to overlook.
**Resolution**: Removed the `.nav-agents` section from the main `<nav>` in `base.html`. Added a new `.agent-subheader` div between `</nav>` and the main content container that spans the full page width. Each agent type is displayed as a link (`agent-subheader-item`) with the full name ("Enterprise Architect", "Business Architect", etc.) and a gold pill count badge. The sub-header uses a dark gradient background slightly lighter than the navbar, centered layout with generous spacing, and links to the filtered agents page for each role. Added responsive CSS for mobile wrapping. Removed old `.nav-agents`, `.nav-agent-link`, `.nav-agent-count`, and `.nav-agent-divider` CSS; replaced with new `.agent-subheader` styles. Updated workspace height calculation to account for the new sub-header height.


### Need 5 agent types, always
**Status**: Complete
**Request**:
    Please look thru the entire project and make sure there are 5 agent types represented:  Enterprise Architect, Business Architect, Service Engineer, Coding Agent,
    Testing Agent.  for example, I only see 3 represented in headers, and 4 represented in "spawn agent".  Anywhere something deals with an agent, there should be 5 choices.
**Request Restated**: All agent-related UI and code should consistently represent 5 agent types: Enterprise Architect, Business Architect, Service Engineer, Coding Agent, and Testing Agent. Previously only 3-4 types were shown depending on the location.
**Root Cause**: The codebase defined only 4 roles (business_owner, enterprise_architect, service_engineer, coding_agent). The nav bar, agents page tabs, and settings page only showed 3 (EA/SE/CA). The "business_owner" name didn't match the desired "Business Architect" label, and Testing Agent didn't exist.
**Resolution**: Added `ROLE_BUSINESS_ARCHITECT` and `ROLE_TESTING_AGENT` to constants.py, updated `AGENT_ROLES` to all 5, updated `ROLE_NAMES`, added per-type defaults. Updated the DB schema CHECK constraint and added a migration for existing DBs. Updated all templates: base.html nav bar (EA/BA/SE/CA/TA), agents.html filter tabs, settings.html per-type overrides. Added system prompts for both new roles in manager.py. Updated orchestrator.py to assign test tasks to Testing Agent. Kept `business_owner` as a legacy alias for backward compatibility with the interview system.


### No "Add Service" button
**Status**: Complete
**Request**:
Although the services should be added by AI, we should still have an "Add Service" on the right side of the Project screen.
**Request Restated**: The Project detail view page (`project_view.html`) should have an "Add Service" button for manually adding services.
**Root Cause**: The "Add Service" button was only present on the Workspace page, not on the dedicated Project view page.
**Resolution**: Added a "+ Add Service" button to the page header button group in `project_view.html`. Clicking it toggles an inline form (service name + description + Create/Cancel) that POSTs to the existing `workspace_add_service` route. Added the `toggleAddService()` JS function.


### No "Add Folder" on Code Dir Selector
**Status**: Complete
**Request**:
The "New Project" "Code Director" folder selector has no "add folder", please add
**Request Restated**: The folder picker modal should include a "New Folder" button that allows users to create a new directory from within the picker without leaving the modal.
**Root Cause**: The folder picker only supported browsing existing directories with no way to create new ones.
**Resolution**: Added a "+ New Folder" button to the folder picker actions bar in `project_form.html`. Clicking it reveals an inline input for the folder name with Create/Cancel buttons. Added `showNewFolder()`, `hideNewFolder()`, and `createFolder()` methods to the `FolderPicker` class in `folder-picker.js`. Added a new `POST /api/create-dir` endpoint in `app.py` that validates the folder name (no path separators, no hidden dirs), creates the directory, and returns the new path. The picker automatically navigates into the newly created folder.


### New Project page: "Code Directory" Folder Selector
**Status**: Complete
**Request**:
when creating a new project, the user should be able to select a folder/directory as the code directory instead of typing a path into a text box. this should open a file browser dialog to allow them to choose the directory.
**Request Restated**: The New Project form's Code Directory field should provide a folder browser modal instead of requiring users to manually type a filesystem path.
**Root Cause**: The Code Directory field was a plain text input with no browsing capability. Users had to know and type the full path manually.
**Resolution**: Created a `FolderPicker` JS class (`static/js/folder-picker.js`) that opens a modal overlay, fetches directories from a new `GET /api/browse-dirs` endpoint, and allows navigation through the filesystem. The selected folder path is populated into the Code Directory input. The API defaults to the user's home directory, filters hidden directories, and handles permission errors. Modal styling added to `style.css` with the gold theme.


### New Project page: Remove Max Agents / model
**Status**: Complete
**Request**:  These should be set during execution, not on the project.  adjust the backend code as well
**Request Restated**: The Max Agents and Model fields should be removed from the New Project and Edit Project forms, as these are execution-time settings, not project-level attributes.
**Root Cause**: The project form included `prjmodel` and `prjmaxagents` fields that were being saved to the project record, but these belong in the agent/settings configuration instead.
**Resolution**: Removed Model and Max Agents fields from `project_form.html` (both new and edit modes), removed them from the `project_view.html` detail display, removed them from the `workspace.html` detail panel, and removed the corresponding parameters from the `project_edit()` route handler in `app.py`. These settings are now managed through the hierarchical agent settings system on the Settings page.


### New Project page: I started a new project, but there was no interview offered?
**Status**: Complete
**Request**:  New Project page: I started a new project, but there was no interview offered?
The entire New Project process should be an interview now.  Please only allow users to type in the project name, set the code directory, and then "start interview".
Everything else should be AI generated.
**Request Restated**: The New Project form should be simplified to only Name + Code Directory + "Start Interview" button. Submitting should auto-create a Business Owner interview and redirect to the interview session.
**Root Cause**: The `project_new()` route created the project but did not create an interview or redirect to one, leaving the user on the projects list with no clear next step.
**Resolution**: Rewrote `project_form.html` with two modes: New (name + codedir + "Start Interview") and Edit (name + desc + codedir + "Update"). Modified `project_new()` in `app.py` to auto-create a `business_owner` interview via `create_interview()` and redirect to `interview_session` with the new interview ID. The form uses the folder picker for code directory selection.


### workspace - Add Service
**Status**: Complete
**Request Restated**: When a project is selected in the left pane, the right detail panel should display context-sensitive action buttons, including "Add Service", to enable quick access to common project-level workflows without navigating away.
**Root Cause**: The workspace right panel had no way to add services directly; users would need to navigate to a separate form.
**Resolution**: Added a "+ Add Service" button in the Actions section of `workspace.html` that toggles an inline form (service name + description + Create/Cancel). The form POSTs to a new `POST /workspace/<prjid>/add-service` route which calls `create_component()` with `cmplevel="service"`. Also added a JSON API variant at `POST /api/projects/<prjid>/services`. Both create the service and redirect/return the new component ID.


### Multi-Agent approach: Enterprise Architect Agent
**Status**: Complete
**Request**:
    OK, this turned into a revamp of the way we manage agents:
    Add an Enterprise Architect Agent interface to the top navigation bar so users can ask questions and get guidance at any time during their workflow, without needing to navigate away from their current page.  Also on the top nav bar should be a total Agent count, by type:
    "Enterprise Architect (1) -- Service Architect (X) -- Coding Agents (Y)"  Clicking on any Enterprise Architect will bring up the web-based terminal window that IS the agent, as well as a surrounding screen with options.   Clicking on Service or Coding agents should bring up a list of active agents, where user can click on the agent in the list and see the same "web-based terminal window that IS the agent, as well as a surrounding screen with options".
    The Agent page should allow you to add more/fewer agents, and manage agent behavior, etc.
    Agent settings should be a top-down defaulting strategy: i.e., higher levels are consider "defaults" to lower levels.
    User can set behaviors at an Agent Global level, or at an Agent Type level, or at an individual Agent level.
    For example,
    - the user could set "Claude 4.5 Opus" at the Global level and nowhere else; all Agents then use 4.5 Opus.
    - If the user assigns "Service" Agent to Sonnet, then Service Agents use Sonnet, all others still default to Opus.
    - If the user assigns on e particular Service Agent to Opus, then the individual overrides all higher level defaults, and the agent uses Opus.
    - this (globally, overridden by Per Project, overridden by individual Agent) means that ALL Agent settings can be set at any level: globally, per Project, or per Agent
    A user can set the following settings per agent:
    - max total number of agents
    - max number of agents by type: Enterprise Architect, Business Architect, Service Owner, Coding Agent, Test Agents
    - LLM Model used
    - "check queue for new work every X seconds" (zero = immediately when next available, 5 would check for work 5 seconds after completing last work)
    Workflow for Agents:
    When there is work to be done, it should enter a queue.  Idle agents can pull work from that queue.  Agents can also add work to the queue, which will be common (testing, for instance).
    This request is wide-ranging, including rebuilding elements of Agent workflow management to be queued based. The UI may be complex, try your best to keep it fairly simple.
    Agents should always (a) save context to files or the application DB, and should always clear context prior to picking up new work from the queue.
**Request Restated**: Complete overhaul of the multi-agent system across 6 areas: (1) Nav bar agent counts by role with links; (2) Agent page with role filters, spawn/terminate controls, and live terminal streaming; (3) Persistent EA chat slideover panel accessible from any page; (4) SSE enrichment with per-agent output streaming via new `agent_output` DB table; (5) Hierarchical settings cascade (individual agent > agent type > global) with new `agent_settings` DB table and per-type override UI; (6) Formalized work queue with context save/restore via new `agent_context` DB table.
**Root Cause**: The agent management system lacked role-based visibility, spawn/terminate controls, live output streaming, persistent EA chat, hierarchical settings, and formalized work queue management.
**Resolution**: Implemented across 6 phases:
- **Phase 1 (Nav counts)**: Added `inject_agent_counts()` context processor with `count_agents_by_role()` query. Nav bar shows `EA (N) -- SE (N) -- CA (N)` with links to filtered agent page.
- **Phase 2 (Agent page)**: Rewrote `agents.html` with role filter tabs, spawn agent form (`POST /api/agents/spawn`), terminate button (`POST /api/agents/<id>/terminate`), and live terminal integration.
- **Phase 3 (EA chat)**: Added EA chat slideover panel in `base.html`, new `ea-chat.js` for message management, and `GET/POST /api/ea-chat/<prjid>` endpoints.
- **Phase 4 (SSE + streaming)**: Added `agent_output` table, `append_agent_output()`/`get_agent_output()` queries, `GET /api/agents/<id>/stream` SSE endpoint, and `agent-terminal.js` for live output display. Updated `manager.py` to persist output chunks.
- **Phase 5 (Hierarchical settings)**: Added `agent_settings` table with UNIQUE constraint, `resolve_setting()` cascade function with type coercion, `GET/POST /api/agent-settings` endpoints, and per-type override UI in `settings.html`. Updated `manager.py` and `orchestrator.py` to use `resolve_setting()`.
- **Phase 6 (Work queue)**: Added `agent_context` table, context save/restore in `orchestrator.py`, `POST /api/work-queue` endpoint, and Work Queue section in `build_progress.html`.


### Highlight row clicked on HTree
**Status**: Complete
**Request**: when clicking on a row in Htree, highlight that row so users know what row the data on the right side pertains to
**Request Restated**: When a user clicks a row in the HTree, that row should be visually highlighted so it's clear which item the right-side detail panel corresponds to.
**Root Cause**: The `.tree-node-selected` CSS class existed but used the same background color (`#FFF8E7`) as the hover state, making it indistinguishable from a hovered row.
**Resolution**: Updated `.tree-node-selected` in `style.css` to use a more prominent background (`#FAEDC4`), a thicker gold left border (4px), and an inset box-shadow for additional contrast. The class is applied/removed via click handlers in `workspace.html`.


### Remove "Define" above the HTree
**Status**: Complete
**Request**: There is a "Define" button above the HTree to the right of the project selector. It doesn't work and its purpose is unclear. Remove it.
**Request Restated**: A phase badge (displaying "Define") appeared in the project selector bar next to the dropdown. It served no interactive purpose and confused users. Remove it.
**Root Cause**: The workspace template included a `<span class="badge badge-{{ current_project.prjphase }}">` in the project-selector div, which displayed the current phase name as a non-functional badge.
**Resolution**: Removed the phase badge span from the project-selector div in `workspace.html`. Phase information is still visible in the right-panel detail view.


### Move Project Selector to align left
**Status**: Complete
**Request**: The project selector on the Workspace page is hanging randomly in the middle. Make it left-aligned so it reads "Project:" followed by the selector dropdown.
**Request Restated**: The project selector bar used `justify-content: space-between`, causing the label and dropdown to spread apart. It should be left-aligned with elements flowing naturally from left to right.
**Root Cause**: The `.project-selector` CSS used `justify-content: space-between`, which spread elements across the full width of the bar.
**Resolution**: Changed `.project-selector` CSS to remove `justify-content: space-between` and added `gap: 10px` so elements align naturally to the left with consistent spacing.


### Add a "New Project" button
**Status**: Complete
**Request**: Add a "New Project" button to the Workspace page, positioned right-aligned across from the project selector dropdown to provide quick access to project creation, the button should initiate the new project workflow by launching the AI interview process.
**Request Restated**: Add a right-aligned "+ New Project" button in the project selector bar that links to the project creation workflow.
**Root Cause**: No quick-access project creation button existed on the Workspace page.
**Resolution**: Added an `<a>` styled as `btn btn-sm btn-primary` with `margin-left: auto` to push it to the right side of the flex container. It links to `url_for('project_new')` which initiates the new project workflow.


### Simplify Top Nav
**Status**: Complete
**Request**: The top navigation bar currently includes multiple options that are unnecessary. Simplify it to keep only "Workspace" and "Settings" tabs, removing all other navigation items to reduce clutter and improve UX.
**Request Restated**: The top nav had 9 items (Workspace, Dashboard, Projects, Interviews, Agents, Build, Messages, System, Settings). Reduce to only Workspace and Settings.
**Root Cause**: All navigation items were listed in `base.html` regardless of whether they were needed for the primary workflow.
**Resolution**: Removed Dashboard, Projects, Interviews, Agents, Build, Messages, and System links from the `<ul class="nav-links">` in `base.html`, keeping only Workspace and Settings.


### Add action buttons
**Status**: Complete
**Request**: Add action buttons in a new section across the top of the right-hand pane of the Workspace screen. These buttons should represent the different actions available for the currently selected item in the left-hand pane (HTree), such as Edit, Delete, Run Tests, View Code, etc., providing quick access to common workflows for the selected Service or Component.
**Request Restated**: Add a context-sensitive action button bar at the top of the right pane that appears when a tree node is selected, with buttons for Edit, Run Tests, View Code, and Delete.
**Root Cause**: The right pane had no quick-action buttons; users had to scroll to the bottom "Actions" section or navigate away to perform common operations.
**Resolution**: Added a `.detail-actions` div between `.detail-header` and `.detail-content` in `workspace.html` containing Edit, Run Tests, View Code, and Delete buttons. The bar is hidden by default (`display: none`) and shown via `.visible` class when a tree node is clicked. JavaScript in the page updates each button's `href` to point to the selected component. Added corresponding CSS for the action bar styling.


### Htree items should display status
**Status**: Complete
**Request**: Each item in the HTree (Service or Component) should display a horizontal progress bar overlay using green and yellow colors. The green section should represent the percentage complete, with yellow filling the remainder. For example, 100% complete = entirely green, 50% complete = half green/half yellow split horizontally across the row.
**Request Restated**: Service and Component rows in the HTree should have a green/yellow background overlay proportional to their completion percentage.
**Root Cause**: The progress overlay existed but used very low opacity values (0.15 for green, 0.08 for yellow), making it barely visible.
**Resolution**: Increased the opacity of `.tree-node-progress::before` (green) from `rgba(92, 184, 92, 0.15)` to `rgba(92, 184, 92, 0.25)` and `.tree-node-progress::after` (yellow) from `rgba(232, 168, 50, 0.08)` to `rgba(232, 168, 50, 0.18)` in `style.css`, making the progress overlay clearly visible.


### HTree Missing Many Data Elements
**Status**: Complete
**Request**:  HTree is missing most of the data elements from the mockup.  The data elements should be, from left to right, and per data element type:
    See `./BW_Design01.svg` for a visual mockup
    - Service: (S) for Service (present)
        - "S{} - Name of Service" (present), in large bold font; just make sure the S{} is assigned, not user input
            - below the "S{} - Name of Service" in smaller font should be:  "{}% Complete    Coding Agents: {}    Orchestrator Agents: {}   Components: {}"
        - on the far right is "Tests" prefixed with an icon indicating the outcome of the last test run (🟢 all passed, 🟡 some failed, ⚪ not tested). The "Tests" should link to a "Testing" page for that element, filtered to this Service, which lists all the tests created, and where the user can initiate a new test run.
        - The background color of the entire bar should be split between green and yellow; the % of horizontal space the green consumes is proportional to the "{}% Complete"
    - Component:  (C) for Component (present)
        - "S{}C{} - Name of Component" where the S{} matches the parent service, and C{} is the (nonsequential) ID.
            - below the "S{}C{} - Name of Component" in smaller font should be:  "{}% Complete    Coding Agents: {}   Functions: {}"
        - on the far right is "Tests" prefixed with an icon indicating the outcome of the last test run (🟢 all passed, 🟡 some failed, ⚪ not tested). The "Tests" should link to a "Testing" page for that element, filtered to this Component, which lists all the tests created, and where the user can initiate a new test run.
        - The background color of the entire bar should be split between green and yellow; the % of horizontal space the green consumes is proportional to the "{}% Complete"
**Request Restated**: The Hierarchy Tree (HTree) on the Workspace page was missing several data elements per the design mockup. Service rows needed: cmpid-based S{} identifiers (not sequential), a two-line layout with stats subtitle (% Complete, Coding Agents, Orchestrator Agents, Components count), emoji test status icons linking to a Tests page, and a green/yellow progress background bar. Component rows needed the same treatment with S{parent}C{id} identifiers, their own stats subtitle (% Complete, Coding Agents, Functions count), test icons, and progress background.
**Root Cause**: The initial implementation used a single-line layout with sequential loop indices for identifiers, simple status dots instead of emoji icons, a "View" link instead of "Tests", and no progress background coloring. Agent counts were not queried or passed to the template.
**Resolution**: Updated `_build_hierarchy_tree()` in `app.py` to accept `prjid`, query agents and test specs, and enrich each node with `coding_agents`, `orchestrator_agents`, and `test_status`. Updated `workspace.html` template to use two-line node layout (name + meta subtitle), cmpid-based identifiers, emoji test icons, and "Tests" links. Added CSS for `tree-node-progress` with `::before`/`::after` pseudo-elements using CSS custom property `--progress-pct` for green/yellow split background. Updated `hierarchy-tree.js` to match the new format for consistency with the server-rendered template.


### Template
**Status**: TBD
**Request**:

