"""
chroma_utils.py
===============
ChromaDB retrieval for the Digital Twin, structured as a drop-in
alternative to query_neo4j_rag() in neo4j_utils.py.

Both functions return the same dict shape:
    {"context": str, "sources": list[str], "scores": list[float]}

so respond_ai() can call either without any other changes.
"""


EMBED_MODEL = "text-embedding-3-small"


def _sensitivity_where(visitor_tier: str) -> dict | None:
    """Build a ChromaDB `where` filter for the given audience tier."""
    if visitor_tier == "inner_circle":
        return None
    elif visitor_tier == "personal":
        return {"sensitivity": {"$in": ["public", "personal"]}}
    else:
        return {"sensitivity": {"$eq": "public"}}


def query_chroma_rag(collection, oai_client, user_query: str,
                     visitor_tier: str = "public", k: int = 5) -> dict:
    """Vector-only retrieval via ChromaDB.

    Returns the same dict shape as query_neo4j_rag() so callers need no
    conditional logic beyond the initial backend dispatch.

    Args:
        collection:   chromadb Collection object (already open)
        oai_client:   openai.OpenAI client (used for embeddings)
        user_query:   raw user message
        visitor_tier: "public" | "personal" | "inner_circle"
        k:            number of chunks to retrieve

    Returns:
        {"context": str, "sources": list[str], "scores": list[float]}
    """
    # Embed the query
    emb = oai_client.embeddings.create(
        model=EMBED_MODEL,
        input=[user_query],
    ).data[0].embedding

    # Build query kwargs
    query_kwargs: dict = {
        "query_embeddings": [emb],
        "n_results": k,
        "include": ["documents", "metadatas", "distances"],
    }
    where = _sensitivity_where(visitor_tier)
    if where:
        query_kwargs["where"] = where

    raw = collection.query(**query_kwargs)

    docs      = raw.get("documents",  [[]])[0] or []
    metas     = raw.get("metadatas",  [[]])[0] or []
    distances = raw.get("distances",  [[]])[0] or []

    # Convert L2 distances → cosine-similarity-ish [0, 1] scores.
    # Formula: sim = 1 - (dist² / 2), clamped to [0, 1].
    # Matches the existing _compute_similarity_stats() convention in app.py.
    scores = [max(0.0, min(1.0, 1.0 - (d * d / 2.0))) for d in distances]

    # Build context string and source labels
    context_parts: list[str] = []
    sources: list[str] = []
    for doc, meta in zip(docs, metas):
        src     = meta.get("source", "")
        section = meta.get("section", "")
        project = meta.get("project_name", "")

        if project and section:
            prefix = f"[{project} — {section}]"
            label  = f"{project} — {section}"
        elif section:
            prefix = f"[{src} — {section}]"
            label  = f"{src} — {section}"
        else:
            prefix = f"[{src}]"
            label  = src

        context_parts.append(f"{prefix}\n{doc}")
        sources.append(label)

    context = "\n---\n".join(context_parts)
    return {"context": context, "sources": sources, "scores": scores}
