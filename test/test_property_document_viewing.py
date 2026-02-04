"""Property-based tests for document viewing with markdown rendering.

Feature: bentwookie-web-ui-enhancements
Property 10: Document Viewing with Markdown Rendering

Validates: Requirements 6.4

For any valid document record pointing to an existing markdown file,
viewing the document SHALL display the file content rendered as HTML
with markdown formatting applied.
"""

from hypothesis import given, settings, strategies as st

from bentwookie.web.app import render_markdown


# Simple alphabet for generating clean text
SAFE_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class TestPropertyDocumentViewing:
    """Property 10: Document Viewing with Markdown Rendering.

    For any valid document record pointing to an existing markdown file,
    viewing the document SHALL display the file content rendered as HTML
    with markdown formatting applied.

    **Validates: Requirements 6.4**
    """

    @settings(max_examples=25)
    @given(st.text(min_size=0, max_size=500))
    def test_markdown_renders_to_html(self, content: str):
        """Any markdown content renders to HTML without errors."""
        result = render_markdown(content)
        # Result should be a string (possibly empty for whitespace-only input)
        assert isinstance(result, str)

    @settings(max_examples=25)
    @given(st.integers(1, 6), st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=50))
    def test_headings_render_to_h_tags(self, level: int, text: str):
        """Markdown headings render to appropriate h tags."""
        markdown = f"{'#' * level} {text}"
        result = render_markdown(markdown)
        assert f"<h{level}>" in result or f"<h{level} " in result

    @settings(max_examples=25)
    @given(st.text(alphabet=SAFE_ALPHABET, min_size=2, max_size=50))
    def test_bold_renders_to_strong(self, text: str):
        """Bold markdown renders to strong tags."""
        markdown = f"**{text}**"
        result = render_markdown(markdown)
        assert "<strong>" in result

    @settings(max_examples=25)
    @given(st.text(alphabet=SAFE_ALPHABET, min_size=2, max_size=50))
    def test_italic_renders_to_em(self, text: str):
        """Italic markdown renders to em tags."""
        markdown = f"*{text}*"
        result = render_markdown(markdown)
        assert "<em>" in result

    @settings(max_examples=25)
    @given(st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=30))
    def test_inline_code_renders_to_code(self, text: str):
        """Inline code markdown renders to code tags."""
        markdown = f"`{text}`"
        result = render_markdown(markdown)
        assert "<code>" in result

    @settings(max_examples=25)
    @given(st.lists(st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=30), min_size=1, max_size=5))
    def test_unordered_list_renders_to_ul(self, items: list[str]):
        """Unordered list markdown renders to ul/li tags."""
        markdown = "\n".join(f"- {item}" for item in items)
        result = render_markdown(markdown)
        assert "<ul>" in result
        assert "<li>" in result

    @settings(max_examples=25)
    @given(st.lists(st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=30), min_size=1, max_size=5))
    def test_ordered_list_renders_to_ol(self, items: list[str]):
        """Ordered list markdown renders to ol/li tags."""
        markdown = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
        result = render_markdown(markdown)
        assert "<ol>" in result
        assert "<li>" in result

    @settings(max_examples=25)
    @given(st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=50))
    def test_links_render_to_a_tags(self, text: str):
        """Link markdown renders to anchor tags."""
        markdown = f"[{text}](https://example.com)"
        result = render_markdown(markdown)
        assert "<a " in result
        assert 'href="https://example.com"' in result

    @settings(max_examples=25)
    @given(st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=200))
    def test_code_blocks_render_to_pre(self, code: str):
        """Fenced code blocks render to pre/code tags."""
        markdown = f"```\n{code}\n```"
        result = render_markdown(markdown)
        assert "<pre>" in result or "<code>" in result

    @settings(max_examples=25)
    @given(st.text(min_size=0, max_size=500))
    def test_empty_and_whitespace_handled(self, content: str):
        """Empty and whitespace-only content is handled gracefully."""
        result = render_markdown(content)
        assert isinstance(result, str)
        # Should not raise any exceptions


class TestPropertyDocumentViewingXSS:
    """Property 10 Extension: Document viewing sanitizes malicious content.

    **Validates: Requirements 6.4 (security aspect)**
    """

    @settings(max_examples=25)
    @given(st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=100))
    def test_script_tags_removed(self, payload: str):
        """Script tags in markdown are removed."""
        markdown = f"<script>{payload}</script>"
        result = render_markdown(markdown)
        assert "<script>" not in result.lower()
        assert "</script>" not in result.lower()

    @settings(max_examples=25)
    @given(st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=50))
    def test_onclick_handlers_removed(self, payload: str):
        """onclick handlers in markdown are removed."""
        markdown = f'<div onclick="{payload}">test</div>'
        result = render_markdown(markdown)
        assert "onclick" not in result.lower()

    @settings(max_examples=25)
    @given(st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=50))
    def test_javascript_urls_removed(self, payload: str):
        """javascript: URLs in markdown are removed."""
        markdown = f'<a href="javascript:{payload}">click</a>'
        result = render_markdown(markdown)
        assert "javascript:" not in result.lower()
