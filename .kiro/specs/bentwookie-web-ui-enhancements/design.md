# Design Document: BentWookie Web UI Enhancements

## Overview

This design document describes the technical implementation for enhancing the BentWookie web UI with sortable tables, markdown rendering, loop controls reconciliation, request document tracking, and a web server status CLI command. The implementation leverages the existing Flask-based architecture, SQLite database, and Jinja2 templating system.

## Architecture

The enhancements follow the existing BentWookie architecture patterns:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Table Sorter│  │  Markdown   │  │    Document Viewer      │  │
│  │    (JS)     │  │  Renderer   │  │       (JS/HTML)         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Flask Web App                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Routes    │  │  Templates  │  │    Static Assets        │  │
│  │  (app.py)   │  │  (Jinja2)   │  │    (CSS/JS)             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  queries.py │  │  schema.sql │  │    connection.py        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Loop Processing                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  phases.py  │  │ processor.py│  │    Doc Tracker          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Table Sorter Component (JavaScript)

A client-side JavaScript module that adds sorting functionality to HTML tables.

```javascript
// Interface: TableSorter
class TableSorter {
    constructor(tableElement: HTMLTableElement)
    
    // Initialize sorting on all sortable columns
    init(): void
    
    // Sort table by specified column index
    sortByColumn(columnIndex: number, direction: 'asc' | 'desc'): void
    
    // Get current sort state
    getSortState(): { column: number | null, direction: 'asc' | 'desc' }
    
    // Compare function for different data types
    compareValues(a: string, b: string, type: 'text' | 'number' | 'date'): number
}
```

**Implementation Details:**
- Attach click handlers to `<th>` elements with `data-sortable="true"` attribute
- Use `data-sort-type` attribute to specify column type (text, number, date)
- Toggle sort direction on repeated clicks
- Add CSS classes for sort indicators (`.sort-asc`, `.sort-desc`)
- Preserve original row order for reset capability

### 2. Markdown Renderer Component

Server-side markdown rendering using Python's `markdown` library with client-side styling.

```python
# Interface: render_markdown
def render_markdown(text: str) -> str:
    """
    Convert markdown text to sanitized HTML.
    
    Args:
        text: Raw markdown string
        
    Returns:
        Sanitized HTML string
    """
```

**Implementation Details:**
- Use `markdown` library with `fenced_code` and `tables` extensions
- Sanitize output using `bleach` library to prevent XSS
- Create Jinja2 filter `|markdown` for template usage
- Apply `.markdown-content` CSS class for consistent styling

### 3. Loop Controls Settings Interface

Extended settings management for all loop control options.

```python
# Extended settings functions in settings.py
def get_max_turns() -> int:
    """Get max turns per phase (default: 50)."""

def set_max_turns(turns: int) -> None:
    """Set max turns per phase."""

def get_all_loop_settings() -> dict:
    """Get all loop-related settings including commit settings."""
```

**Web UI Form Fields:**
- Poll Interval (number input, min=1)
- Max Iterations (number input, min=0)
- Max Turns (number input, min=1)
- Doc Retention Days (number input, min=0)
- Commit Enabled (checkbox)
- Commit Branch Mode (select: current/other)
- Commit Branch Name (text input, conditional)

### 4. Request Documents Database Interface

```python
# Database operations in queries.py

def create_request_doc(
    reqid: int,
    doc_name: str,
    doc_path: str,
    doc_phase: str | None = None
) -> int:
    """Create a new request document record."""

def get_request_docs(reqid: int) -> list[dict]:
    """Get all documents for a request."""

def delete_request_docs(reqid: int) -> int:
    """Delete all documents for a request. Returns count deleted."""

def get_request_doc(doc_id: int) -> dict | None:
    """Get a single document by ID."""
```

### 5. Document Tracker Component

Parses LLM responses to extract document metadata.

```python
# Interface: DocTracker in loop/doc_tracker.py
class DocTracker:
    # Pattern to match document output in LLM response
    DOC_PATTERN = r'\[DOC:([^\]]+)\]\s*path:\s*([^\n]+)'
    
    def parse_response(self, response: str) -> list[dict]:
        """
        Extract document metadata from LLM response.
        
        Returns:
            List of dicts with 'name' and 'path' keys
        """
    
    def save_docs(self, reqid: int, docs: list[dict], phase: str) -> int:
        """
        Save extracted documents to database.
        
        Returns:
            Number of documents saved
        """
```

**LLM Output Format:**
```
[DOC:PLAN.md] path: /path/to/project/PLAN.md
[DOC:custom_output.md] path: /path/to/project/custom_output.md
```

### 6. Document Viewer Route

```python
# New route in app.py
@app.route("/docs/<int:doc_id>")
def view_document(doc_id: int):
    """
    Display a document rendered as markdown.
    
    Returns:
        Rendered template with markdown content
    """
```

### 7. Web Server Status Component

```python
# Functions in web/status.py (new file)
def get_web_server_pid() -> int | None:
    """Get PID of running web server if detectable."""

def is_web_server_running(host: str, port: int) -> bool:
    """Check if web server is responding."""

def get_web_status() -> dict:
    """
    Get comprehensive web server status.
    
    Returns:
        Dict with keys: running, host, port, pid, url
    """
```

```python
# CLI command in cli.py
@web_group.command("status")
def web_status():
    """Show web server status."""
```

## Data Models

### Request Documents Table Schema

```sql
-- New table in schema.sql
CREATE TABLE IF NOT EXISTS request_doc (
    docid INTEGER PRIMARY KEY AUTOINCREMENT,
    reqid INTEGER NOT NULL,
    doc_name TEXT NOT NULL,
    doc_path TEXT NOT NULL,
    doc_phase TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reqid) REFERENCES request(reqid) ON DELETE CASCADE
);

-- Index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_request_doc_reqid ON request_doc(reqid);
```

### Document Record Structure

```python
@dataclass
class RequestDoc:
    docid: int
    reqid: int
    doc_name: str
    doc_path: str
    doc_phase: str | None
    created_at: datetime
```

### Extended Settings Structure

```python
# Updated DEFAULT_SETTINGS in settings.py
DEFAULT_SETTINGS = {
    "auth_mode": "max",
    "model": "claude-opus-4-5",
    "max_turns": 50,           # Already exists
    "poll_interval": 30,
    "loop_paused": False,
    "max_iterations": 0,
    "doc_retention_days": 30,
    "commit_enabled": True,
    "commit_branch_mode": "current",
    "commit_branch_name": None,
    "web_host": "127.0.0.1",   # New: default web host
    "web_port": 5000,          # New: default web port
}
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Table Sorting Correctness by Data Type

*For any* array of table row data and any column with a specified data type (text, number, or date), sorting by that column SHALL produce rows ordered correctly according to the data type's natural ordering (alphabetical for text, numerical for numbers, chronological for dates).

**Validates: Requirements 1.1, 1.6**

### Property 2: Markdown Rendering Element Support

*For any* valid markdown string containing headings, bold, italic, lists, code blocks, or links, the Markdown_Renderer SHALL produce HTML output containing the corresponding HTML elements (`<h1>`-`<h6>`, `<strong>`, `<em>`, `<ul>`/`<ol>`/`<li>`, `<pre>`/`<code>`, `<a>`).

**Validates: Requirements 2.1, 2.2**

### Property 3: Markdown XSS Sanitization

*For any* markdown input containing potentially malicious content (script tags, event handlers, javascript: URLs), the Markdown_Renderer output SHALL NOT contain any executable JavaScript code or event handlers.

**Validates: Requirements 2.3**

### Property 4: Settings Round-Trip Persistence

*For any* valid loop control setting value, updating the setting via the Web_UI and then reading it back SHALL return the same value that was set.

**Validates: Requirements 3.2, 3.3**

### Property 5: Settings Input Validation

*For any* loop control setting with a defined valid range, attempting to set a value outside that range SHALL be rejected or clamped to the valid range (e.g., poll_interval < 1 should be rejected or set to 1).

**Validates: Requirements 3.4**

### Property 6: Request Document Cascade Delete

*For any* request with associated documents, deleting the request SHALL result in all associated document records being deleted from the Requests_Docs_Table.

**Validates: Requirements 4.2, 4.3**

### Property 7: Multiple Documents Per Request

*For any* request, the system SHALL allow creating multiple document records with different doc_names, and retrieving documents for that request SHALL return all created documents.

**Validates: Requirements 4.5**

### Property 8: Arbitrary Document Names

*For any* non-empty string as a document name (including phase names like "plan", "dev", "test" and custom names like "IP_Output.md"), the system SHALL successfully store and retrieve the document record with that name.

**Validates: Requirements 4.6, 5.5**

### Property 9: Document Tracker Parsing

*For any* LLM response containing document metadata in the format `[DOC:name] path: /path/to/file`, the Doc_Tracker SHALL extract all document entries and return a list containing the correct name and path for each.

**Validates: Requirements 5.2, 5.3**

### Property 10: Document Viewing with Markdown Rendering

*For any* valid document record pointing to an existing markdown file, viewing the document SHALL display the file content rendered as HTML with markdown formatting applied.

**Validates: Requirements 6.4**

## Error Handling

### Database Errors

- **Foreign Key Violations**: When creating a request_doc with an invalid reqid, return a clear error message indicating the request does not exist
- **File Not Found**: When viewing a document whose file no longer exists, display an error message with the expected path
- **Database Connection Errors**: Gracefully handle SQLite connection issues with user-friendly error messages

### Input Validation Errors

- **Invalid Settings Values**: Display validation errors inline in the form with specific guidance
- **Empty Required Fields**: Prevent form submission and highlight required fields
- **Invalid Markdown**: Render as plain text if markdown parsing fails

### File System Errors

- **Permission Denied**: Display error when document file cannot be read due to permissions
- **Path Traversal Attempts**: Sanitize and validate file paths to prevent directory traversal attacks

### Web Server Status Errors

- **Port Already in Use**: Detect and report when the configured port is occupied
- **Network Errors**: Handle connection timeouts gracefully in status checks

## Testing Strategy

### Unit Tests

Unit tests will verify specific examples and edge cases:

1. **Table Sorter**
   - Test sorting empty arrays
   - Test sorting single-element arrays
   - Test sorting with null/undefined values
   - Test sort direction toggle

2. **Markdown Renderer**
   - Test empty string input
   - Test null input
   - Test malformed markdown
   - Test each supported element type individually

3. **Settings Management**
   - Test default values
   - Test boundary values (min/max)
   - Test invalid type inputs

4. **Document Tracker**
   - Test empty response
   - Test response with no documents
   - Test malformed document entries
   - Test multiple documents in single response

5. **Database Operations**
   - Test CRUD operations for request_doc table
   - Test cascade delete behavior
   - Test index usage

### Property-Based Tests

Property-based tests will use the `hypothesis` library for Python to verify universal properties across many generated inputs. Each test will run a minimum of 100 iterations.

**Test Configuration:**
```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
```

**Property Test Tags:**
Each property test will be tagged with a comment referencing the design property:
```python
# Feature: bentwookie-web-ui-enhancements, Property 1: Table Sorting Correctness by Data Type
```

### Integration Tests

1. **End-to-End Document Flow**
   - Create request → Run phase → Verify documents tracked → View documents

2. **Settings Persistence**
   - Update settings via Web UI → Verify settings file updated → Verify daemon uses new settings

3. **Web Server Status**
   - Start web server → Check status → Stop server → Check status again

### Test Coverage Goals

- Minimum 80% code coverage for new code
- 100% coverage for database operations
- 100% coverage for security-sensitive code (XSS sanitization, path validation)
