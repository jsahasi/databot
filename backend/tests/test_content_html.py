"""Tests for content agent HTML extraction and sanitisation functions.

Tests cover:
- _extract_html: fenced ```html blocks, fallback density detection, no-HTML passthrough
- _sanitize_html: dangerous tag/attribute stripping, safe HTML preservation

Run with:
    python -m pytest tests/test_content_html.py -v
"""

import pytest

from app.agents.content_agent import _extract_html, _sanitize_html


# ===========================================================================
# 1. _extract_html
# ===========================================================================


class TestExtractHtml:
    """Tests for HTML extraction from LLM text output."""

    def test_fenced_html_block_extracted(self):
        """A fenced ```html block should be extracted and the surrounding text returned cleaned."""
        text = (
            "Here is your blog post:\n"
            "```html\n"
            "<h1>Title</h1>\n"
            "<p>Body text</p>\n"
            "```\n"
            "Let me know if you need changes."
        )
        cleaned, html = _extract_html(text)
        assert html is not None
        assert "<h1>Title</h1>" in html
        assert "<p>Body text</p>" in html
        assert "```html" not in cleaned
        assert "Let me know" in cleaned

    def test_no_html_returns_original_text_and_none(self):
        """Plain text with no HTML should return (original, None)."""
        text = "Here are your top 5 events by attendance."
        cleaned, html = _extract_html(text)
        assert cleaned == text
        assert html is None

    def test_multiple_block_tags_triggers_density_detection(self):
        """3+ block-level HTML tags without a fence should trigger density fallback."""
        text = "<h1>Title</h1><p>Paragraph one</p><div>Section</div><p>Another</p>"
        cleaned, html = _extract_html(text)
        assert html is not None
        # In density fallback, html == text
        assert html == text

    def test_empty_string_returns_empty_and_none(self):
        """Empty string input should return ('', None)."""
        cleaned, html = _extract_html("")
        assert cleaned == ""
        assert html is None

    def test_few_inline_tags_not_detected_as_html(self):
        """One or two tags (below density threshold) should not be extracted."""
        text = "Use <b>bold</b> and <i>italic</i> for emphasis."
        cleaned, html = _extract_html(text)
        assert html is None
        assert cleaned == text


# ===========================================================================
# 2. _sanitize_html
# ===========================================================================


class TestSanitizeHtml:
    """Tests for HTML sanitisation (XSS prevention on agent output)."""

    def test_strips_script_tags_and_content(self):
        """<script> tags and their content must be completely removed."""
        html = '<p>Hello</p><script>alert("xss")</script><p>World</p>'
        result = _sanitize_html(html)
        assert "<script" not in result
        assert "alert" not in result
        assert "<p>Hello</p>" in result
        assert "<p>World</p>" in result

    def test_strips_iframe_tags(self):
        """<iframe> tags must be removed."""
        html = '<div>Content</div><iframe src="https://evil.com"></iframe>'
        result = _sanitize_html(html)
        assert "<iframe" not in result
        assert "<div>Content</div>" in result

    def test_strips_on_event_handlers(self):
        """on* event handler attributes (onclick, onerror, onload) must be removed."""
        html = '<img src="photo.jpg" onerror="alert(1)" onclick="steal()">'
        result = _sanitize_html(html)
        assert "onerror" not in result
        assert "onclick" not in result
        # The img tag itself should remain
        assert "<img" in result

    def test_strips_javascript_urls(self):
        """javascript: URLs in href/src must be neutralised to about:blank."""
        html = '<a href="javascript:alert(1)">Click</a>'
        result = _sanitize_html(html)
        assert "javascript:" not in result
        assert "about:blank" in result

    def test_preserves_safe_html(self):
        """Safe tags (p, h1, h2, div, span, img, a with https) must be preserved."""
        html = (
            '<h1>Title</h1>'
            '<h2>Subtitle</h2>'
            '<p>Paragraph</p>'
            '<div><span>Inline</span></div>'
            '<img src="https://example.com/img.jpg">'
            '<a href="https://example.com">Link</a>'
        )
        result = _sanitize_html(html)
        assert result == html

    def test_strips_form_tags(self):
        """<form> tags must be removed."""
        html = '<form action="/steal"><input type="text"></form>'
        result = _sanitize_html(html)
        assert "<form" not in result
        assert "<input" not in result

    def test_strips_object_and_embed_tags(self):
        """<object> and <embed> tags must be removed."""
        html = '<object data="evil.swf"></object><embed src="evil.swf">'
        result = _sanitize_html(html)
        assert "<object" not in result
        assert "<embed" not in result

    def test_strips_onload_handler(self):
        """onload event handler must be stripped."""
        html = '<body onload="init()"><p>Content</p></body>'
        result = _sanitize_html(html)
        assert "onload" not in result
        assert "<p>Content</p>" in result
