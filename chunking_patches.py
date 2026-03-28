# Chunking improvement patches
# Apply these changes to your existing files.
# Run chunk_inspector.py --canonical before and after each change to compare.

# ══════════════════════════════════════════════════════════════════
# PATCH 1: embed_kb_doc.py
# Problem: CHUNK_SIZE=500 orphans trailing paragraphs from sections.
#          Section name is only in metadata, not in chunk text itself.
# ══════════════════════════════════════════════════════════════════

# CHANGE THIS (line ~17-18):
# CHUNK_SIZE  = 500
# OVERLAP     = 50

# TO THIS:
CHUNK_SIZE  = 900
OVERLAP     = 120
MIN_CHUNK_CHARS = 150   # ← ADD THIS LINE

# ALSO ADD this helper after the import block and before process_kb_doc():
def merge_tiny_chunks(chunks: list[dict], min_chars: int = 150) -> list[dict]:
    """
    Merge any chunk shorter than min_chars into the next chunk.
    Prevents orphaned header-only or trailing fragments.
    """
    if not chunks:
        return chunks
    merged = []
    carry  = None
    for chunk in chunks:
        if carry is not None:
            # Merge carry into this chunk
            combined_text = carry["text"] + "\n\n" + chunk["text"]
            chunk = {**chunk, "text": combined_text, "char_count": len(combined_text)}
            carry = None
        if len(chunk["text"]) < min_chars:
            carry = chunk   # hold it, merge forward
        else:
            merged.append(chunk)
    if carry is not None:
        # Last chunk was tiny — merge backward
        if merged:
            combined_text = merged[-1]["text"] + "\n\n" + carry["text"]
            merged[-1] = {**merged[-1], "text": combined_text,
                          "char_count": len(combined_text)}
        else:
            merged.append(carry)   # only chunk, keep it regardless of size
    return merged


# AND UPDATE the chunk call inside process_kb_doc() (line ~95):
# CHANGE THIS:
#   chunk_results = chunk_prose(section_text, chunk_size=CHUNK_SIZE, overlap=OVERLAP)

# TO THIS:
#   chunk_results = chunk_prose(section_text, chunk_size=CHUNK_SIZE, overlap=OVERLAP)
#   chunk_results = merge_tiny_chunks(chunk_results, min_chars=MIN_CHUNK_CHARS)

# ALSO: prepend section name to chunk text so retrieval context is self-contained.
# UPDATE the chunk loop (line ~100):
# CHANGE THIS:
#   all_chunks.append(chunk_data["text"])

# TO THIS:
#   prefixed_text = f"[{section_name}]\n{chunk_data['text']}"
#   all_chunks.append(prefixed_text)

# ══════════════════════════════════════════════════════════════════
# PATCH 2: embed_project_summaries.py
# Problem: No 'featured' flag in metadata — twin can't prioritize.
#          (Chunking is already correct — atomic sections, no change needed.)
# ══════════════════════════════════════════════════════════════════

# ADD this constant near the top of the file (after TECH_KEYWORDS):
FEATURED_PROJECTS = {
    "resume-explorer",       # ← use the slug from your PDF filenames
    "concept-cartographer",  # ← add/remove slugs to match your featured set
    # "digital-twin",
    # "add-your-third-here",
}
# Note: slugs come from slug_from_filename() — run --dry-run to see yours.

# UPDATE the metadata build call inside process_pdf() (line ~353):
# CHANGE THIS:
#   metadata = build_metadata(
#       source_type="project-summary",
#       identifier=slug,
#       section_name=section_label,
#       chunk_index=chunk_index,
#       project_name=project_name,
#       tech_stack=tech_stack,
#   )

# TO THIS:
#   metadata = build_metadata(
#       source_type="project-summary",
#       identifier=slug,
#       section_name=section_label,
#       chunk_index=chunk_index,
#       project_name=project_name,
#       tech_stack=tech_stack,
#   )
#   metadata["featured"] = slug in FEATURED_PROJECTS
#   metadata["char_count"] = len(text)


# ══════════════════════════════════════════════════════════════════
# PATCH 3: embed_jekyll.py
# Problem: CHUNK_SIZE=500 same as kb_doc. Short pages get over-split.
#          No whole-doc guard for short pages.
# ══════════════════════════════════════════════════════════════════

# CHANGE THIS (line ~63-64):
# CHUNK_SIZE   = 500
# OVERLAP      = 50

# TO THIS:
CHUNK_SIZE   = 900
OVERLAP      = 120
WHOLE_DOC_THRESHOLD = 1200   # ← ADD: pages shorter than this → single chunk

# UPDATE the chunk call inside process_site() (line ~246):
# CHANGE THIS:
#   chunk_results = chunk_prose(page["text"], chunk_size=CHUNK_SIZE, overlap=OVERLAP)

# TO THIS:
#   if len(page["text"]) <= WHOLE_DOC_THRESHOLD:
#       # Short page — embed as single unit, no splitting
#       chunk_results = [{"text": page["text"], "para_start": 0,
#                         "para_end": -1, "char_count": len(page["text"])}]
#   else:
#       chunk_results = chunk_prose(page["text"], chunk_size=CHUNK_SIZE, overlap=OVERLAP)


# ══════════════════════════════════════════════════════════════════
# PATCH 4: app.py (ZERO re-ingest — do this first)
# Problem: Retrieved chunks have no source context in their text.
#          LLM sees "The system uses Flask" with no section label.
# ══════════════════════════════════════════════════════════════════

# FIND this block in respond_ai() (line ~588):
#   context = "\n---------\n".join(results['documents'][0])

# REPLACE WITH:
#   context_parts = []
#   for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
#       src     = meta.get('source', '')
#       section = meta.get('section', '')
#       project = meta.get('project_name', '')
#       # Build a prefix that gives the LLM orientation
#       if project and section:
#           prefix = f"[{project} — {section}]"
#       elif section:
#           prefix = f"[{src} — {section}]"
#       else:
#           prefix = f"[{src}]"
#       context_parts.append(f"{prefix}\n{doc}")
#   context = "\n---\n".join(context_parts)

# ALSO: bump N_CHUNKS_RETRIEVE (line ~34):
# CHANGE: N_CHUNKS_RETRIEVE = 8
# TO:     N_CHUNKS_RETRIEVE = 10
# Rationale: featured project chunks will now compete for slots with
# kb- sources. More slots = better coverage without hurting precision.
