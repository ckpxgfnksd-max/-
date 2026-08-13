"""Regression tests for translation metadata front-matter parsing.

The maintenance script must not corrupt Pelican-style / opening-fence-only
articles: empty YAML documents drop titles (404s), and a body `---` treated as
a closer silently truncates intros.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "add_translation_metadata.py"
CONTENT_DIR = Path(__file__).resolve().parents[1] / "content"

spec = importlib.util.spec_from_file_location("add_translation_metadata", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def rewrite(content: str, translation_slug: str) -> str:
    front_matter, body = mod.get_front_matter(content)
    new_front_matter = mod.add_translation_field(front_matter, translation_slug)
    return f"---\n{new_front_matter}\n---{body}"


def pelican_title(content: str) -> str | None:
    """Title Pelican would see: first YAML/metadata Title line, not an empty doc."""
    lines = content.split("\n")
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                return None
            if line.startswith("Title:"):
                return line.split(":", 1)[1].strip()
            if line.strip() == "":
                break
        return None
    for line in lines:
        if line.strip() == "":
            break
        if line.startswith("Title:"):
            return line.split(":", 1)[1].strip()
    return None


class TestGetFrontMatter:
    def test_yaml_with_both_fences(self):
        content = "---\nTitle: Hello\nSlug: hello\n---\n\nBody\n"
        fm, body = mod.get_front_matter(content)
        assert "Title: Hello" in fm
        assert "---" not in fm
        assert "Body" in body

    def test_opening_fence_only_strips_opening_dash(self):
        content = "---\nTitle: Notes\nSlug: structured-notes\nSummary: x\n\n## Body\n"
        fm, body = mod.get_front_matter(content)
        assert not fm.startswith("---")
        assert "Title: Notes" in fm
        assert "Slug: structured-notes" in fm
        assert "## Body" in body

    def test_body_hr_is_not_a_closer(self):
        content = (
            "---\n"
            "Title: Year End\n"
            "Slug: 2024-year-end\n"
            "Summary: wrap\n"
            "\n"
            "Intro paragraph stays in the body.\n"
            "\n"
            "---\n"
            "\n"
            "## Section\n"
        )
        fm, body = mod.get_front_matter(content)
        assert "Intro paragraph" not in fm
        assert "Intro paragraph stays in the body." in body
        assert "---" in body
        assert "## Section" in body

    def test_pelican_style_no_fences(self):
        content = "Title: Plain\nSlug: plain\n\nHello\n"
        fm, body = mod.get_front_matter(content)
        assert fm.startswith("Title: Plain")
        assert "Hello" in body


class TestProcessFile:
    def test_opening_fence_only_does_not_create_empty_yaml(self, tmp_path: Path):
        src = tmp_path / "structured-notes.md"
        original_title = "你不需要懂金融"
        src.write_text(
            f"---\nTitle: {original_title}\nSlug: structured-notes\nSummary: x\n\n## Body\n",
            encoding="utf-8",
        )
        assert mod.process_file(src, "structured-notes-en")
        rewritten = src.read_text(encoding="utf-8")
        assert not rewritten.startswith("---\n---")
        assert pelican_title(rewritten) == original_title
        assert "Translation: structured-notes-en.html" in rewritten
        assert "## Body" in rewritten

    def test_body_hr_keeps_intro_in_body(self, tmp_path: Path):
        src = tmp_path / "2024-year-end.md"
        intro = "又到了年终盘点的时间。"
        src.write_text(
            "---\n"
            "Title: 年终盘点\n"
            "Slug: 2024-year-end\n"
            "Summary: wrap\n"
            "\n"
            f"{intro}\n"
            "\n"
            "---\n"
            "\n"
            "## 1. Section\n",
            encoding="utf-8",
        )
        assert mod.process_file(src, "2024-year-end-en")
        rewritten = src.read_text(encoding="utf-8")
        fm, body = mod.get_front_matter(rewritten)
        assert intro not in fm
        assert intro in body
        assert pelican_title(rewritten) == "年终盘点"

    def test_skips_existing_translation(self, tmp_path: Path):
        src = tmp_path / "foo-en.md"
        original = "---\nTitle: Foo\nSlug: foo-en\nTranslation: foo.html\n---\n\nBody\n"
        src.write_text(original, encoding="utf-8")
        assert mod.process_file(src, "foo") is False
        assert src.read_text(encoding="utf-8") == original


class TestAtRiskArticlesDryRun:
    AT_RISK = [
        "2024-year-end.md",
        "2025-year-end.md",
        "3d-print-laser-cutting.md",
        "GPT-API-usage-creation.md",
        "GPT-knowledge-management.md",
        "GPT-product-iteration.md",
        "GPT-prompt-engineering.md",
        "GPT-shortcut.md",
        "agentic-ai-202504.md",
        "agentic-ai-crisis.md",
        "agentic-ai-frameworks.md",
        "agentic-memory.md",
        "structured-notes.md",
    ]

    def test_dry_run_preserves_pelican_titles(self):
        preserved = []
        for name in self.AT_RISK:
            path = CONTENT_DIR / name
            assert path.exists(), f"missing at-risk article {name}"
            original = path.read_text(encoding="utf-8")
            original_title = pelican_title(original)
            assert original_title, f"{name} has no Pelican title before rewrite"
            rewritten = rewrite(original, path.stem + "-en")
            assert not rewritten.startswith("---\n---"), f"{name} became an empty YAML document"
            new_title = pelican_title(rewritten)
            assert new_title == original_title, f"{name}: {original_title!r} -> {new_title!r}"
            preserved.append(name)
        assert len(preserved) == 13
