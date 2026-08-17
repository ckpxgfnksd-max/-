#!/usr/bin/env python3
"""
Add Translation metadata to paired Chinese-English articles for hreflang SEO.

For each pair of articles (e.g., foo.md and foo-en.md):
- Add Translation: foo-en.html to foo.md
- Add Translation: foo.html to foo-en.md
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Optional

CONTENT_DIR = Path(__file__).parent.parent / "content"


def _split_at_blank(lines: list[str], start: int) -> tuple[str, str]:
    """Pelican-style: metadata is contiguous lines until the first blank."""
    fm_lines: list[str] = []
    body_start = start
    for i in range(start, len(lines)):
        if lines[i].strip() == "":
            body_start = i
            break
        fm_lines.append(lines[i])
    else:
        return "\n".join(fm_lines).strip(), ""
    body = "\n" + "\n".join(lines[body_start:])
    return "\n".join(fm_lines).strip(), body


def get_front_matter(content: str) -> tuple[str, str]:
    """Split content into front matter and body.

    Supports two formats:
    1. YAML-style with --- delimiters
    2. Pelican-style without delimiters (first blank line separates)

    A closing --- counts only before the first blank line. Opening-fence-only
    files (a leading --- and no closer before that blank line) are treated as
    Pelican-style after skipping the fence. Naive str.split("---") would
    otherwise keep the opening fence in metadata (rewritten into an empty YAML
    document) or treat a later markdown HR as the closer (silent intro loss).
    """
    lines = content.split("\n")

    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "":
                return _split_at_blank(lines, 1)
            if line.strip() == "---":
                front_matter = "\n".join(lines[1:i]).strip()
                rest = lines[i + 1 :]
                body = ("\n" + "\n".join(rest)) if rest else ""
                return front_matter, body
        return "\n".join(lines[1:]).strip(), ""

    if lines:
        return _split_at_blank(lines, 0)

    return "", content


def get_slug_from_front_matter(front_matter: str) -> str | None:
    """Extract Slug from front matter."""
    for line in front_matter.split("\n"):
        if line.startswith("Slug:"):
            return line.split(":", 1)[1].strip()
    return None


def add_translation_field(front_matter: str, translation_slug: str) -> str:
    """Add or update Translation field in front matter."""
    lines = front_matter.split("\n")
    new_lines = []
    translation_added = False
    
    for line in lines:
        new_lines.append(line)
        # Add Translation after Slug line if not already present
        if line.startswith("Slug:") and not any(l.startswith("Translation:") for l in lines):
            new_lines.append(f"Translation: {translation_slug}.html")
            translation_added = True
    
    return "\n".join(new_lines)


def process_file(filepath: Path, translation_slug: str) -> bool:
    """Process a single file to add Translation field."""
    content = filepath.read_text(encoding="utf-8")
    front_matter, body = get_front_matter(content)
    
    if not front_matter:
        print(f"  Skipping {filepath.name}: no front matter found")
        return False
    
    # Check if Translation already exists
    if "Translation:" in front_matter:
        print(f"  Skipping {filepath.name}: Translation already exists")
        return False
    
    new_front_matter = add_translation_field(front_matter, translation_slug)
    new_content = f"---\n{new_front_matter}\n---{body}"
    
    filepath.write_text(new_content, encoding="utf-8")
    return True


def find_paired_articles() -> list[tuple[Path, Path]]:
    """Find all paired Chinese-English articles."""
    pairs = []
    
    for en_file in CONTENT_DIR.glob("*-en.md"):
        base_name = en_file.stem[:-3]  # Remove -en suffix
        cn_file = CONTENT_DIR / f"{base_name}.md"
        
        if cn_file.exists():
            pairs.append((cn_file, en_file))
    
    return pairs


def main():
    pairs = find_paired_articles()
    print(f"Found {len(pairs)} paired articles\n")
    
    for cn_file, en_file in pairs:
        cn_slug = cn_file.stem
        en_slug = en_file.stem
        
        print(f"Processing: {cn_slug} <-> {en_slug}")
        
        # Add translation to Chinese article
        if process_file(cn_file, en_slug):
            print(f"  Added Translation to {cn_file.name}")
        
        # Add translation to English article
        if process_file(en_file, cn_slug):
            print(f"  Added Translation to {en_file.name}")
    
    print(f"\nDone! Processed {len(pairs)} pairs.")


if __name__ == "__main__":
    main()
