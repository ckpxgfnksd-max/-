"""Regression tests for scripts/add_translation_metadata.py front-matter parsing."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "add_translation_metadata.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("add_translation_metadata", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


atm = _load_script()


class TestGetFrontMatter:
    def test_closed_yaml_fence(self):
        content = "---\nTitle: Closed\nSlug: closed\n---\n\nBody with --- still here\n"
        fm, body = atm.get_front_matter(content)
        assert "Title: Closed" in fm
        assert "Slug: closed" in fm
        assert not fm.startswith("---")
        assert "Body with --- still here" in body

    def test_open_fence_without_closing(self):
        """Opening --- without closing must not keep --- inside metadata."""
        content = (
            "---\n"
            "Title: Open Fence\n"
            "Slug: open-fence\n"
            "Summary: hello\n"
            "\n"
            "## Heading\n"
            "\n"
            "Article body\n"
        )
        fm, body = atm.get_front_matter(content)
        assert fm.startswith("Title:")
        assert "---" not in fm.split("\n")[0]
        assert "Title: Open Fence" in fm
        assert "Slug: open-fence" in fm
        assert "## Heading" in body
        assert "Article body" in body

    def test_open_fence_with_dash_line_in_body_does_not_truncate(self):
        content = (
            "---\n"
            "Title: Truncation Trap\n"
            "Slug: truncation-trap\n"
            "Summary: hi\n"
            "\n"
            "Before separator\n"
            "---\n"
            "After separator must remain in body\n"
        )
        fm, body = atm.get_front_matter(content)
        assert "Title: Truncation Trap" in fm
        assert "Before separator" in body
        assert "After separator must remain in body" in body
        assert "Before separator" not in fm

    def test_pelican_style_without_fences(self):
        content = "Title: Plain\nSlug: plain\n\nBody text\n"
        fm, body = atm.get_front_matter(content)
        assert fm == "Title: Plain\nSlug: plain"
        assert "Body text" in body


class TestProcessFile:
    def test_open_fence_rewrite_keeps_pelican_title(self, tmp_path: Path):
        src = tmp_path / "open-fence.md"
        src.write_text(
            "---\n"
            "Title: Must Keep Title\n"
            "Date: 2025-04-20 11:00\n"
            "Category: Computing\n"
            "Tags: Chinese, AI\n"
            "Slug: open-fence\n"
            "Summary: summary text\n"
            "\n"
            "## Body\n"
            "\n"
            "Content remains\n",
            encoding="utf-8",
        )

        assert atm.process_file(src, "open-fence-en") is True
        rewritten = src.read_text(encoding="utf-8")

        # Must be a single non-empty YAML document, not an empty ---/--- pair.
        assert rewritten.startswith("---\nTitle: Must Keep Title\n")
        assert "\n---\nTitle:" not in rewritten
        assert "Translation: open-fence-en.html" in rewritten
        assert "## Body" in rewritten
        assert "Content remains" in rewritten

        pelican = pytest.importorskip("pelican")
        from pelican.readers import MarkdownReader
        from pelican.settings import DEFAULT_CONFIG

        settings = dict(DEFAULT_CONFIG)
        reader = MarkdownReader(settings)
        _, meta = reader.read(str(src))
        assert meta.get("title") == "Must Keep Title"
        assert meta.get("slug") == "open-fence"

    def test_skips_when_translation_exists(self, tmp_path: Path):
        src = tmp_path / "already.md"
        src.write_text(
            "---\nTitle: Done\nSlug: done\nTranslation: done-en.html\n---\n\nBody\n",
            encoding="utf-8",
        )
        before = src.read_text(encoding="utf-8")
        assert atm.process_file(src, "other") is False
        assert src.read_text(encoding="utf-8") == before
