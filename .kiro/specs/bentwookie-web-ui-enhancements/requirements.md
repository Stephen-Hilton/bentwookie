# Requirements Document

## Introduction

This document specifies requirements for enhancing the BentWookie web UI with improved usability features including sortable tables, markdown rendering, loop controls reconciliation, and request document tracking capabilities. These enhancements aim to improve the user experience when managing projects, requests, and viewing generated documentation through the web interface.

## Glossary

- **Web_UI**: The Flask-based web interface for BentWookie accessible via `bw web` command
- **Table_Sorter**: JavaScript component that enables click-to-sort functionality on table headers
- **Markdown_Renderer**: Component that converts markdown text to formatted HTML for display
- **Loop_Controls**: Configuration settings that control daemon behavior (poll interval, max iterations, max turns, etc.)
- **Request_Doc**: A document generated during request processing phases (plan, dev, test, document, etc.)
- **Requests_Docs_Table**: Database table storing metadata about documents generated for each request
- **Phase_Prompt**: LLM prompt template used during a specific processing phase
- **Doc_Tracker**: System component responsible for capturing and storing document metadata from LLM responses

## Requirements

### Requirement 1: Sortable Tables

**User Story:** As a user, I want to click on table column headers to sort data, so that I can quickly find and organize information in list views.

#### Acceptance Criteria

1. WHEN a user clicks a sortable column header THEN THE Table_Sorter SHALL sort the table rows by that column in ascending order
2. WHEN a user clicks the same column header again THEN THE Table_Sorter SHALL toggle the sort order to descending
3. WHEN a user clicks a different column header THEN THE Table_Sorter SHALL sort by the new column in ascending order and reset the previous column's sort state
4. THE Table_Sorter SHALL display a visual indicator (arrow icon) showing the current sort column and direction
5. THE Table_Sorter SHALL be applied to all list view tables including projects, requests, infrastructure, and status tables
6. THE Table_Sorter SHALL handle numeric, text, and date column types appropriately during sorting
7. WHEN the page loads THEN THE Table_Sorter SHALL maintain the default server-side sort order until user interaction

### Requirement 2: Markdown Rendering for Project Prompt

**User Story:** As a user, I want to see the Project Prompt displayed as rendered markdown, so that I can read formatted documentation with proper headings, lists, and code blocks.

#### Acceptance Criteria

1. WHEN the project view page displays a Project Prompt THEN THE Markdown_Renderer SHALL convert the markdown text to formatted HTML
2. THE Markdown_Renderer SHALL support standard markdown elements including headings, bold, italic, lists, code blocks, and links
3. THE Markdown_Renderer SHALL sanitize the rendered HTML to prevent XSS attacks
4. WHEN the Project Prompt is empty or null THEN THE Web_UI SHALL display a placeholder dash character
5. THE Markdown_Renderer SHALL apply consistent styling that matches the existing Web_UI design

### Requirement 3: Loop Controls Reconciliation

**User Story:** As a user, I want all configurable loop options available in the web UI, so that I can manage daemon settings without using the CLI.

#### Acceptance Criteria

1. THE Web_UI System page SHALL display all loop control settings that are available via CLI including: poll_interval, max_iterations, max_turns, doc_retention_days, commit_enabled, commit_branch_mode, and commit_branch_name
2. WHEN a user updates a loop control setting via the Web_UI THEN THE Web_UI SHALL persist the change to the settings file
3. THE Web_UI SHALL display the current value for each loop control setting
4. WHEN a setting has a valid range constraint THEN THE Web_UI SHALL enforce input validation (e.g., poll_interval minimum 1 second)
5. THE Web_UI SHALL group related settings logically (loop controls, commit settings, retention settings)

### Requirement 4: Request Documents Database Table

**User Story:** As a developer, I want request-generated documents tracked in the database, so that the system can display and link to all documents created during request processing.

#### Acceptance Criteria

1. THE Database SHALL contain a Requests_Docs_Table with columns: doc_id (primary key), reqid (foreign key to request), doc_name, doc_path, doc_phase, and created_at timestamp
2. THE Requests_Docs_Table SHALL enforce a foreign key relationship to the request table with cascade delete
3. WHEN a request is deleted THEN THE Database SHALL automatically delete all associated document records
4. THE Database SHALL create an index on reqid for efficient document lookups by request
5. THE Database SHALL allow multiple documents per request (1:M relationship)
6. THE doc_name column SHALL accept arbitrary document names including phase names (plan, dev, test, document) and user-requested custom names

### Requirement 5: Phase Prompt Document Tracking

**User Story:** As a developer, I want LLM prompts to instruct the model to report created documents, so that the framework can capture and store document metadata.

#### Acceptance Criteria

1. WHEN a phase creates a document THEN THE Phase_Prompt SHALL instruct the LLM to output document metadata in a parseable format
2. THE Phase_Prompt output format SHALL include doc_name and doc_path fields
3. THE Doc_Tracker SHALL parse the LLM response to extract document metadata
4. WHEN document metadata is extracted THEN THE Doc_Tracker SHALL insert a record into the Requests_Docs_Table
5. IF the LLM creates additional user-requested documents THEN THE Phase_Prompt SHALL allow reporting of arbitrary document names
6. THE Doc_Tracker SHALL handle cases where no documents are created without error

### Requirement 6: Documents Section in Request View

**User Story:** As a user, I want to see all documents generated by a request in the request view page, so that I can access and review the generated documentation.

#### Acceptance Criteria

1. THE Request View page SHALL display a "Documents" section listing all documents associated with the request
2. WHEN documents exist for a request THEN THE Web_UI SHALL display them in a sortable table with columns: Doc Name, Phase, File Path, and Created At
3. THE doc_name column SHALL render as a hyperlink that opens the document content
4. WHEN a user clicks a document link THEN THE Web_UI SHALL display the file content rendered as markdown
5. THE File Path column SHALL display the full filesystem path for direct file access
6. WHEN no documents exist for a request THEN THE Web_UI SHALL display an appropriate empty state message
7. THE Table_Sorter SHALL be applied to the documents table for sorting by any column

### Requirement 7: Web Server Status CLI Command

**User Story:** As a user, I want a CLI command to check web server status, so that I can verify if the web UI is running and on which port without opening a browser.

#### Acceptance Criteria

1. THE CLI SHALL provide a `bw web status` command
2. WHEN the web server is running THEN THE CLI SHALL display the server status as "Running", the host address, and the port number
3. WHEN the web server is not running THEN THE CLI SHALL display the server status as "Not Running"
4. THE CLI SHALL display the configured default host and port settings
5. IF the web server process can be detected THEN THE CLI SHALL display the process ID (PID)
