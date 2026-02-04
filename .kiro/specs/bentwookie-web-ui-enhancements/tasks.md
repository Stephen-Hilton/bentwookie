# Implementation Plan: BentWookie Web UI Enhancements

## Overview

This implementation plan breaks down the web UI enhancements into discrete coding tasks. The approach prioritizes database schema changes first, then backend logic, followed by frontend components, and finally CLI additions. Testing tasks are included as sub-tasks close to their related implementation.

## Tasks

- [x] 1. Database Schema and Migrations
  - [x] 1.1 Add request_doc table to schema.sql
    - Create table with columns: docid, reqid, doc_name, doc_path, doc_phase, created_at
    - Add foreign key constraint with ON DELETE CASCADE
    - Create index on reqid column
    - _Requirements: 4.1, 4.2, 4.4_
  
  - [x] 1.2 Add migration for existing databases in connection.py
    - Add request_doc table creation to _run_migrations()
    - Handle case where table already exists
    - _Requirements: 4.1_
  
  - [x] 1.3 Write property test for cascade delete
    - **Property 6: Request Document Cascade Delete**
    - **Validates: Requirements 4.2, 4.3**

- [x] 2. Request Documents Database Operations
  - [x] 2.1 Implement CRUD functions in queries.py
    - create_request_doc(reqid, doc_name, doc_path, doc_phase) -> int
    - get_request_docs(reqid) -> list[dict]
    - get_request_doc(doc_id) -> dict | None
    - delete_request_docs(reqid) -> int
    - _Requirements: 4.1, 4.5, 4.6_
  
  - [x] 2.2 Write property test for multiple docs per request
    - **Property 7: Multiple Documents Per Request**
    - **Validates: Requirements 4.5**
  
  - [x] 2.3 Write property test for arbitrary document names
    - **Property 8: Arbitrary Document Names**
    - **Validates: Requirements 4.6, 5.5**

- [x] 3. Checkpoint - Database Layer Complete
  - Ensure all database tests pass, ask the user if questions arise.

- [x] 4. Document Tracker Component
  - [x] 4.1 Create doc_tracker.py in src/bentwookie/loop/
    - Implement DocTracker class with DOC_PATTERN regex
    - Implement parse_response(response) -> list[dict]
    - Implement save_docs(reqid, docs, phase) -> int
    - _Requirements: 5.2, 5.3, 5.4_
  
  - [x] 4.2 Write property test for document tracker parsing
    - **Property 9: Document Tracker Parsing**
    - **Validates: Requirements 5.2, 5.3**
  
  - [x] 4.3 Update phase prompt templates to include doc output format
    - Update data/prompts/phases/plan.md with [DOC:] output instruction
    - Update data/prompts/phases/dev.md with [DOC:] output instruction
    - Update data/prompts/phases/test.md with [DOC:] output instruction
    - Update data/prompts/phases/document.md with [DOC:] output instruction
    - _Requirements: 5.1, 5.2_
  
  - [x] 4.4 Integrate DocTracker into processor.py
    - Call DocTracker.parse_response() after each phase completion
    - Save extracted documents to database
    - Handle empty/no-doc responses gracefully
    - _Requirements: 5.4, 5.6_

- [x] 5. Markdown Renderer Component
  - [x] 5.1 Add markdown and bleach dependencies
    - Update requirements.txt with markdown and bleach packages
    - _Requirements: 2.1, 2.3_
  
  - [x] 5.2 Create markdown rendering utility
    - Create render_markdown() function in web/app.py or new utils module
    - Configure markdown extensions (fenced_code, tables)
    - Implement bleach sanitization for XSS prevention
    - Register Jinja2 filter |markdown
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [x] 5.3 Write property test for markdown element support
    - **Property 2: Markdown Rendering Element Support**
    - **Validates: Requirements 2.1, 2.2**
  
  - [x] 5.4 Write property test for XSS sanitization
    - **Property 3: Markdown XSS Sanitization**
    - **Validates: Requirements 2.3**

- [x] 6. Checkpoint - Backend Components Complete
  - Ensure all backend tests pass, ask the user if questions arise.

- [x] 7. Extended Loop Settings
  - [x] 7.1 Add max_turns getter/setter to settings.py
    - Implement get_max_turns() and set_max_turns()
    - Add web_host and web_port settings
    - Update get_all_loop_settings() to include all settings
    - _Requirements: 3.1_
  
  - [x] 7.2 Update status.html template with all loop controls
    - Add max_turns input field
    - Add commit_enabled checkbox
    - Add commit_branch_mode select
    - Add commit_branch_name input (conditional)
    - Group settings logically
    - _Requirements: 3.1, 3.5_
  
  - [x] 7.3 Update api_loop_settings route to handle new fields
    - Accept and persist max_turns, commit settings
    - Return all settings in response
    - _Requirements: 3.2_
  
  - [x] 7.4 Write property test for settings round-trip
    - **Property 4: Settings Round-Trip Persistence**
    - **Validates: Requirements 3.2, 3.3**
  
  - [x] 7.5 Write property test for settings validation
    - **Property 5: Settings Input Validation**
    - **Validates: Requirements 3.4**

- [x] 8. Table Sorter JavaScript Component
  - [x] 8.1 Create table-sorter.js in web/static/js/
    - Implement TableSorter class
    - Add click handlers for sortable columns
    - Implement compareValues() for text, number, date types
    - Add sort indicator CSS classes
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_
  
  - [x] 8.2 Add table-sorter.css styles
    - Style sort indicators (arrows)
    - Style sortable header hover states
    - _Requirements: 1.4_
  
  - [x] 8.3 Update base.html to include table sorter assets
    - Add script and stylesheet references
    - Initialize TableSorter on page load
    - _Requirements: 1.5, 1.7_
  
  - [x] 8.4 Add data-sortable attributes to table templates
    - Update projects.html table headers
    - Update requests.html table headers
    - Update project_view.html table headers
    - Update request_view.html table headers
    - Update status.html table headers
    - _Requirements: 1.5_
  
  - [x] 8.5 Write property test for table sorting
    - **Property 1: Table Sorting Correctness by Data Type**
    - **Validates: Requirements 1.1, 1.6**

- [x] 9. Project View Markdown Rendering
  - [x] 9.1 Update project_view.html to render Project Prompt as markdown
    - Apply |markdown filter to prjprompt field
    - Add .markdown-content wrapper div
    - Handle empty/null prompt with dash placeholder
    - _Requirements: 2.1, 2.4_
  
  - [x] 9.2 Add markdown-content CSS styles
    - Style headings, lists, code blocks
    - Ensure consistent look with existing UI
    - _Requirements: 2.5_

- [x] 10. Documents Section in Request View
  - [x] 10.1 Add route to fetch request documents
    - Update request_view route to include documents
    - Call get_request_docs(reqid)
    - _Requirements: 6.1, 6.2_
  
  - [x] 10.2 Create document viewer route
    - Add /docs/<int:doc_id> route
    - Read file content from doc_path
    - Render as markdown
    - Handle file not found errors
    - _Requirements: 6.3, 6.4_
  
  - [x] 10.3 Update request_view.html with Documents section
    - Add Documents section with sortable table
    - Display Doc Name, Phase, File Path, Created At columns
    - Make doc_name a hyperlink to viewer route
    - Show empty state when no documents
    - _Requirements: 6.1, 6.2, 6.3, 6.5, 6.6, 6.7_
  
  - [x] 10.4 Create document_view.html template
    - Display rendered markdown content
    - Show file path and metadata
    - Add back navigation
    - _Requirements: 6.4_
  
  - [x] 10.5 Write property test for document viewing
    - **Property 10: Document Viewing with Markdown Rendering**
    - **Validates: Requirements 6.4**

- [x] 11. Checkpoint - Web UI Complete
  - Ensure all web UI tests pass, ask the user if questions arise.

- [x] 12. Web Server Status CLI Command
  - [x] 12.1 Create web status utilities
    - Create is_web_server_running(host, port) function
    - Create get_web_server_pid() function (if detectable)
    - Create get_web_status() function returning status dict
    - _Requirements: 7.2, 7.3, 7.5_
  
  - [x] 12.2 Add bw web status command to cli.py
    - Create web_group if not exists
    - Add status subcommand
    - Display running status, host, port, PID
    - Display configured defaults
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 12.3 Write unit tests for web status command
    - Test output when server running
    - Test output when server not running
    - Test display of configured settings
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 13. Final Checkpoint - All Features Complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Update exports and documentation
  - [x] 14.1 Update db/__init__.py exports
    - Export new request_doc functions
    - _Requirements: 4.1_
  
  - [x] 14.2 Update loop/__init__.py exports
    - Export DocTracker class
    - _Requirements: 5.3_

## Notes

- All tasks including property tests are required for comprehensive validation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation order ensures dependencies are satisfied (database first, then backend, then frontend)
