"""Property-based tests for markdown rendering element support.

# Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
# **Validates: Requirements 2.1, 2.2**

Property Definition:
*For any* valid markdown string containing headings, bold, italic, lists, code blocks,
or links, the Markdown_Renderer SHALL produce HTML output containing the corresponding
HTML elements (`<h1>`-`<h6>`, `<strong>`, `<em>`, `<ul>`/`<ol>`/`<li>`, `<pre>`/`<code>`, `<a>`).
"""

from hypothesis import given, settings, strategies as st

from bentwookie.web.app import render_markdown


# Strategies for generating test data

# Strategy for plain text content (no special markdown characters)
plain_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Z"),  # Letters, numbers, spaces
        blacklist_characters="#*_`[]()><\n\r",  # Avoid markdown special chars
    ),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())  # Must have non-whitespace content


# Strategy for heading levels (1-6)
heading_level_strategy = st.integers(min_value=1, max_value=6)


# Strategy for URL-safe text (for links)
url_safe_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="-_.",
    ),
    min_size=1,
    max_size=20,
).filter(lambda x: x.strip())


# Strategy for simple URLs
url_strategy = st.builds(
    lambda domain, path: f"https://{domain}.com/{path}",
    url_safe_text_strategy,
    url_safe_text_strategy,
)


# Strategy for list items (1-5 items)
list_items_strategy = st.lists(
    plain_text_strategy,
    min_size=1,
    max_size=5,
)


class TestMarkdownElementSupportProperty:
    """Property-based tests for render_markdown() element support.
    
    # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
    # **Validates: Requirements 2.1, 2.2**
    """

    @settings(max_examples=25)
    @given(
        level=heading_level_strategy,
        text=plain_text_strategy,
    )
    def test_headings_render_to_h_tags(
        self,
        level: int,
        text: str,
    ):
        """Property: Markdown headings render to corresponding HTML h1-h6 tags.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any heading level (1-6) and text content, the markdown heading
        SHALL render to the corresponding HTML heading element.
        """
        # Build markdown heading
        markdown = "#" * level + " " + text
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify the correct heading tag is present
        expected_tag = f"<h{level}>"
        expected_close_tag = f"</h{level}>"
        
        assert expected_tag in result, (
            f"Expected {expected_tag} in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert expected_close_tag in result, (
            f"Expected {expected_close_tag} in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        text=plain_text_strategy,
    )
    def test_bold_renders_to_strong_tag(
        self,
        text: str,
    ):
        """Property: Markdown bold text renders to HTML strong tag.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any text wrapped in ** markers, the markdown bold
        SHALL render to the HTML <strong> element.
        """
        # Strip whitespace - markdown requires markers to be adjacent to text
        text = text.strip()
        if not text:
            return  # Skip empty text after stripping
        
        # Build markdown bold text
        markdown = f"**{text}**"
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify strong tag is present
        assert "<strong>" in result, (
            f"Expected <strong> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</strong>" in result, (
            f"Expected </strong> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        text=plain_text_strategy,
    )
    def test_italic_renders_to_em_tag(
        self,
        text: str,
    ):
        """Property: Markdown italic text renders to HTML em tag.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any text wrapped in * markers, the markdown italic
        SHALL render to the HTML <em> element.
        """
        # Strip whitespace - markdown requires markers to be adjacent to text
        text = text.strip()
        if not text:
            return  # Skip empty text after stripping
        
        # Build markdown italic text
        markdown = f"*{text}*"
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify em tag is present
        assert "<em>" in result, (
            f"Expected <em> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</em>" in result, (
            f"Expected </em> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        items=list_items_strategy,
    )
    def test_unordered_list_renders_to_ul_li_tags(
        self,
        items: list[str],
    ):
        """Property: Markdown unordered lists render to HTML ul/li tags.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any list of items with - prefix, the markdown unordered list
        SHALL render to HTML <ul> and <li> elements.
        """
        # Build markdown unordered list
        markdown = "\n".join(f"- {item}" for item in items)
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify ul and li tags are present
        assert "<ul>" in result, (
            f"Expected <ul> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</ul>" in result, (
            f"Expected </ul> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "<li>" in result, (
            f"Expected <li> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</li>" in result, (
            f"Expected </li> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        items=list_items_strategy,
    )
    def test_ordered_list_renders_to_ol_li_tags(
        self,
        items: list[str],
    ):
        """Property: Markdown ordered lists render to HTML ol/li tags.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any list of items with numbered prefix, the markdown ordered list
        SHALL render to HTML <ol> and <li> elements.
        """
        # Build markdown ordered list
        markdown = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify ol and li tags are present
        assert "<ol>" in result, (
            f"Expected <ol> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</ol>" in result, (
            f"Expected </ol> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "<li>" in result, (
            f"Expected <li> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</li>" in result, (
            f"Expected </li> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        text=plain_text_strategy,
    )
    def test_inline_code_renders_to_code_tag(
        self,
        text: str,
    ):
        """Property: Markdown inline code renders to HTML code tag.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any text wrapped in backticks, the markdown inline code
        SHALL render to the HTML <code> element.
        """
        # Build markdown inline code
        markdown = f"`{text}`"
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify code tag is present
        assert "<code>" in result, (
            f"Expected <code> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</code>" in result, (
            f"Expected </code> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        text=plain_text_strategy,
    )
    def test_fenced_code_block_renders_to_pre_code_tags(
        self,
        text: str,
    ):
        """Property: Markdown fenced code blocks render to HTML pre/code tags.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any text in a fenced code block (```), the markdown code block
        SHALL render to HTML <pre> and <code> elements.
        """
        # Build markdown fenced code block
        markdown = f"```\n{text}\n```"
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify pre and code tags are present
        assert "<pre>" in result, (
            f"Expected <pre> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</pre>" in result, (
            f"Expected </pre> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "<code>" in result, (
            f"Expected <code> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</code>" in result, (
            f"Expected </code> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        link_text=plain_text_strategy,
        url=url_strategy,
    )
    def test_links_render_to_a_tag(
        self,
        link_text: str,
        url: str,
    ):
        """Property: Markdown links render to HTML anchor tag.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any link text and URL, the markdown link [text](url)
        SHALL render to the HTML <a> element with href attribute.
        """
        # Build markdown link
        markdown = f"[{link_text}]({url})"
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify anchor tag is present with href
        assert "<a " in result or "<a>" in result, (
            f"Expected <a> tag in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "</a>" in result, (
            f"Expected </a> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert 'href="' in result, (
            f"Expected href attribute in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        level=heading_level_strategy,
        heading_text=plain_text_strategy,
        bold_text=plain_text_strategy,
        italic_text=plain_text_strategy,
    )
    def test_combined_elements_all_render(
        self,
        level: int,
        heading_text: str,
        bold_text: str,
        italic_text: str,
    ):
        """Property: Multiple markdown elements in one document all render correctly.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any markdown document containing multiple element types,
        ALL elements SHALL render to their corresponding HTML elements.
        """
        # Strip whitespace - markdown requires markers to be adjacent to text
        bold_text = bold_text.strip()
        italic_text = italic_text.strip()
        if not bold_text or not italic_text:
            return  # Skip if text becomes empty after stripping
        
        # Build markdown with multiple elements
        markdown = f"""{"#" * level} {heading_text}

**{bold_text}**

*{italic_text}*
"""
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify all element types are present
        assert f"<h{level}>" in result, (
            f"Expected <h{level}> in combined output\n"
            f"Markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "<strong>" in result, (
            f"Expected <strong> in combined output\n"
            f"Markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "<em>" in result, (
            f"Expected <em> in combined output\n"
            f"Markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        text=plain_text_strategy,
    )
    def test_empty_input_returns_empty_string(
        self,
        text: str,  # Not used, but keeps hypothesis happy
    ):
        """Property: Empty or None input returns empty string.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For empty string or None input, render_markdown SHALL return
        an empty string without error.
        """
        # Test empty string
        result_empty = render_markdown("")
        assert result_empty == "", (
            f"Expected empty string for empty input, got: {result_empty!r}"
        )
        
        # Test None (if supported)
        result_none = render_markdown(None)
        assert result_none == "", (
            f"Expected empty string for None input, got: {result_none!r}"
        )

    @settings(max_examples=25)
    @given(
        text=plain_text_strategy,
        lang=st.sampled_from(["python", "javascript", "bash", "sql", ""]),
    )
    def test_fenced_code_with_language_renders(
        self,
        text: str,
        lang: str,
    ):
        """Property: Fenced code blocks with language specifier render correctly.
        
        # Feature: bentwookie-web-ui-enhancements, Property 2: Markdown Rendering Element Support
        # **Validates: Requirements 2.1, 2.2**
        
        For any fenced code block with a language specifier,
        the markdown SHALL render to HTML <pre> and <code> elements.
        """
        # Build markdown fenced code block with language
        markdown = f"```{lang}\n{text}\n```"
        
        # Render markdown
        result = render_markdown(markdown)
        
        # Verify pre and code tags are present
        assert "<pre>" in result, (
            f"Expected <pre> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
        assert "<code>" in result, (
            f"Expected <code> in output for markdown: {markdown!r}\n"
            f"Got: {result!r}"
        )
