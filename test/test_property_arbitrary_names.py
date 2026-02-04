"""Property-based tests for arbitrary document names.

# Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
# **Validates: Requirements 4.6, 5.5**

Property Definition:
*For any* non-empty string as a document name (including phase names like "plan",
"dev", "test" and custom names like "IP_Output.md"), the system SHALL successfully
store and retrieve the document record with that name.
"""

import tempfile
import uuid
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck, strategies as st

from bentwookie.db import connection, queries


# Module-level temp database setup
_temp_db_path: Path | None = None


def setup_module(module):
    """Set up a temporary database for the entire test module."""
    global _temp_db_path
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        _temp_db_path = Path(f.name)
    
    connection.set_db_path(_temp_db_path)
    connection.init_db()


def teardown_module(module):
    """Clean up the temporary database."""
    global _temp_db_path
    if _temp_db_path and _temp_db_path.exists():
        _temp_db_path.unlink()


def unique_name(base: str) -> str:
    """Generate a unique name to avoid conflicts between test iterations."""
    return f"{base}_{uuid.uuid4().hex[:8]}"


# =============================================================================
# Strategies for generating test data
# =============================================================================

# Strategy for generating arbitrary non-empty document names
# Includes letters, numbers, punctuation, and unicode characters
arbitrary_doc_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),  # Letters, Numbers, Punctuation, Symbols
        blacklist_characters="\x00",  # Exclude null character
    ),
    min_size=1,
    max_size=100,
).filter(lambda x: x.strip())  # Ensure non-empty after stripping

# Strategy for generating unicode document names
unicode_doc_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S", "M"),  # Include marks for accents
        blacklist_characters="\x00",
    ),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())

# Strategy for phase names (specific test cases)
phase_name_strategy = st.sampled_from(["plan", "dev", "test", "document", "commit", "verify", "deploy"])

# Strategy for custom file-like names
custom_file_name_strategy = st.sampled_from([
    "IP_Output.md",
    "custom_report.txt",
    "PLAN.md",
    "DEV.md",
    "TEST.md",
    "README.md",
    "output_2024.json",
    "data.csv",
    "report-final.pdf",
    "my_document.docx",
])

# Strategy for document paths
doc_path_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=100,
).filter(lambda x: x.strip())

# Strategy for document phases
doc_phase_strategy = st.sampled_from(["plan", "dev", "test", "document", "commit", None])


class TestArbitraryDocumentNamesProperty:
    """Property-based tests for arbitrary document names.
    
    # Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
    # **Validates: Requirements 4.6, 5.5**
    """

    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        doc_name=arbitrary_doc_name_strategy,
        doc_path=doc_path_strategy,
        doc_phase=doc_phase_strategy,
    )
    def test_arbitrary_names_stored_and_retrieved(
        self,
        doc_name: str,
        doc_path: str,
        doc_phase: str | None,
    ):
        """Property: Any non-empty string as document name is stored and retrieved exactly.
        
        # Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
        # **Validates: Requirements 4.6, 5.5**
        
        For any non-empty string as a document name, the system SHALL successfully
        store and retrieve the document record with that name.
        """
        # Create project and request with unique names
        project_name = unique_name("arb_proj")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name("arb_req"),
                reqprompt="Test prompt for arbitrary names property test",
            )
            
            # Create document with arbitrary name
            docid = queries.create_request_doc(
                reqid=reqid,
                doc_name=doc_name,
                doc_path=doc_path,
                doc_phase=doc_phase,
            )
            
            # Verify document was created
            assert docid is not None, "Document ID should not be None"
            assert docid > 0, "Document ID should be positive"
            
            # Retrieve document by ID
            doc = queries.get_request_doc(docid)
            assert doc is not None, f"Document with ID {docid} should exist"
            
            # Verify the name is stored exactly as provided
            assert doc["doc_name"] == doc_name, (
                f"Document name mismatch: expected '{doc_name}', got '{doc['doc_name']}'"
            )
            assert doc["doc_path"] == doc_path, (
                f"Document path mismatch: expected '{doc_path}', got '{doc['doc_path']}'"
            )
            assert doc["doc_phase"] == doc_phase, (
                f"Document phase mismatch: expected '{doc_phase}', got '{doc['doc_phase']}'"
            )
            
            # Also verify via get_request_docs
            docs = queries.get_request_docs(reqid)
            assert len(docs) == 1, f"Expected 1 document, got {len(docs)}"
            assert docs[0]["doc_name"] == doc_name, (
                f"Document name in list mismatch: expected '{doc_name}', got '{docs[0]['doc_name']}'"
            )
        finally:
            # Cleanup
            queries.delete_request(reqid)
            queries.delete_project(prjid)

    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        phase_name=phase_name_strategy,
        doc_phase=doc_phase_strategy,
    )
    def test_phase_names_as_document_names(
        self,
        phase_name: str,
        doc_phase: str | None,
    ):
        """Property: Phase names can be used as document names.
        
        # Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
        # **Validates: Requirements 4.6, 5.5**
        
        Phase names like "plan", "dev", "test" should be valid document names.
        """
        # Create project and request with unique names
        project_name = unique_name("phase_proj")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name("phase_req"),
                reqprompt="Test prompt",
            )
            
            # Create document with phase name as doc_name
            docid = queries.create_request_doc(
                reqid=reqid,
                doc_name=phase_name,
                doc_path=f"/path/to/{phase_name}",
                doc_phase=doc_phase,
            )
            
            # Verify document was created and name is preserved
            doc = queries.get_request_doc(docid)
            assert doc is not None, f"Document should exist"
            assert doc["doc_name"] == phase_name, (
                f"Phase name '{phase_name}' should be stored exactly as document name"
            )
        finally:
            # Cleanup
            queries.delete_request(reqid)
            queries.delete_project(prjid)

    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        custom_name=custom_file_name_strategy,
        doc_phase=doc_phase_strategy,
    )
    def test_custom_file_names(
        self,
        custom_name: str,
        doc_phase: str | None,
    ):
        """Property: Custom file names like "IP_Output.md" are stored correctly.
        
        # Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
        # **Validates: Requirements 4.6, 5.5**
        
        Custom names like "IP_Output.md", "custom_report.txt" should be valid.
        """
        # Create project and request with unique names
        project_name = unique_name("custom_proj")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name("custom_req"),
                reqprompt="Test prompt",
            )
            
            # Create document with custom file name
            docid = queries.create_request_doc(
                reqid=reqid,
                doc_name=custom_name,
                doc_path=f"/path/to/{custom_name}",
                doc_phase=doc_phase,
            )
            
            # Verify document was created and name is preserved
            doc = queries.get_request_doc(docid)
            assert doc is not None, f"Document should exist"
            assert doc["doc_name"] == custom_name, (
                f"Custom name '{custom_name}' should be stored exactly as document name"
            )
        finally:
            # Cleanup
            queries.delete_request(reqid)
            queries.delete_project(prjid)

    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        doc_name=unicode_doc_name_strategy,
        doc_path=doc_path_strategy,
    )
    def test_unicode_document_names(
        self,
        doc_name: str,
        doc_path: str,
    ):
        """Property: Unicode characters in document names are preserved.
        
        # Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
        # **Validates: Requirements 4.6, 5.5**
        
        Document names with unicode characters should be stored and retrieved correctly.
        """
        # Create project and request with unique names
        project_name = unique_name("unicode_proj")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name("unicode_req"),
                reqprompt="Test prompt",
            )
            
            # Create document with unicode name
            docid = queries.create_request_doc(
                reqid=reqid,
                doc_name=doc_name,
                doc_path=doc_path,
                doc_phase="dev",
            )
            
            # Verify document was created and unicode name is preserved
            doc = queries.get_request_doc(docid)
            assert doc is not None, f"Document should exist"
            assert doc["doc_name"] == doc_name, (
                f"Unicode name should be stored exactly: expected '{doc_name}', got '{doc['doc_name']}'"
            )
        finally:
            # Cleanup
            queries.delete_request(reqid)
            queries.delete_project(prjid)

    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        doc_names=st.lists(
            arbitrary_doc_name_strategy,
            min_size=2,
            max_size=10,
            unique=True,
        ),
    )
    def test_multiple_arbitrary_names_per_request(
        self,
        doc_names: list[str],
    ):
        """Property: Multiple documents with arbitrary names can be stored per request.
        
        # Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
        # **Validates: Requirements 4.6, 5.5**
        
        Multiple documents with different arbitrary names should all be stored
        and retrievable for the same request.
        """
        # Create project and request with unique names
        project_name = unique_name("multi_arb_proj")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name("multi_arb_req"),
                reqprompt="Test prompt",
            )
            
            # Create multiple documents with arbitrary names
            created_doc_ids = []
            for i, doc_name in enumerate(doc_names):
                docid = queries.create_request_doc(
                    reqid=reqid,
                    doc_name=doc_name,
                    doc_path=f"/path/to/doc_{i}",
                    doc_phase="dev" if i % 2 == 0 else "test",
                )
                created_doc_ids.append(docid)
            
            # Retrieve all documents
            docs = queries.get_request_docs(reqid)
            
            # Verify all documents are present
            assert len(docs) == len(doc_names), (
                f"Expected {len(doc_names)} documents, got {len(docs)}"
            )
            
            # Verify all names are present
            retrieved_names = {doc["doc_name"] for doc in docs}
            for name in doc_names:
                assert name in retrieved_names, (
                    f"Document name '{name}' not found in retrieved documents"
                )
        finally:
            # Cleanup
            queries.delete_request(reqid)
            queries.delete_project(prjid)

    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        doc_name=st.text(
            alphabet=st.characters(
                whitelist_categories=("P",),  # Only punctuation
                blacklist_characters="\x00",
            ),
            min_size=1,
            max_size=20,
        ).filter(lambda x: x.strip()),
    )
    def test_special_character_names(
        self,
        doc_name: str,
    ):
        """Property: Document names with special characters are stored correctly.
        
        # Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
        # **Validates: Requirements 4.6, 5.5**
        
        Document names containing only special characters should be valid.
        """
        # Create project and request with unique names
        project_name = unique_name("special_proj")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name("special_req"),
                reqprompt="Test prompt",
            )
            
            # Create document with special character name
            docid = queries.create_request_doc(
                reqid=reqid,
                doc_name=doc_name,
                doc_path="/path/to/special",
                doc_phase="dev",
            )
            
            # Verify document was created and name is preserved
            doc = queries.get_request_doc(docid)
            assert doc is not None, f"Document should exist"
            assert doc["doc_name"] == doc_name, (
                f"Special character name should be stored exactly"
            )
        finally:
            # Cleanup
            queries.delete_request(reqid)
            queries.delete_project(prjid)

    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        doc_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
            min_size=50,
            max_size=100,
        ).filter(lambda x: x.strip()),
    )
    def test_long_document_names(
        self,
        doc_name: str,
    ):
        """Property: Long document names are stored correctly.
        
        # Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
        # **Validates: Requirements 4.6, 5.5**
        
        Document names up to 100 characters should be stored and retrieved correctly.
        """
        # Create project and request with unique names
        project_name = unique_name("long_proj")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name("long_req"),
                reqprompt="Test prompt",
            )
            
            # Create document with long name
            docid = queries.create_request_doc(
                reqid=reqid,
                doc_name=doc_name,
                doc_path="/path/to/long",
                doc_phase="dev",
            )
            
            # Verify document was created and full name is preserved
            doc = queries.get_request_doc(docid)
            assert doc is not None, f"Document should exist"
            assert doc["doc_name"] == doc_name, (
                f"Long name should be stored exactly (length: {len(doc_name)})"
            )
            assert len(doc["doc_name"]) == len(doc_name), (
                f"Name length should be preserved: expected {len(doc_name)}, got {len(doc['doc_name'])}"
            )
        finally:
            # Cleanup
            queries.delete_request(reqid)
            queries.delete_project(prjid)

    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        doc_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=1,
        ),
    )
    def test_single_character_names(
        self,
        doc_name: str,
    ):
        """Property: Single character document names are valid.
        
        # Feature: bentwookie-web-ui-enhancements, Property 8: Arbitrary Document Names
        # **Validates: Requirements 4.6, 5.5**
        
        Edge case: Single character names should be valid document names.
        """
        # Create project and request with unique names
        project_name = unique_name("single_proj")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name("single_req"),
                reqprompt="Test prompt",
            )
            
            # Create document with single character name
            docid = queries.create_request_doc(
                reqid=reqid,
                doc_name=doc_name,
                doc_path="/path/to/single",
                doc_phase="dev",
            )
            
            # Verify document was created and name is preserved
            doc = queries.get_request_doc(docid)
            assert doc is not None, f"Document should exist"
            assert doc["doc_name"] == doc_name, (
                f"Single character name '{doc_name}' should be stored exactly"
            )
        finally:
            # Cleanup
            queries.delete_request(reqid)
            queries.delete_project(prjid)
