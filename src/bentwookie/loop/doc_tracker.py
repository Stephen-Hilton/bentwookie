"""Document tracker for extracting and saving document metadata from LLM responses."""

import re

from ..db.queries import create_request_doc


class DocTracker:
    """Tracks documents created during LLM request processing.
    
    Parses LLM responses to extract document metadata in the format:
        [DOC:name] path: /path/to/file
    
    And saves the extracted documents to the database.
    """
    
    # Pattern to match document output in LLM response
    # Format: [DOC:name] path: /path/to/file
    DOC_PATTERN = r'\[DOC:([^\]]+)\]\s*path:\s*([^\n]+)'
    
    def __init__(self):
        """Initialize the DocTracker."""
        self._pattern = re.compile(self.DOC_PATTERN)
    
    def parse_response(self, response: str) -> list[dict]:
        """Extract document metadata from LLM response.
        
        Parses the response text looking for document entries in the format:
            [DOC:name] path: /path/to/file
        
        Args:
            response: The LLM response text to parse.
            
        Returns:
            List of dicts with 'name' and 'path' keys for each document found.
            Returns an empty list if no documents are found or if response is empty.
        """
        if not response:
            return []
        
        docs = []
        matches = self._pattern.findall(response)
        
        for name, path in matches:
            # Strip whitespace from name and path
            doc_name = name.strip()
            doc_path = path.strip()
            
            # Only add if both name and path are non-empty
            if doc_name and doc_path:
                docs.append({
                    'name': doc_name,
                    'path': doc_path,
                })
        
        return docs
    
    def save_docs(self, reqid: int, docs: list[dict], phase: str) -> int:
        """Save extracted documents to database.
        
        Creates request_doc records for each document in the list.
        
        Args:
            reqid: The request ID to associate documents with.
            docs: List of document dicts with 'name' and 'path' keys.
            phase: The phase that created the documents (plan, dev, test, etc.).
            
        Returns:
            Number of documents saved.
        """
        if not docs:
            return 0
        
        saved_count = 0
        for doc in docs:
            doc_name = doc.get('name')
            doc_path = doc.get('path')
            
            # Skip if missing required fields
            if not doc_name or not doc_path:
                continue
            
            create_request_doc(
                reqid=reqid,
                doc_name=doc_name,
                doc_path=doc_path,
                doc_phase=phase,
            )
            saved_count += 1
        
        return saved_count
