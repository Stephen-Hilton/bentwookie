# BentWookie — Requirements Specification

BentWookie (BW) is a framework for orchestrating AI agent swarms to build complex software projects. It enforces deterministic architectural decisions at each level of a project hierarchy, then delegates atomic coding tasks to parallel agents with minimal context requirements. BW manages all agents as Claude Code instances running in BW-controlled terminal shells.

## Core Principles

1. **Separation of concerns**: Business logic is designed independently from infrastructure and transport.
2. **Minimal agent context**: Higher-level agents make architectural decisions; coding agents receive only the narrow context they need for atomic tasks.
3. **Define top-down, design top-down, validate bottom-up, build middle-out**: The user defines the hierarchy from Project → Function. AI designs the build plan top-down. AI validates and tests bottom-up. Construction starts at Module/Function and aggregates upward through Subsystem to Service.
4. **Dependency-driven parallelism**: Work is parallelized up to a user-defined limit, constrained by the dependency graph.

---

## Project Hierarchy

BW decomposes every project into up to five levels. Each level follows the same pattern during planning:
- **Inputs**: The parent level's outputs, plus user corrections to AI assumptions.
- **Outputs**: A decomposition into child components, a connection map between them, and build-vs-buy (OSS) recommendations.

The Enterprise Architect may collapse the middle levels (Subsystem, Module) at their discretion. If a service is simple enough, it can go straight from Service → Functions, with the Service Engineer handling integration directly.

| Level | Description | Example | Planning Agent |
|-------|-------------|---------|----------------|
| **Project** | Top-level scope; one or more git repos. Defines business goals, deployment targets, and technical requirements. | "E-commerce platform" | Enterprise Architect, Business Architect |
| **Service** | Self-contained deployable unit (container, cloud resource). | Database, API, UI Frontend, Event Bus | Subject Matter Expert / Technical Architect |
| **Subsystem** | High-level code organizational unit within a service. | Auth, Session Mgmt, Query Parsing | Senior Engineering Architect |
| **Module** | Mid-level unit: a package, class, or file of related functions. Modules can depend on peer modules within their subsystem. | `validate_syntax`, `optimize_rewrite` | Senior Software Engineer |
| **Function** | Atomic unit of work: single function with defined inputs/outputs. Lowest level — no further decomposition. | `get_userid()`, `diff_tablelist(a, b)` | Senior Software Engineer |

### Project-Level Outputs

- Recommended set of Services with specific technology choices.
- Service connection map (how services interact).
- Traceability map: which services satisfy which business goals/use-cases.

### Cascading Pattern (Service → Subsystem → Module → Function)

At each subsequent level, the AI agent:
1. Receives the parent's outputs (decomposition + connection map).
2. Proposes child-level decomposition with connection map and OSS recommendations.
3. Presents to user for sign-off or correction.
4. Produces the finalized plan for the next level down.

---

## Workflow Phases

### Phase 1: Define — Top-Down (Human + AI)

#### Step 1A: Project Discovery Interviews

Project-level input is collected through two sequential agent interviews — real two-sided conversations, not form-filling. Voice input is supported (speech-to-text) so the user can speak naturally.

**Interview 1 — Business Owner Agent**

The Business Owner conducts a conversational interview to extract all business-relevant project details. The agent should:
- Start with a few hard-coded seed questions (e.g., project name, high-level purpose).
- Dynamically follow up based on answers — dig deeper where the user is vague, move on where they're clear.
- Ask hard questions: challenge assumptions, surface hidden requirements, identify risks.
- Make proactive recommendations: suggest business models, user engagement strategies, monetization approaches, competitive positioning — like a real advisor would.
- Offer suggestions when asked. If the user says "I don't know, what do you think?" the agent should propose concrete options with tradeoffs.
- Cover at minimum: purpose, target audience, engagement model, use-cases, success criteria, constraints, budget/timeline awareness.

The full transcript is saved.

**Interview 2 — Enterprise Architect Agent**

The Enterprise Architect reads the Business Owner transcript, then conducts a second interview focused on technical decisions:
- References and builds on what the user already told the Business Owner — does not re-ask answered questions.
- Asks hard technical questions: deployment model, scalability needs, security posture, compliance requirements, data residency, disaster recovery.
- Makes proactive recommendations: suggests architecture patterns, technology stacks, cloud vs. on-prem tradeoffs, build vs. buy decisions — like a real architect would.
- Challenges the user's technical assumptions when warranted.
- Cover at minimum: deployment target (cloud-native vs. agnostic, containers, local vs. SaaS), language/framework preferences, RPO/RTO, availability vs. latency tradeoffs, security requirements.

The full transcript is saved.

**Output of Step 1A**: Both transcripts, plus a structured summary of all project-level decisions. The Business Owner and Enterprise Architect now have enough information to produce their Project-level outputs (service decomposition, connection map, traceability map).

#### Step 1B: Hierarchy Decomposition

Starting from the Project-level outputs, walk the user through each level of the hierarchy interactively:
- AI proposes decomposition at each level (Services, Subsystems, Modules, Functions).
- User reviews, corrects, and approves before moving to the next level down.
- This is a collaborative session — the human steers, the AI generates.

**Output of Phase 1**: Complete hierarchy from Project → Functions, with technology choices and component definitions locked at every level.

### Phase 2: Design — Top-Down (AI-Driven)

With the hierarchy defined, the AI produces the full build plan top-down:
- Build plans for each level (what gets built, in what order).
- Dependency graph across all components.
- Integration maps: how components connect within and across levels.
- Connection point specifications: interfaces, contracts, and data flows between components.
- OSS vs. build-from-scratch decisions finalized.

**Output**: Complete build plan with dependency DAG, integration maps, and connection point specs.

### Phase 3: Validate — Bottom-Up (AI-Driven)

Starting at the Function level, the AI validates the design upward and generates **test specifications** (not runnable test code):
1. **Function specs**: Expected behaviors, inputs/outputs, edge cases for each function.
2. **Module specs**: Integration expectations for each module's functions working together.
3. **Subsystem specs**: Integration expectations across modules within a subsystem.
4. **Service specs**: End-to-end behavioral expectations for each service.
5. **Project specs**: Cross-service acceptance criteria tied to business use-cases.

Coding agents write the actual runnable test code during Phase 4, alongside implementation.

The AI also validates the design from this bottom-up perspective:
- Identifies dependency conflicts or missing connections in the top-down plan.
- Adjusts the dependency graph and integration maps as needed.
- Confirms that all connection points are testable and well-defined.

**Output**: Complete test specifications at every level. Validated and finalized dependency graph ready for parallel execution.

### Phase 4: Build — Middle-Out (AI Swarm)

Construction starts at the **Module and Function level** and aggregates upward:

1. **Coding Agents** receive a module's test specifications (from Phase 3), implement all functions, write runnable test code, and run module-level tests.
2. Completed modules are handed to the **Service Engineer**, who assembles them into **Subsystems** and runs subsystem-level tests. The Service Engineer may delegate subsystem assembly back to coding agents when appropriate.
3. Service Engineers then integrate completed subsystems into the **Service**, run service-level tests, and coordinate with the Architect and Business Owner to validate requirements.

| Agent Role | Count | Responsibility |
|------------|-------|----------------|
| **Business Owner** | 1 | Answers business-goal questions from other agents. Guides project direction toward business objectives. Persistent — always available. |
| **Enterprise Architect** | 1 | Top-down architectural guidance. Ensures the project remains structurally sound as pieces are assembled. May collapse hierarchy levels for simple services. Persistent — always available. |
| **Service Engineer** | N (one per service) | Sets up OSS infrastructure. Assembles modules into subsystems, subsystems into services. May delegate subsystem assembly to coding agents. Runs integration tests at each aggregation step. Coordinates with Architect and Business Owner. |
| **Coding Agent** | X (user-configured max) | Receives a single module + test specs. Implements all functions, writes runnable tests, runs module-level tests. May also be assigned subsystem assembly by Service Engineer. Requires minimal context — no architectural decisions. |

**Concurrency rules**:
- X is a ceiling. Actual active coding agents = min(X, available independent work items in the dependency graph).
- Coding agents work on modules whose dependencies are already satisfied.
- Service Engineers integrate completed work and may unblock additional modules for coding agents.

### Rework Protocol

When a coding agent discovers the plan is wrong during implementation:
1. **Coding agent flags the issue** to its Service Engineer with a description of the conflict.
2. **Service Engineer triages**: if the issue is local to the module (e.g., a function signature needs adjustment), the Service Engineer authorizes the fix in place.
3. **If the issue is structural** (affects other modules, subsystems, or the dependency graph), the Service Engineer escalates to the **Enterprise Architect**.
4. The **Architect issues a design amendment** that updates the affected portion of the hierarchy. Impacted agents receive the amendment and adjust accordingly.

---

## Inter-Agent Communication

Agent communication is a core BW capability. All agents run as Claude Code instances in BW-managed terminal shells, giving BW full control over all agent activity.

### Message Types

| Type | Behavior | Use Case |
|------|----------|----------|
| **Normal** | Queued in the recipient's work queue. Delivered when the recipient finishes its current task. | Status updates, completed module handoffs, non-blocking questions. |
| **Urgent** | Interrupts the recipient's current execution immediately. | Architect detects a coding agent is actively building something incorrect and needs to stop. Design amendments that invalidate in-progress work. |

Urgent messages should be used sparingly — only when continuing current work would be wasteful or harmful.

### Communication Patterns

- **Coding Agent → Service Engineer**: Module completion handoffs (normal). Flagging design conflicts (normal).
- **Service Engineer → Coding Agent**: Subsystem assembly delegation (normal). Work cancellation (urgent).
- **Service Engineer → Enterprise Architect**: Structural issue escalation (normal).
- **Enterprise Architect → Any Agent**: Design amendments (urgent if the agent is actively building against stale plans, normal otherwise).
- **Any Agent → Business Owner**: Business-goal clarification questions (normal).

---

## Key Constraints

- **No concurrent writes to shared state without coordination**: Service Engineers own integration; coding agents own only their assigned module.
- **All architectural decisions are locked before Phase 4**: Coding agents do not make design choices. Design amendments during Phase 4 flow through the Architect via the rework protocol.
- **Test specs exist before code is written**: Phase 3 produces test specifications; coding agents write runnable test code alongside implementation in Phase 4.
- **User approval gates**: Each hierarchy level in Phase 1 requires user sign-off before proceeding.
- **BW owns all shells**: Every agent runs in a BW-managed terminal. BW can observe, message, or terminate any agent at any time.
