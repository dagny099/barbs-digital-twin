"""
respond_ai() — UPDATED
======================
Three changes from the previous version:

CHANGE 1: Diagram serving is decoupled from walkthrough detection.
  - find_mentioned_project() fires on ANY project mention (broad)
  - select_project_for_walkthrough() fires on walkthrough intent (narrow)
  - A question like "how does Resume Explorer handle normalization?"
    now gets a diagram even though it's not a walkthrough request.

CHANGE 2: Walkthrough context is injected as a separate block, not
  appended to the user message. This means RAG retrieval embeds the
  user's ACTUAL question (not the enriched one), so you get relevant
  chunks from ChromaDB + the full walkthrough context in the LLM prompt.
  
CHANGE 3: Hybrid mode — walkthrough requests get BOTH the walkthrough
  context block AND the RAG-retrieved chunks. Previously the enriched
  message biased retrieval unpredictably; now each source contributes
  independently.
"""

# ── NEW IMPORTS (add to top of app.py) ──────────────────────────
# Replace the old import line:
#   from featured_projects import select_project_for_walkthrough, get_diagram_path, enrich_message_for_walkthrough
# With:
#   from featured_projects import (
#       select_project_for_walkthrough,
#       find_mentioned_project,
#       get_diagram_path,
#       build_walkthrough_context_block,
#   )


def respond_ai(message, history):
    # ── Step 1: Detect walkthrough intent (narrow) ──────────────
    walkthrough_project = select_project_for_walkthrough(message)
    walkthrough_block = None
    if walkthrough_project:
        walkthrough_block = build_walkthrough_context_block(walkthrough_project)
        print(f"WORKFLOW: Walkthrough → {walkthrough_project['title']}")

    # ── Step 2: Detect project mention for diagram (broad) ──────
    # Walkthrough project takes priority; otherwise check for any mention
    diagram_project = walkthrough_project or find_mentioned_project(message)
    diagram_path = get_diagram_path(diagram_project) if diagram_project else None
    if diagram_path and not walkthrough_project:
        print(f"WORKFLOW: Diagram only → {diagram_project['title']}")

    # ── Step 3: RAG retrieval on the ORIGINAL message ───────────
    # (Not the enriched one — this is the key change for hybrid mode)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[message]   # ← user's actual question, unmodified
    )
    query_embedded = response.data[0].embedding
    results = collection.query(
        query_embeddings=[query_embedded],
        n_results=N_CHUNKS_RETRIEVE
    )

    # ── Step 4: Build context from RAG chunks ───────────────────
    context_parts = []
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        src     = meta.get('source', '')
        section = meta.get('section', '')
        project = meta.get('project_name', '')
        if project and section:
            prefix = f"[{project} — {section}]"
        elif section:
            prefix = f"[{src} — {section}]"
        else:
            prefix = f"[{src}]"
        context_parts.append(f"{prefix}\n{doc}")
    context = "\n---\n".join(context_parts)

    print(f"Retrieved chunks:")
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        section_info = f" >> {meta.get('section', 'N/A')}" if meta.get('section') else ""
        print(f"<<Document {meta['source']}{section_info} -- Chunk {meta['chunk_index']}>>\n{doc}\n")

    # ── Step 5: Assemble system message (HYBRID) ────────────────
    # RAG context is always included.
    # Walkthrough context is added as a SEPARATE block when present,
    # so the LLM has both the curated walkthrough notes AND whatever
    # ChromaDB retrieved for the user's actual question.
    system_message_enhanced = system_message + "\n\nContext:\n" + context

    if walkthrough_block:
        system_message_enhanced += (
            "\n\n---\n"
            "[WALKTHROUGH MODE — The visitor asked for a project walkthrough. "
            "Use the walkthrough notes below as your primary source for this response. "
            "The retrieved context above may contain additional relevant details — "
            "incorporate them if they add value, but the walkthrough notes are your "
            "main guide for structure and content.]\n\n"
            + walkthrough_block
        )

    # ── Step 6: Clean history, build messages ───────────────────
    def _clean_content(msg):
        c = msg.get("content")
        if isinstance(c, dict):
            return {**msg, "content": c.get("text", "")}
        if isinstance(c, list):
            texts = [p.get("text", "") for p in c if p.get("type") == "text"]
            return {**msg, "content": " ".join(texts)}
        return msg

    clean_history = [_clean_content(m) for m in history]

    msgs = (
        [{"role": "system", "content": system_message_enhanced}]
        + clean_history
        + [{"role": "user", "content": message}]  # ← original message, not enriched
    )

    # ── Step 7: Tool-calling loop ───────────────────────────────
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=msgs,
        tools=tools
    )

    while response.choices[0].message.tool_calls:
        tool_result = handle_tool_call(response.choices[0].message.tool_calls)
        msgs.append(response.choices[0].message)
        msgs.extend(tool_result)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=msgs,
            tools=tools
        )

    # ── Step 8: Stream the response ─────────────────────────────
    stream = client.chat.completions.create(
        model=LLM_MODEL,
        messages=msgs,
        stream=True
    )
    collected = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            collected += delta
            yield collected

    print(f"<<LLM RESPONSE RAW>>\n{collected}\n")
    print(f"<<FILES:>>\n{diagram_path}\n")

    # ── Step 9: Append diagram if available ──────────────────────
    # Now fires for ANY project mention, not just walkthroughs
    if diagram_path:
        with open(diagram_path, "rb") as _img:
            _b64 = base64.b64encode(_img.read()).decode()
        _ext = diagram_path.rsplit(".", 1)[-1].lower()
        _file_url = f"/file={diagram_path}"
        _style = "max-width:45vw;display:block;margin:1.5rem auto 0;border-radius:8px;cursor:pointer"
        _img_tag = f'<img src="data:image/{_ext};base64,{_b64}" style="{_style}" alt="Project diagram"/>'
        _tag = f'<a href="{_file_url}" target="_blank" rel="noopener noreferrer">{_img_tag}</a>'
        collected += f"\n\n{_tag}"
        yield collected
