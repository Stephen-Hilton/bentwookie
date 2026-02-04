"""Property-based tests for request document cascade delete.

# Feature: bentwookie-web-ui-enhancements, Property 6: Request Document Cascade Delete
# **Validates: Requirements 4.2, 4.3**

Property Definition:
*For any* request with associated documents, deleting the request SHALL result in
all associated document records being deleted from the Requests_Docs_Table.
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

# Strategy for number of documents (1-10 as per task)
num_docs_strategy = st.integers(min_value=1, max_value=10)


def create_request_doc_raw(conn, reqid: int, doc_name: str, doc_path: str, doc_phase: str | None) -> int:
    """Create a request document record using raw SQL.
    
    This is a helper function since CRUD functions may not exist yet.
    """
    cursor = conn.execute(
        """
        INSERT INTO request_doc (reqid, doc_name, doc_path, doc_phase)
        VALUES (?, ?, ?, ?)
        """,
        (reqid, doc_name, doc_path, doc_phase),
    )
    return cursor.lastrowid


def get_request_docs_raw(conn, reqid: int) -> list[dict]:
    """Get all documents for a request using raw SQL.
    
    This is a helper function since CRUD functions may not exist yet.
    """
    cursor = conn.execute(
        "SELECT * FROM request_doc WHERE reqid = ?",
        (reqid,),
    )
    return [dict(row) for row in cursor.fetchall()]


def count_request_docs_raw(conn, reqid: int) -> int:
    """Count documents for a request using raw SQL."""
    cursor = conn.execute(
        "SELECT COUNT(*) as cnt FROM request_doc WHERE reqid = ?",
        (reqid,),
    )
    row = cursor.fetchone()
    return row["cnt"] if row else 0


def unique_name(base: str) -> str:
    """Generate a unique name to avoid conflicts between test iterations."""
    return f"{base}_{uuid.uuid4().hex[:8]}"


class TestCascadeDeleteProperty:
    """Property-based tests for cascade delete behavior.
    
    # Feature: bentwookie-web-ui-enhancements, Property 6: Request Document Cascade Delete
    # **Validates: Requirements 4.2, 4.3**
    """

    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        request_name=request_name_strategy,
        num_docs=num_docs_strategy,
        doc_names=st.lists(doc_name_strategy, min_size=1, max_size=10),
        doc_paths=st.lists(doc_path_strategy, min_size=1, max_size=10),
        doc_phases=st.lists(doc_phase_strategy, min_size=1, max_size=10),
    )
    def test_cascade_delete_removes_all_documents(
        self,
        request_name: str,
        num_docs: int,
        doc_names: list[str],
        doc_paths: list[str],
        doc_phases: list[str | None],
    ):
        """Property: Deleting a request removes all associated documents.
        
        # Feature: bentwookie-web-ui-enhancements, Property 6: Request Document Cascade Delete
        # **Validates: Requirements 4.2, 4.3**
        
        For any request with associated documents, deleting the request SHALL result
        in all associated document records being deleted from the Requests_Docs_Table.
        """
        # Step 1: Create a project (required for request) with unique name
        project_name = unique_name(f"proj_{request_name[:10]}")
        prjid = queries.create_project(project_name)
        
        try:
            # Step 2: Create a request
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name(request_name),
                reqprompt="Test prompt for cascade delete property test",
            )
            
            # Step 3: Create documents for the request
            # Use the minimum of num_docs and available generated data
            actual_num_docs = min(num_docs, len(doc_names), len(doc_paths), len(doc_phases))
            
            with connection.get_db() as conn:
                created_doc_ids = []
                for i in range(actual_num_docs):
                    doc_id = create_request_doc_raw(
                        conn,
                        reqid=reqid,
                        doc_name=doc_names[i],
                        doc_path=doc_paths[i],
                        doc_phase=doc_phases[i],
                    )
                    created_doc_ids.append(doc_id)
                
                # Verify documents were created
                docs_before = get_request_docs_raw(conn, reqid)
                assert len(docs_before) == actual_num_docs, (
                    f"Expected {actual_num_docs} documents before delete, got {len(docs_before)}"
                )
            
            # Step 4: Delete the request
            result = queries.delete_request(reqid)
            assert result is True, "Request deletion should succeed"
            
            # Step 5: Verify all associated documents are deleted (CASCADE)
            with connection.get_db() as conn:
                docs_after = get_request_docs_raw(conn, reqid)
                assert len(docs_after) == 0, (
                    f"Expected 0 documents after cascade delete, got {len(docs_after)}. "
                    f"Documents remaining: {docs_after}"
                )
                
                # Also verify by counting
                count_after = count_request_docs_raw(conn, reqid)
                assert count_after == 0, (
                    f"Expected count 0 after cascade delete, got {count_after}"
                )
        finally:
            # Cleanup: Delete the project
            queries.delete_project(prjid)

    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        request_name=request_name_strategy,
        doc_name=doc_name_strategy,
        doc_path=doc_path_strategy,
        doc_phase=doc_phase_strategy,
    )
    def test_cascade_delete_single_document(
        self,
        request_name: str,
        doc_name: str,
        doc_path: str,
        doc_phase: str | None,
    ):
        """Property: Deleting a request with a single document removes that document.
        
        # Feature: bentwookie-web-ui-enhancements, Property 6: Request Document Cascade Delete
        # **Validates: Requirements 4.2, 4.3**
        
        Edge case: Single document should also be cascade deleted.
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
            with connection.get_db() as conn:
                doc_id = create_request_doc_raw(conn, reqid, doc_name, doc_path, doc_phase)
                
                # Verify document exists
                docs = get_request_docs_raw(conn, reqid)
                assert len(docs) == 1
            
            # Delete request
            queries.delete_request(reqid)
            
            # Verify document is gone
            with connection.get_db() as conn:
                docs_after = get_request_docs_raw(conn, reqid)
                assert len(docs_after) == 0, "Single document should be cascade deleted"
        finally:
            # Cleanup
            queries.delete_project(prjid)

    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        request_name=request_name_strategy,
    )
    def test_cascade_delete_no_documents(
        self,
        request_name: str,
    ):
        """Property: Deleting a request with no documents succeeds without error.
        
        # Feature: bentwookie-web-ui-enhancements, Property 6: Request Document Cascade Delete
        # **Validates: Requirements 4.2, 4.3**
        
        Edge case: Request with no documents should delete cleanly.
        """
        # Create project and request with unique names
        project_name = unique_name(f"nodoc_{request_name[:10]}")
        prjid = queries.create_project(project_name)
        
        try:
            reqid = queries.create_request(
                prjid=prjid,
                reqname=unique_name(request_name),
                reqprompt="Test prompt",
            )
            
            # Verify no documents exist
            with connection.get_db() as conn:
                docs = get_request_docs_raw(conn, reqid)
                assert len(docs) == 0
            
            # Delete request - should succeed without error
            result = queries.delete_request(reqid)
            assert result is True
            
            # Verify request is gone
            assert queries.get_request(reqid) is None
        finally:
            # Cleanup
            queries.delete_project(prjid)

    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        request_name1=request_name_strategy,
        request_name2=request_name_strategy,
        doc_name=doc_name_strategy,
        doc_path=doc_path_strategy,
    )
    def test_cascade_delete_only_affects_target_request(
        self,
        request_name1: str,
        request_name2: str,
        doc_name: str,
        doc_path: str,
    ):
        """Property: Cascade delete only removes documents for the deleted request.
        
        # Feature: bentwookie-web-ui-enhancements, Property 6: Request Document Cascade Delete
        # **Validates: Requirements 4.2, 4.3**
        
        Documents belonging to other requests should not be affected.
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
                reqprompt="Prompt 1"
            )
            reqid2 = queries.create_request(
                prjid=prjid, 
                reqname=unique_name(request_name2), 
                reqprompt="Prompt 2"
            )
            
            # Create documents for both requests
            with connection.get_db() as conn:
                create_request_doc_raw(conn, reqid1, doc_name + "_req1", doc_path + "/req1", "plan")
                create_request_doc_raw(conn, reqid2, doc_name + "_req2", doc_path + "/req2", "dev")
                
                # Verify both have documents
                assert count_request_docs_raw(conn, reqid1) == 1
                assert count_request_docs_raw(conn, reqid2) == 1
            
            # Delete only request 1
            queries.delete_request(reqid1)
            
            # Verify request 1's documents are gone, but request 2's remain
            with connection.get_db() as conn:
                assert count_request_docs_raw(conn, reqid1) == 0, "Request 1 docs should be deleted"
                assert count_request_docs_raw(conn, reqid2) == 1, "Request 2 docs should remain"
                
                # Verify the remaining document belongs to request 2
                remaining_docs = get_request_docs_raw(conn, reqid2)
                assert len(remaining_docs) == 1
                assert remaining_docs[0]["reqid"] == reqid2
        finally:
            # Cleanup
            if reqid2:
                queries.delete_request(reqid2)
            queries.delete_project(prjid)
