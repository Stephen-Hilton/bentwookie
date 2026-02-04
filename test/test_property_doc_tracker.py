"""Property-based tests for document tracker parsing.

# Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
# **Validates: Requirements 5.2, 5.3**

Property Definition:
*For any* LLM response containing document metadata in the format
`[DOC:name] path: /path/to/file`, the Doc_Tracker SHALL extract all document
entries and return a list containing the correct name and path for each.
"""

from hypothesis import given, settings, strategies as st

from bentwookie.loop.doc_tracker import DocTracker


# Strategies for generating test data

# Strategy for document names - alphanumeric with common file name characters
doc_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),  # Letters and numbers
        whitelist_characters="_-.",  # Common file name characters
    ),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip() and "]" not in x)  # Must be non-empty and not contain ]

# Strategy for document paths - Unix-style paths
path_segment_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="_-.",
    ),
    min_size=1,
    max_size=20,
).filter(lambda x: x.strip())

doc_path_strategy = st.builds(
    lambda segments: "/" + "/".join(segments),
    st.lists(path_segment_strategy, min_size=1, max_size=5),
)

# Strategy for surrounding text (text that appears around document markers)
surrounding_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="[]",  # Avoid characters that could interfere with pattern
    ),
    min_size=0,
    max_size=100,
)

# Strategy for number of documents in a response
num_docs_strategy = st.integers(min_value=1, max_value=10)


def build_doc_marker(name: str, path: str) -> str:
    """Build a document marker string in the expected format."""
    return f"[DOC:{name}] path: {path}"


def build_llm_response(doc_entries: list[tuple[str, str]], surrounding_texts: list[str]) -> str:
    """Build an LLM response containing document markers with surrounding text.
    
    Args:
        doc_entries: List of (name, path) tuples for documents
        surrounding_texts: List of text strings to intersperse between markers
        
    Returns:
        A string simulating an LLM response with document markers
    """
    parts = []
    for i, (name, path) in enumerate(doc_entries):
        # Add surrounding text before the marker if available
        if i < len(surrounding_texts):
            parts.append(surrounding_texts[i])
        parts.append(build_doc_marker(name, path))
    
    # Add any remaining surrounding text after the last marker
    if len(surrounding_texts) > len(doc_entries):
        parts.append(surrounding_texts[-1])
    
    return "\n".join(parts)


class TestDocTrackerParsingProperty:
    """Property-based tests for DocTracker.parse_response().
    
    # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
    # **Validates: Requirements 5.2, 5.3**
    """

    @settings(max_examples=25)
    @given(
        doc_name=doc_name_strategy,
        doc_path=doc_path_strategy,
    )
    def test_single_document_extracted_correctly(
        self,
        doc_name: str,
        doc_path: str,
    ):
        """Property: A single document marker is correctly extracted.
        
        # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
        # **Validates: Requirements 5.2, 5.3**
        
        For any valid document name and path, parsing a response containing
        a single document marker SHALL return a list with one entry containing
        the correct name and path.
        """
        tracker = DocTracker()
        
        # Build response with single document marker
        response = build_doc_marker(doc_name, doc_path)
        
        # Parse the response
        result = tracker.parse_response(response)
        
        # Verify exactly one document is extracted
        assert len(result) == 1, (
            f"Expected 1 document, got {len(result)} for response: {response}"
        )
        
        # Verify name and path are correct (stripped of whitespace)
        assert result[0]["name"] == doc_name.strip(), (
            f"Expected name '{doc_name.strip()}', got '{result[0]['name']}'"
        )
        assert result[0]["path"] == doc_path.strip(), (
            f"Expected path '{doc_path.strip()}', got '{result[0]['path']}'"
        )

    @settings(max_examples=25)
    @given(
        doc_entries=st.lists(
            st.tuples(doc_name_strategy, doc_path_strategy),
            min_size=1,
            max_size=10,
        ),
    )
    def test_multiple_documents_all_extracted(
        self,
        doc_entries: list[tuple[str, str]],
    ):
        """Property: All document markers in a response are extracted.
        
        # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
        # **Validates: Requirements 5.2, 5.3**
        
        For any number of document markers in a response, parsing SHALL
        return a list containing all documents with correct names and paths.
        """
        tracker = DocTracker()
        
        # Build response with multiple document markers
        response = build_llm_response(doc_entries, [])
        
        # Parse the response
        result = tracker.parse_response(response)
        
        # Verify correct number of documents extracted
        assert len(result) == len(doc_entries), (
            f"Expected {len(doc_entries)} documents, got {len(result)}"
        )
        
        # Verify each document has correct name and path
        for i, (expected_name, expected_path) in enumerate(doc_entries):
            assert result[i]["name"] == expected_name.strip(), (
                f"Document {i}: expected name '{expected_name.strip()}', "
                f"got '{result[i]['name']}'"
            )
            assert result[i]["path"] == expected_path.strip(), (
                f"Document {i}: expected path '{expected_path.strip()}', "
                f"got '{result[i]['path']}'"
            )

    @settings(max_examples=25)
    @given(
        doc_entries=st.lists(
            st.tuples(doc_name_strategy, doc_path_strategy),
            min_size=1,
            max_size=5,
        ),
        surrounding_texts=st.lists(surrounding_text_strategy, min_size=1, max_size=6),
    )
    def test_documents_extracted_with_surrounding_text(
        self,
        doc_entries: list[tuple[str, str]],
        surrounding_texts: list[str],
    ):
        """Property: Documents are extracted regardless of surrounding text.
        
        # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
        # **Validates: Requirements 5.2, 5.3**
        
        For any LLM response containing document markers interspersed with
        arbitrary text, parsing SHALL extract all documents correctly.
        """
        tracker = DocTracker()
        
        # Build response with surrounding text
        response = build_llm_response(doc_entries, surrounding_texts)
        
        # Parse the response
        result = tracker.parse_response(response)
        
        # Verify correct number of documents extracted
        assert len(result) == len(doc_entries), (
            f"Expected {len(doc_entries)} documents, got {len(result)}"
        )
        
        # Verify each document has correct name and path
        for i, (expected_name, expected_path) in enumerate(doc_entries):
            assert result[i]["name"] == expected_name.strip(), (
                f"Document {i}: expected name '{expected_name.strip()}', "
                f"got '{result[i]['name']}'"
            )
            assert result[i]["path"] == expected_path.strip(), (
                f"Document {i}: expected path '{expected_path.strip()}', "
                f"got '{result[i]['path']}'"
            )

    @settings(max_examples=25)
    @given(
        doc_name=doc_name_strategy,
        doc_path=doc_path_strategy,
        prefix_spaces=st.integers(min_value=0, max_value=5),
        suffix_spaces=st.integers(min_value=0, max_value=5),
    )
    def test_whitespace_in_name_and_path_stripped(
        self,
        doc_name: str,
        doc_path: str,
        prefix_spaces: int,
        suffix_spaces: int,
    ):
        """Property: Whitespace around name and path is stripped.
        
        # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
        # **Validates: Requirements 5.2, 5.3**
        
        For any document marker with extra whitespace around the name or path,
        parsing SHALL return the name and path with whitespace stripped.
        """
        tracker = DocTracker()
        
        # Build response with extra whitespace
        padded_name = " " * prefix_spaces + doc_name + " " * suffix_spaces
        padded_path = " " * prefix_spaces + doc_path + " " * suffix_spaces
        response = f"[DOC:{padded_name}] path: {padded_path}"
        
        # Parse the response
        result = tracker.parse_response(response)
        
        # Verify document is extracted with stripped values
        assert len(result) == 1, (
            f"Expected 1 document, got {len(result)}"
        )
        assert result[0]["name"] == doc_name.strip(), (
            f"Expected stripped name '{doc_name.strip()}', got '{result[0]['name']}'"
        )
        assert result[0]["path"] == doc_path.strip(), (
            f"Expected stripped path '{doc_path.strip()}', got '{result[0]['path']}'"
        )

    @settings(max_examples=25)
    @given(
        doc_name=doc_name_strategy,
        doc_path=doc_path_strategy,
    )
    def test_document_order_preserved(
        self,
        doc_name: str,
        doc_path: str,
    ):
        """Property: Document extraction preserves order of appearance.
        
        # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
        # **Validates: Requirements 5.2, 5.3**
        
        For any sequence of document markers, parsing SHALL return documents
        in the same order they appear in the response.
        """
        tracker = DocTracker()
        
        # Create multiple documents with numbered names to verify order
        doc_entries = [
            (f"{i}_{doc_name}", f"{doc_path}/file_{i}.md")
            for i in range(5)
        ]
        
        response = build_llm_response(doc_entries, [])
        result = tracker.parse_response(response)
        
        # Verify order is preserved
        assert len(result) == len(doc_entries), (
            f"Expected {len(doc_entries)} documents, got {len(result)}"
        )
        
        for i, (expected_name, expected_path) in enumerate(doc_entries):
            assert result[i]["name"] == expected_name.strip(), (
                f"Document {i} out of order: expected '{expected_name.strip()}', "
                f"got '{result[i]['name']}'"
            )

    @settings(max_examples=25)
    @given(
        text=surrounding_text_strategy,
    )
    def test_no_documents_returns_empty_list(
        self,
        text: str,
    ):
        """Property: Response with no document markers returns empty list.
        
        # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
        # **Validates: Requirements 5.2, 5.3**
        
        For any response text that does not contain valid document markers,
        parsing SHALL return an empty list.
        """
        tracker = DocTracker()
        
        # Parse response with no document markers
        result = tracker.parse_response(text)
        
        # Verify empty list is returned
        assert result == [], (
            f"Expected empty list for text without markers, got {result}"
        )

    @settings(max_examples=25)
    @given(
        doc_name=doc_name_strategy,
        doc_path=doc_path_strategy,
    )
    def test_result_contains_name_and_path_keys(
        self,
        doc_name: str,
        doc_path: str,
    ):
        """Property: Each extracted document has 'name' and 'path' keys.
        
        # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
        # **Validates: Requirements 5.2, 5.3**
        
        For any valid document marker, the extracted document dict SHALL
        contain exactly 'name' and 'path' keys.
        """
        tracker = DocTracker()
        
        response = build_doc_marker(doc_name, doc_path)
        result = tracker.parse_response(response)
        
        assert len(result) == 1, f"Expected 1 document, got {len(result)}"
        
        # Verify the dict has the expected keys
        assert "name" in result[0], "Result dict missing 'name' key"
        assert "path" in result[0], "Result dict missing 'path' key"
        assert set(result[0].keys()) == {"name", "path"}, (
            f"Expected keys {{'name', 'path'}}, got {set(result[0].keys())}"
        )

    @settings(max_examples=25)
    @given(
        doc_name=st.sampled_from([
            "PLAN.md", "DEV.md", "TEST.md", "DOCUMENT.md",
            "custom_output.md", "IP_Output_v2.0.md", "test_results.txt",
            "architecture.md", "README.md", "CHANGELOG.md",
        ]),
        doc_path=doc_path_strategy,
    )
    def test_common_document_names_extracted(
        self,
        doc_name: str,
        doc_path: str,
    ):
        """Property: Common document names (phase names, custom names) are extracted.
        
        # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
        # **Validates: Requirements 5.2, 5.3**
        
        For common document names including phase names (plan, dev, test, document)
        and custom names, parsing SHALL correctly extract the document.
        """
        tracker = DocTracker()
        
        response = build_doc_marker(doc_name, doc_path)
        result = tracker.parse_response(response)
        
        assert len(result) == 1, f"Expected 1 document, got {len(result)}"
        assert result[0]["name"] == doc_name, (
            f"Expected name '{doc_name}', got '{result[0]['name']}'"
        )

    @settings(max_examples=25)
    @given(
        doc_name=doc_name_strategy,
        path_with_spaces=st.builds(
            lambda segments: "/" + "/".join(segments),
            st.lists(
                st.text(
                    alphabet=st.characters(
                        whitelist_categories=("L", "N"),
                        whitelist_characters="_-. ",  # Include spaces
                    ),
                    min_size=1,
                    max_size=20,
                ).filter(lambda x: x.strip()),
                min_size=1,
                max_size=3,
            ),
        ),
    )
    def test_paths_with_spaces_extracted(
        self,
        doc_name: str,
        path_with_spaces: str,
    ):
        """Property: Paths containing spaces are correctly extracted.
        
        # Feature: bentwookie-web-ui-enhancements, Property 9: Document Tracker Parsing
        # **Validates: Requirements 5.2, 5.3**
        
        For any document path containing spaces, parsing SHALL extract
        the complete path including spaces.
        """
        tracker = DocTracker()
        
        response = build_doc_marker(doc_name, path_with_spaces)
        result = tracker.parse_response(response)
        
        assert len(result) == 1, f"Expected 1 document, got {len(result)}"
        assert result[0]["path"] == path_with_spaces.strip(), (
            f"Expected path '{path_with_spaces.strip()}', got '{result[0]['path']}'"
        )

