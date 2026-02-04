"""Property-based tests for multiple documents per request.

# Feature: bentwookie-web-ui-enhancements, Property 7: Multiple Documents Per Request
# **Validates: Requirements 4.5**

Property Definition:
*For any* request, the system SHALL allow creating multiple document records with
different doc_names, and retrieving documents for that request SHALL return all
created documents.
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


# Strategies for generating test data
request_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=30,
).filter(lambda x: x.strip())

doc_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())

doc_path_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=100,
).filter(lambda x: x.strip())

doc_phase_strategy = st.sampled_from(["plan", "dev", "test", "document", "commit", None])

# Strategy for number of documents (1-20 as per task)
num_docs_strategy = st.integers(min_value=1, max_value=20)


def unique_name(base: str) -> str:
    """Generate a unique name to avoid conflicts between test iterations."""
    return f"{base}_{uuid.uuid4().hex[:8]}"


class TestMultipleDocsPerRequestProperty:
    """Property-based tests for multiple documents per request.
    
    # Feature: bentwookie-web-ui-enhancements, Property 7: Multiple Documents Per Request
    # **Validates: Requirements 4.5**
    """

    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        request_name=request_name_strategy,
        num_docs=num_docs_strategy,
        doc_names=st.lists(doc_name_strategy, min_size=1, max_size=20, unique=True),
        doc_paths=st.lists(doc_path_strategy, min_size=1, max_size=20),
        doc_phases=st.lists(doc_phase_strategy, min_size=1, max_size=20),
    )
    def test_multiple_docs_created_and_retrieved(
        self,
        request_name: str,
        num_docs: int,
        doc_names: list[str],
        doc_paths: list[str],
        doc_phases: list[str | None],
    ):
        """Property: Multiple documents can be created and all are retrieved.
        
        # Feature: bentwookie-web-ui-enhancements, Property 7: Multiple Documents Per Request
        # **Validates: Requirements 4.5**
        
        For any request, the system SHALL allow creating multiple document records
        with different doc_names, and retrieving documents for that request SHALL
        return all created documents.
        """
        # Step 1: Create a project (required for request) with unique name
        project_name = unique_name(f"proj_{request_name[:10]}")
        prjid = queries.create_project(project_name)
        
        try:
            # Step 2: Create a request
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name(request_name),
                reqprompt="Test prompt for multiple docs property test",
            )
            
            # Step 3: Determine actual number of documents to create
            # Use the minimum of num_docs and available generated data
            actual_num_docs = min(num_docs, len(doc_names), len(doc_paths), len(doc_phases))
            
            # Step 4: Create multiple documents for the request
            created_doc_ids = []
            created_doc_names = []
            for i in range(actual_num_docs):
                doc_id = queries.create_request_doc(
                    reqid=reqid,
                    doc_name=doc_names[i],
                    doc_path=doc_paths[i],
                    doc_phase=doc_phases[i],
                )
                created_doc_ids.append(doc_id)
                created_doc_names.append(doc_names[i])
            
            # Step 5: Retrieve documents using get_request_docs()
            retrieved_docs = queries.get_request_docs(reqid)
            
            # Step 6: Verify all created documents are returned
            assert len(retrieved_docs) == actual_num_docs, (
                f"Expected {actual_num_docs} documents, got {len(retrieved_docs)}"
            )
            
            # Verify all document IDs are present
            retrieved_doc_ids = {doc["docid"] for doc in retrieved_docs}
            for doc_id in created_doc_ids:
                assert doc_id in retrieved_doc_ids, (
                    f"Document ID {doc_id} not found in retrieved documents"
                )
            
            # Verify all document names are present
            retrieved_doc_names = {doc["doc_name"] for doc in retrieved_docs}
            for doc_name in created_doc_names:
                assert doc_name in retrieved_doc_names, (
                    f"Document name '{doc_name}' not found in retrieved documents"
                )
            
            # Verify all documents belong to the correct request
            for doc in retrieved_docs:
                assert doc["reqid"] == reqid, (
                    f"Document {doc['docid']} has wrong reqid: {doc['reqid']} != {reqid}"
                )
        finally:
            # Cleanup: Delete the request (cascade deletes docs) and project
            queries.delete_request(reqid)
            queries.delete_project(prjid)

    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        request_name=request_name_strategy,
        num_docs=num_docs_strategy,
    )
    def test_multiple_docs_count_matches_created(
        self,
        request_name: str,
        num_docs: int,
    ):
        """Property: The count of retrieved documents matches the count of created documents.
        
        # Feature: bentwookie-web-ui-enhancements, Property 7: Multiple Documents Per Request
        # **Validates: Requirements 4.5**
        
        For any number of documents created (1-20), retrieving documents SHALL
        return exactly that many documents.
        """
        # Create project and request with unique names
        project_name = unique_name(f"count_{request_name[:10]}")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name(request_name),
                reqprompt="Test prompt",
            )
            
            # Create exactly num_docs documents with unique names
            for i in range(num_docs):
                queries.create_request_doc(
                    reqid=reqid,
                    doc_name=f"doc_{i}_{uuid.uuid4().hex[:6]}.md",
                    doc_path=f"/path/to/doc_{i}.md",
                    doc_phase="plan" if i % 2 == 0 else "dev",
                )
            
            # Retrieve and verify count
            retrieved_docs = queries.get_request_docs(reqid)
            assert len(retrieved_docs) == num_docs, (
                f"Expected {num_docs} documents, got {len(retrieved_docs)}"
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
        request_name=request_name_strategy,
        doc_names=st.lists(doc_name_strategy, min_size=2, max_size=10, unique=True),
    )
    def test_multiple_docs_unique_names_preserved(
        self,
        request_name: str,
        doc_names: list[str],
    ):
        """Property: Documents with unique names are all stored and retrievable.
        
        # Feature: bentwookie-web-ui-enhancements, Property 7: Multiple Documents Per Request
        # **Validates: Requirements 4.5**
        
        For any set of unique document names, all documents SHALL be stored
        and retrievable without name collision.
        """
        # Create project and request with unique names
        project_name = unique_name(f"unique_{request_name[:10]}")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name(request_name),
                reqprompt="Test prompt",
            )
            
            # Create documents with unique names
            for i, doc_name in enumerate(doc_names):
                queries.create_request_doc(
                    reqid=reqid,
                    doc_name=doc_name,
                    doc_path=f"/path/to/{doc_name}",
                    doc_phase="plan",
                )
            
            # Retrieve and verify all unique names are present
            retrieved_docs = queries.get_request_docs(reqid)
            retrieved_names = {doc["doc_name"] for doc in retrieved_docs}
            
            assert len(retrieved_names) == len(doc_names), (
                f"Expected {len(doc_names)} unique names, got {len(retrieved_names)}"
            )
            
            for name in doc_names:
                assert name in retrieved_names, (
                    f"Document name '{name}' not found in retrieved documents"
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
        request_name=request_name_strategy,
        num_docs=num_docs_strategy,
        doc_phases=st.lists(doc_phase_strategy, min_size=1, max_size=20),
    )
    def test_multiple_docs_different_phases(
        self,
        request_name: str,
        num_docs: int,
        doc_phases: list[str | None],
    ):
        """Property: Documents with different phases are all stored correctly.
        
        # Feature: bentwookie-web-ui-enhancements, Property 7: Multiple Documents Per Request
        # **Validates: Requirements 4.5**
        
        For any combination of phases (plan, dev, test, document, commit, None),
        all documents SHALL be stored with their correct phase values.
        """
        # Create project and request with unique names
        project_name = unique_name(f"phase_{request_name[:10]}")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name(request_name),
                reqprompt="Test prompt",
            )
            
            # Determine actual number of documents
            actual_num_docs = min(num_docs, len(doc_phases))
            
            # Create documents with different phases
            expected_phases = []
            for i in range(actual_num_docs):
                phase = doc_phases[i]
                queries.create_request_doc(
                    reqid=reqid,
                    doc_name=f"doc_{i}_{uuid.uuid4().hex[:6]}.md",
                    doc_path=f"/path/to/doc_{i}.md",
                    doc_phase=phase,
                )
                expected_phases.append(phase)
            
            # Retrieve and verify phases
            retrieved_docs = queries.get_request_docs(reqid)
            retrieved_phases = [doc["doc_phase"] for doc in retrieved_docs]
            
            # Sort both lists to compare (order may differ due to ORDER BY created_at DESC)
            assert sorted(retrieved_phases, key=lambda x: (x is None, x)) == sorted(
                expected_phases, key=lambda x: (x is None, x)
            ), (
                f"Phase mismatch: expected {expected_phases}, got {retrieved_phases}"
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
        request_name=request_name_strategy,
    )
    def test_single_doc_is_retrievable(
        self,
        request_name: str,
    ):
        """Property: A single document is also retrievable (edge case of 1:M).
        
        # Feature: bentwookie-web-ui-enhancements, Property 7: Multiple Documents Per Request
        # **Validates: Requirements 4.5**
        
        Edge case: The 1:M relationship should work for M=1.
        """
        # Create project and request with unique names
        project_name = unique_name(f"single_{request_name[:10]}")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name(request_name),
                reqprompt="Test prompt",
            )
            
            # Create single document
            doc_id = queries.create_request_doc(
                reqid=reqid,
                doc_name="single_doc.md",
                doc_path="/path/to/single_doc.md",
                doc_phase="plan",
            )
            
            # Retrieve and verify
            retrieved_docs = queries.get_request_docs(reqid)
            assert len(retrieved_docs) == 1, (
                f"Expected 1 document, got {len(retrieved_docs)}"
            )
            assert retrieved_docs[0]["docid"] == doc_id
            assert retrieved_docs[0]["doc_name"] == "single_doc.md"
        finally:
            # Cleanup
            queries.delete_request(reqid)
            queries.delete_project(prjid)

    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        request_name1=request_name_strategy,
        request_name2=request_name_strategy,
        num_docs1=st.integers(min_value=1, max_value=5),
        num_docs2=st.integers(min_value=1, max_value=5),
    )
    def test_multiple_requests_have_independent_docs(
        self,
        request_name1: str,
        request_name2: str,
        num_docs1: int,
        num_docs2: int,
    ):
        """Property: Documents for different requests are independent.
        
        # Feature: bentwookie-web-ui-enhancements, Property 7: Multiple Documents Per Request
        # **Validates: Requirements 4.5**
        
        For any two requests with different numbers of documents, retrieving
        documents for each request SHALL return only that request's documents.
        """
        # Create project with unique name
        project_name = unique_name(f"multi_{request_name1[:8]}")
        prjid = queries.create_project(project_name)
        
        reqid2 = None
        try:
            # Create two requests
            reqid1 = queries.create_request(
                prjid=prjid,
                reqname=unique_name(request_name1),
                reqprompt="Prompt 1",
            )
            reqid2 = queries.create_request(
                prjid=prjid,
                reqname=unique_name(request_name2),
                reqprompt="Prompt 2",
            )
            
            # Create documents for request 1
            for i in range(num_docs1):
                queries.create_request_doc(
                    reqid=reqid1,
                    doc_name=f"req1_doc_{i}_{uuid.uuid4().hex[:6]}.md",
                    doc_path=f"/path/req1/doc_{i}.md",
                    doc_phase="plan",
                )
            
            # Create documents for request 2
            for i in range(num_docs2):
                queries.create_request_doc(
                    reqid=reqid2,
                    doc_name=f"req2_doc_{i}_{uuid.uuid4().hex[:6]}.md",
                    doc_path=f"/path/req2/doc_{i}.md",
                    doc_phase="dev",
                )
            
            # Retrieve and verify independence
            docs1 = queries.get_request_docs(reqid1)
            docs2 = queries.get_request_docs(reqid2)
            
            assert len(docs1) == num_docs1, (
                f"Request 1: expected {num_docs1} docs, got {len(docs1)}"
            )
            assert len(docs2) == num_docs2, (
                f"Request 2: expected {num_docs2} docs, got {len(docs2)}"
            )
            
            # Verify all docs in docs1 belong to reqid1
            for doc in docs1:
                assert doc["reqid"] == reqid1, (
                    f"Doc {doc['docid']} should belong to request {reqid1}, not {doc['reqid']}"
                )
            
            # Verify all docs in docs2 belong to reqid2
            for doc in docs2:
                assert doc["reqid"] == reqid2, (
                    f"Doc {doc['docid']} should belong to request {reqid2}, not {doc['reqid']}"
                )
        finally:
            # Cleanup
            queries.delete_request(reqid1)
            if reqid2:
                queries.delete_request(reqid2)
            queries.delete_project(prjid)
