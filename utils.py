"""
utils.py
========
Shared utilities for text chunking and section parsing across all
ingestion scripts (app.py, embed_resume.py, embed_biosketch.py,
embed_readmes.py, embed_mkdocs.py).

This module provides:
- Text chunking with paragraph-level boundaries
- Section parsing for TXT (delimiter-based) and Markdown (header-based)
- Standardized metadata construction for ChromaDB storage

Usage:
    from utils import chunk_prose, parse_sections_by_delimiter, build_metadata
"""

import re


# ═══════════════════════════════════════════════════════════════════
# CORE TEXT PROCESSING
# ═══════════════════════════════════════════════════════════════════

def parse_paragraphs(raw_text: str) -> list[str]:
    """
    Split text on blank lines, strip whitespace, drop empties.
    Handles both \\n\\n and \\r\\n\\r\\n line endings.

    Args:
        raw_text: Full text with paragraphs separated by blank lines.

    Returns:
        List of non-empty paragraph strings with internal newlines
        collapsed to spaces.

    Examples:
        >>> parse_paragraphs("Para 1\\n\\nPara 2\\n\\nPara 3")
        ['Para 1', 'Para 2', 'Para 3']

        >>> parse_paragraphs("")
        []

        >>> parse_paragraphs("Line 1\\nLine 2\\n\\nPara 2")
        ['Line 1 Line 2', 'Para 2']
    """
    paragraphs = raw_text.split("\n\n")
    # Collapse internal newlines within each paragraph into spaces
    cleaned = [" ".join(p.split()) for p in paragraphs]
    return [p for p in cleaned if p]


def chunk_prose(raw_text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """
    Chunk plain prose into overlapping segments, preserving paragraph boundaries.

    Atomic unit: paragraph (double-newline delimited)
    - Paragraphs are never split mid-sentence
    - Overlap re-includes trailing paragraphs from the previous chunk
    - No external dependencies

    Args:
        raw_text:   Full text (paragraphs separated by blank lines).
        chunk_size: Target size in chars. May slightly exceed to keep
                    paragraphs intact. Default: 500.
        overlap:    Target overlap in chars. Backtracks whole paragraphs.
                    Default: 50.

    Returns:
        List of dicts with structure:
        [
            {
                "text": "chunk text...",
                "para_start": 0,      # starting paragraph index
                "para_end": 2,        # ending paragraph index
                "char_count": 485     # actual character count
            },
            ...
        ]

    Examples:
        >>> chunks = chunk_prose("Para 1\\n\\nPara 2\\n\\nPara 3", chunk_size=20, overlap=5)
        >>> len(chunks) >= 1
        True
        >>> chunks[0]["text"]
        'Para 1\\n\\nPara 2'

    Edge Cases:
        - Empty text: returns []
        - Single paragraph: returns single chunk
        - Very large paragraph: included in single chunk (exceeds chunk_size)
    """
    paragraphs = parse_paragraphs(raw_text)

    if not paragraphs:
        return []

    chunks = []
    i = 0

    while i < len(paragraphs):
        # Accumulate paragraphs until we hit chunk_size
        chunk_paras, char_count, j = [], 0, i
        while j < len(paragraphs):
            para_len = len(paragraphs[j])

            # Always include at least one paragraph per chunk
            if char_count > 0 and (char_count + para_len) > chunk_size:
                break

            chunk_paras.append(paragraphs[j])
            char_count += para_len + 1
            j += 1

        # Store as a plain dict
        text = "\n\n".join(chunk_paras)
        chunks.append({
            "text": text,
            "para_start": i,
            "para_end": j - 1,
            "char_count": len(text),
        })

        # Stop if we've consumed everything
        if j >= len(paragraphs):
            break

        # Backtrack for overlap
        overlap_chars = 0
        backtrack = 0
        for k in range(j - 1, i, -1):
            if overlap_chars + len(paragraphs[k]) > overlap:
                break
            overlap_chars += len(paragraphs[k])
            backtrack += 1

        i = j - backtrack

    return chunks


# ═══════════════════════════════════════════════════════════════════
# SECTION PARSING - DELIMITER-BASED (for TXT files)
# ═══════════════════════════════════════════════════════════════════

def parse_sections_by_delimiter(
    raw_text: str,
    delimiter: str = "======",
    preserve_section_names: bool = True
) -> list[dict]:
    """
    Parse document into sections using a consistent text delimiter.

    Designed for the resume TXT format where sections are structured as:
        SECTION NAME
        ======
        content...

        NEXT SECTION
        ======
        content...

    Args:
        raw_text: Full document text.
        delimiter: String that marks section boundaries. Default: "======".
        preserve_section_names: If True, include section title in the
                                returned text; if False, title is only
                                in metadata. Default: True.

    Returns:
        List of dicts with structure:
        [
            {
                "section_name": "Summary",
                "text": "section content...",
                "start_line": 9,  # line number where section starts
                "end_line": 12     # line number where section ends
            },
            ...
        ]

    Edge Cases:
        - No delimiter found: returns entire document as single section
          with section_name = "Full Document"
        - Empty sections (delimiter followed immediately by delimiter):
          skipped, not returned
        - Preamble before first delimiter: included as section_name = "Preamble"

    Examples:
        >>> text = "Summary\\n======\\nThis is a summary.\\n\\nDetails\\n======\\nMore info."
        >>> sections = parse_sections_by_delimiter(text)
        >>> len(sections)
        2
        >>> sections[0]["section_name"]
        'Summary'
        >>> "This is a summary" in sections[0]["text"]
        True
    """
    lines = raw_text.split('\n')
    sections = []
    current_section_name = None
    current_section_lines = []
    current_start_line = 0

    # Track if we found any delimiters
    found_delimiter = False

    for line_num, line in enumerate(lines):
        # Check if this line is a delimiter
        if line.strip() == delimiter.strip():
            found_delimiter = True

            # If we have accumulated lines, save the previous section
            if current_section_lines:
                section_text = '\n'.join(current_section_lines).strip()
                if section_text:  # Only add non-empty sections
                    sections.append({
                        "section_name": current_section_name or "Preamble",
                        "text": section_text,
                        "start_line": current_start_line,
                        "end_line": line_num - 1
                    })

            # The line BEFORE the delimiter is the section name
            # (look back in current_section_lines)
            if current_section_lines:
                # Last line accumulated is the section title
                potential_title = current_section_lines[-1].strip()
                if potential_title:
                    current_section_name = potential_title
                    # Remove the title line from content if not preserving
                    if not preserve_section_names:
                        current_section_lines = current_section_lines[:-1]
                else:
                    current_section_name = "Untitled Section"
                current_section_lines = []
            else:
                current_section_name = "Untitled Section"

            current_start_line = line_num + 1
            continue

        # Accumulate content lines
        current_section_lines.append(line)

    # Handle remaining content after last delimiter
    if current_section_lines:
        section_text = '\n'.join(current_section_lines).strip()
        if section_text:
            sections.append({
                "section_name": current_section_name or ("Preamble" if found_delimiter else "Full Document"),
                "text": section_text,
                "start_line": current_start_line,
                "end_line": len(lines) - 1
            })

    # If no delimiter found, treat entire document as one section
    if not found_delimiter:
        sections = [{
            "section_name": "Full Document",
            "text": raw_text.strip(),
            "start_line": 0,
            "end_line": len(lines) - 1
        }]

    return sections


# ═══════════════════════════════════════════════════════════════════
# SECTION PARSING - MARKDOWN HEADERS (for .md files)
# ═══════════════════════════════════════════════════════════════════

def parse_markdown_sections(
    raw_text: str,
    header_level: int = 2,
    include_nested: bool = False
) -> list[dict]:
    """
    Parse markdown document into sections based on header levels.

    Designed for biosketch format with ## H2 headers:
        # Document Title

        ## Personal Information
        Content here...

        ## Family
        More content...

        ### Subsection
        Nested content...

    Args:
        raw_text: Full markdown document text.
        header_level: Header level to split on (2 for ##, 3 for ###, etc.).
                      Default: 2.
        include_nested: If True, subsections are merged into parent section;
                        if False, subsections become their own sections with
                        hierarchical names. Default: False.

    Returns:
        List of dicts with structure:
        [
            {
                "section_name": "Personal Information",
                "text": "## Personal Information\\nContent including subsections...",
                "header_level": 2,
                "start_line": 10,
                "end_line": 45
            },
            ...
        ]

    Edge Cases:
        - No headers found: returns entire document as "Full Document"
        - Content before first header: included as "Preamble"
        - Empty sections: skipped

    Notes:
        - Preserves markdown formatting in section text
        - Section names are stripped of # markers and whitespace
        - Section text INCLUDES the header line for context

    Examples:
        >>> text = "# Title\\n\\n## Section 1\\nContent 1\\n\\n## Section 2\\nContent 2"
        >>> sections = parse_markdown_sections(text, header_level=2)
        >>> len(sections)
        2
        >>> sections[0]["section_name"]
        'Section 1'
        >>> "## Section 1" in sections[0]["text"]
        True
    """
    lines = raw_text.split('\n')
    sections = []

    # Regex pattern for markdown headers: ^#{level} Title
    header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')

    current_section_name = None
    current_section_lines = []
    current_header_level = None
    current_start_line = 0
    found_target_header = False

    for line_num, line in enumerate(lines):
        match = header_pattern.match(line)

        if match:
            hashes = match.group(1)
            title = match.group(2).strip()
            level = len(hashes)

            # Check if this is a target-level header
            if level == header_level:
                # Save previous section if it exists
                if current_section_lines:
                    section_text = '\n'.join(current_section_lines).strip()
                    if section_text:
                        sections.append({
                            "section_name": current_section_name or "Preamble",
                            "text": section_text,
                            "header_level": current_header_level or 0,
                            "start_line": current_start_line,
                            "end_line": line_num - 1
                        })

                # Start new section
                current_section_name = title
                current_header_level = level
                current_section_lines = [line]  # Include the header in the text
                current_start_line = line_num
                found_target_header = True
                continue

            elif include_nested and level > header_level and current_section_name:
                # This is a subsection - include it in current section
                current_section_lines.append(line)
                continue

            elif not include_nested and level > header_level and current_section_name:
                # Subsections become their own sections with hierarchical names
                # Save current section first
                if current_section_lines:
                    section_text = '\n'.join(current_section_lines).strip()
                    if section_text:
                        sections.append({
                            "section_name": current_section_name,
                            "text": section_text,
                            "header_level": current_header_level,
                            "start_line": current_start_line,
                            "end_line": line_num - 1
                        })

                # Start new subsection
                current_section_name = f"{current_section_name} > {title}"
                current_header_level = level
                current_section_lines = [line]
                current_start_line = line_num
                continue

        # Accumulate content
        if current_section_name:
            current_section_lines.append(line)
        else:
            # Content before first header (preamble)
            if not found_target_header:
                if not current_section_lines:
                    current_section_name = "Preamble"
                    current_start_line = line_num
                current_section_lines.append(line)

    # Handle remaining content
    if current_section_lines:
        section_text = '\n'.join(current_section_lines).strip()
        if section_text:
            sections.append({
                "section_name": current_section_name or "Full Document",
                "text": section_text,
                "header_level": current_header_level or 0,
                "start_line": current_start_line,
                "end_line": len(lines) - 1
            })

    # If no sections found, return entire document
    if not sections:
        sections = [{
            "section_name": "Full Document",
            "text": raw_text.strip(),
            "header_level": 0,
            "start_line": 0,
            "end_line": len(lines) - 1
        }]

    return sections


# ═══════════════════════════════════════════════════════════════════
# METADATA CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════

def build_metadata(
    source_type: str,
    identifier: str,
    section_name: str = None,
    chunk_index: int = 0,
    **extra_fields
) -> dict:
    """
    Build standardized metadata dict for ChromaDB storage.

    Ensures consistent metadata schema across all ingestion sources
    with support for optional section tracking and extensible fields.

    Args:
        source_type: Type of source (e.g., 'resume', 'biosketch', 'github-readme', 'mkdocs')
        identifier: Unique identifier (filename, repo name, site name, etc.)
        section_name: Optional section name (e.g., 'Education', 'Summary').
                      Use None for sources without section parsing. Default: None.
        chunk_index: Position of chunk within section (or document if no sections).
                     Resets to 0 for each new section. Default: 0.
        **extra_fields: Additional metadata fields (e.g., page_url, title, site)

    Returns:
        Metadata dict conforming to standard schema:
        {
            'source': 'source-type:identifier',
            'section': 'Section Name' or None,
            'chunk_index': 0,
            ...extra fields
        }

    Examples:
        >>> build_metadata('resume', '2026.txt', 'Education', 0)
        {'source': 'resume:2026.txt', 'section': 'Education', 'chunk_index': 0}

        >>> build_metadata('biosketch', 'barbara.md', 'Family', 2)
        {'source': 'biosketch:barbara.md', 'section': 'Family', 'chunk_index': 2}

        >>> build_metadata('github-readme', 'concept-cartographer', chunk_index=5)
        {'source': 'github-readme:concept-cartographer', 'section': None, 'chunk_index': 5}

        >>> build_metadata('mkdocs', 'beehive-tracker', 'User Guide', 0,
        ...                page_url='https://docs.example.com', site='beehive')
        {'source': 'mkdocs:beehive-tracker', 'section': 'User Guide', 'chunk_index': 0,
         'page_url': 'https://docs.example.com', 'site': 'beehive'}
    """
    metadata = {
        'source': f'{source_type}:{identifier}',
        'section': section_name,
        'chunk_index': chunk_index
    }
    metadata.update(extra_fields)
    return metadata


# ═══════════════════════════════════════════════════════════════════
# CHROMADB HELPERS
# ═══════════════════════════════════════════════════════════════════

def delete_chunks_by_source(collection, source_prefix: str) -> None:
    """
    Delete all chunks whose 'source' metadata field starts with source_prefix.

    Used by embed scripts to wipe an existing source before force re-embedding.

    Args:
        collection:    ChromaDB collection object
        source_prefix: Prefix to match (e.g. 'biosketch:', 'project-summary:')
    """
    try:
        all_data = collection.get(include=["metadatas"])
        matching_ids = [
            id_ for id_, meta in zip(all_data["ids"], all_data["metadatas"])
            if meta.get("source", "").startswith(source_prefix)
        ]
        if matching_ids:
            print(f"   🗑️  Deleting {len(matching_ids)} existing chunks from {source_prefix}...")
            collection.delete(ids=matching_ids)
            print(f"   ✅ Deleted successfully")
        else:
            print(f"   ℹ️  No existing chunks found for {source_prefix}")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not delete existing chunks: {e}")


def section_already_embedded(collection, source: str, section: str) -> bool:
    """
    Check if a specific (source, section) pair is already in the collection.

    Used by embed scripts for per-section idempotency checks.

    Args:
        collection: ChromaDB collection object
        source:     Full source string (e.g. 'biosketch:barbara-hidalgo-sotelo-biosketch.md')
        section:    Section name (e.g. 'Education')

    Returns:
        True if at least one chunk with this source+section exists, False otherwise.
    """
    try:
        results = collection.get(
            where={"$and": [{"source": source}, {"section": section}]}
        )
        return len(results["ids"]) > 0
    except Exception:
        return False
