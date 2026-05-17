"""
replay_retrieval.py
───────────────────────────────────────────────────────────────────────────────
Neo4j retrieval debugger for the Digital Twin.

Shows EXACTLY what context the LLM received for any query — the retrieved
chunks, their composite scores, and the text injected into the system prompt.
Optionally compares Neo4j results against ChromaDB's raw vector ranking so
you can spot when graph-signal reranking promotes or demotes the wrong chunks.

USAGE
    python replay_retrieval.py --query "How did you get into beekeeping?"
    python replay_retrieval.py --query "..." --compare          # Neo4j vs ChromaDB
    python replay_retrieval.py --query "..." --tier personal    # unlock personal chunks
    python replay_retrieval.py --query "..." --k 8 --full       # 8 results, full text
    python replay_retrieval.py --replay "How did you get into beekeeping?"
        # Finds matching entry in query_log.jsonl and uses its tier/k settings

COMPLEMENT TO chunk_inspector.py
    chunk_inspector.py  →  audits ChromaDB chunk quality, simulates ChromaDB retrieval
    replay_retrieval.py →  debugs Neo4j GraphRAG retrieval, compares Neo4j vs ChromaDB
"""

import os
import sys
import json
import argparse
import textwrap
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# ── CONFIG ───────────────────────────────────────────────────────────────────
CHROMA_PATH    = ".chroma_db_DT"
COLLECTION     = "barb-twin"
QUERY_LOG      = "query_log.jsonl"
DEFAULT_K      = int(os.getenv("N_CHUNKS_RETRIEVE", 5))
PREVIEW_CHARS  = 400   # default chars to show per chunk (--full overrides)
MIN_CHUNK_WARN = 150   # flag suspiciously short chunks
# ─────────────────────────────────────────────────────────────────────────────

TIER_HIERARCHY = {
    "public":       ["public"],
    "personal":     ["public", "personal"],
    "inner_circle": ["public", "personal", "inner_circle"],
}


def get_embedding(query: str) -> list[float]:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return (
        client.embeddings
        .create(model="text-embedding-3-small", input=query)
        .data[0].embedding
    )


# ── NEO4J RETRIEVAL ──────────────────────────────────────────────────────────

def run_neo4j(query: str, tier: str, k: int, fetch_k_mult: int = 4) -> list[dict]:
    """Run the hybrid Neo4j query and return ranked results.

    Uses the same scoring weights as neo4j_utils.py (imported as constants)
    but with an extended RETURN clause to surface the bonus breakdown for debugging.
    """
    from neo4j_utils import get_driver, SCORE_W_VECTOR, SCORE_W_PROJECT, SCORE_W_ENTITY, SCORE_W_LENGTH

    embedding = get_embedding(query)
    allowed   = TIER_HIERARCHY.get(tier, ["public"])
    fetch_k   = k * fetch_k_mult

    # Extended version of _HYBRID_CYPHER — same weights, extra debug fields returned.
    # Weights come from neo4j_utils constants so they stay in sync automatically.
    cypher = f"""
    CALL db.index.vector.queryNodes('section_embeddings', $fetch_k, $query_embedding)
    YIELD node AS section, score AS vector_score

    WHERE section.sensitivity IN $allowed_tiers

    OPTIONAL MATCH (section)<-[:DESCRIBED_IN]-(p:Project)
    OPTIONAL MATCH (section)-[:MENTIONS]->(entity)

    WITH section, vector_score,
         count(DISTINCT p) AS projects_described,
         count(DISTINCT entity) AS entities_mentioned

    WITH section,
         (vector_score * {SCORE_W_VECTOR} +
          CASE WHEN projects_described > 0 THEN {SCORE_W_PROJECT} ELSE 0 END +
          toFloat(CASE WHEN entities_mentioned > 5 THEN 5 ELSE entities_mentioned END) / 5 * {SCORE_W_ENTITY} +
          (CASE WHEN section.char_count > 2000 THEN {SCORE_W_LENGTH} ELSE 0 END)) AS final_score,
         vector_score,
         projects_described,
         entities_mentioned

    ORDER BY final_score DESC
    LIMIT $k

    MATCH (doc:Document)-[:HAS_SECTION]->(section)
    OPTIONAL MATCH (section)<-[:DESCRIBED_IN]-(project:Project)

    RETURN section.full_text  AS text,
           section.name       AS section_name,
           section.sensitivity AS sensitivity,
           section.char_count AS char_count,
           doc.title          AS source,
           final_score,
           vector_score,
           projects_described,
           entities_mentioned,
           collect(DISTINCT project.title) AS related_projects
    """

    driver = get_driver()
    with driver.session() as session:
        records = session.run(cypher, {
            "query_embedding": embedding,
            "k": k,
            "fetch_k": fetch_k,
            "allowed_tiers": allowed,
        }).data()

    return records


# ── CHROMADB RETRIEVAL ───────────────────────────────────────────────────────

def run_chromadb(query: str, tier: str, k: int) -> list[dict]:
    """Run ChromaDB vector retrieval and return results in a comparable format."""
    import chromadb

    embedding = get_embedding(query)
    allowed   = TIER_HIERARCHY.get(tier, ["public"])

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    coll   = client.get_or_create_collection(name=COLLECTION)

    # Build sensitivity filter
    if len(allowed) == 1:
        where = {"sensitivity": {"$eq": allowed[0]}}
    else:
        where = {"sensitivity": {"$in": allowed}}

    results = coll.query(
        query_embeddings=[embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
        where=where,
    )

    rows = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # L2 distance → cosine-like similarity: sim = 1 - dist²/2  (clamp to [0,1])
        sim = max(0.0, min(1.0, 1.0 - (dist * dist / 2.0)))
        rows.append({
            "source":       meta.get("source", "?"),
            "section_name": meta.get("section", ""),
            "sensitivity":  meta.get("sensitivity", "?"),
            "text":         doc,
            "vector_score": round(sim, 4),
            "final_score":  round(sim, 4),   # no graph boosting in ChromaDB
            "dist":         round(dist, 4),
        })
    return rows


# ── DISPLAY HELPERS ──────────────────────────────────────────────────────────

def _label(rec: dict) -> str:
    src = rec.get("source") or "?"
    sec = rec.get("section_name") or ""
    return f"{src} — {sec}" if sec else src


def _score_bar(score: float, width: int = 20) -> str:
    filled = int(score * width)
    return "█" * filled + "░" * (width - filled)


def print_neo4j_results(records: list[dict], preview: int, tier: str, k: int, fetch_k_mult: int):
    from neo4j_utils import SCORE_W_VECTOR, SCORE_W_PROJECT, SCORE_W_ENTITY, SCORE_W_LENGTH
    W = 72
    print(f"\n{'═'*W}")
    print(f"  NEO4J GraphRAG  —  tier={tier}  k={k}  fetch_k={k*fetch_k_mult}")
    print(f"  Weights: vec={SCORE_W_VECTOR}  proj={SCORE_W_PROJECT}  entity={SCORE_W_ENTITY}  length={SCORE_W_LENGTH}")
    print(f"{'─'*W}")
    for i, rec in enumerate(records):
        label     = _label(rec)
        final     = rec.get("final_score", 0)
        vec       = rec.get("vector_score", 0)
        proj_desc = rec.get("projects_described", 0)
        ent_ment  = rec.get("entities_mentioned", 0)
        char_c    = rec.get("char_count") or len(rec.get("text") or "")
        text      = rec.get("text") or ""
        tiny_flag = "  ⚠️  SHORT" if char_c < MIN_CHUNK_WARN else ""

        proj_bonus   = SCORE_W_PROJECT if proj_desc > 0 else 0.0
        ent_bonus    = min(ent_ment, 5) / 5 * SCORE_W_ENTITY
        length_bonus = SCORE_W_LENGTH if char_c > 2000 else 0.0

        print(f"\n  #{i+1}  {_score_bar(final)}  final={final:.3f}  vec={vec:.3f}")
        print(f"       +proj={proj_bonus:.2f}  +entity={ent_bonus:.2f}  +length={length_bonus:.2f}{tiny_flag}")
        print(f"       {label}")
        print(f"       sensitivity={rec.get('sensitivity','?')}  "
              f"projects_linked={proj_desc}  entities={ent_ment}  chars={char_c}")
        excerpt = text[:preview].replace("\n", " ")
        if len(text) > preview:
            excerpt += "…"
        for line in textwrap.wrap(excerpt, width=W - 7):
            print(f"       {line}")
    print(f"\n{'═'*W}\n")


def print_chromadb_results(rows: list[dict], preview: int, tier: str, k: int):
    W = 72
    print(f"\n{'═'*W}")
    print(f"  CHROMADB vector-only  —  tier={tier}  k={k}  (no graph boosting)")
    print(f"{'─'*W}")
    for i, rec in enumerate(rows):
        label = _label(rec)
        sim   = rec.get("vector_score", 0)
        dist  = rec.get("dist", 0)
        text  = rec.get("text") or ""
        char_c = len(text)
        tiny_flag = "  ⚠️  SHORT" if char_c < MIN_CHUNK_WARN else ""

        print(f"\n  #{i+1}  {_score_bar(sim)}  sim={sim:.3f}  L2_dist={dist:.3f}{tiny_flag}")
        print(f"       {label}")
        print(f"       sensitivity={rec.get('sensitivity','?')}  chars={char_c}")
        excerpt = text[:preview].replace("\n", " ")
        if len(text) > preview:
            excerpt += "…"
        for line in textwrap.wrap(excerpt, width=W - 7):
            print(f"       {line}")
    print(f"\n{'═'*W}\n")


def print_comparison(neo4j_recs: list[dict], chroma_rows: list[dict]):
    """Side-by-side ranking table so drift is immediately visible."""
    W = 72
    print(f"\n{'═'*W}")
    print(f"  RANKING COMPARISON  (Neo4j composite  vs  ChromaDB vector-only)")
    print(f"{'─'*W}")

    neo4j_labels  = [_label(r) for r in neo4j_recs]
    chroma_labels = [_label(r) for r in chroma_rows]
    all_labels    = list(dict.fromkeys(neo4j_labels + chroma_labels))

    print(f"  {'Label':<44}  {'Neo4j':^6}  {'Chroma':^6}  {'Drift'}")
    print(f"  {'─'*44}  {'─'*6}  {'─'*6}  {'─'*5}")

    for lbl in all_labels:
        n_rank = neo4j_labels.index(lbl)  + 1 if lbl in neo4j_labels  else None
        c_rank = chroma_labels.index(lbl) + 1 if lbl in chroma_labels else None

        n_str  = f"#{n_rank}" if n_rank else " —  "
        c_str  = f"#{c_rank}" if c_rank else " —  "

        if n_rank and c_rank:
            drift = c_rank - n_rank   # positive = graph PROMOTED, negative = DEMOTED
            if drift > 1:
                drift_str = f"▲ {drift:+d}"   # promoted by graph
            elif drift < -1:
                drift_str = f"▽ {drift:+d}"   # demoted by graph
            else:
                drift_str = "  ≈"
        elif n_rank and not c_rank:
            drift_str = "← Neo4j only"
        elif c_rank and not n_rank:
            drift_str = "→ Chroma only"
        else:
            drift_str = ""

        short_lbl = lbl[:43] + "…" if len(lbl) > 44 else lbl
        print(f"  {short_lbl:<44}  {n_str:^6}  {c_str:^6}  {drift_str}")

    print(f"\n  ▲ = graph signals promoted chunk above vector rank")
    print(f"  ▽ = graph signals demoted chunk below vector rank")
    print(f"{'═'*W}\n")


# ── QUERY LOG REPLAY ─────────────────────────────────────────────────────────

def find_in_log(message: str, log_path: str) -> dict | None:
    """Find most recent log entry whose message contains the search string."""
    hits = []
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if message.lower() in (entry.get("message") or "").lower():
                        hits.append(entry)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"⚠️  Query log not found: {log_path}")
        return None

    if not hits:
        print(f"⚠️  No log entries matching: {message!r}")
        return None

    best = hits[-1]  # most recent
    if len(hits) > 1:
        print(f"  (Found {len(hits)} matching log entries — using most recent: {best['ts']})")
    return best


def print_log_entry(entry: dict):
    W = 72
    print(f"\n{'─'*W}")
    print(f"  REPLAYING FROM LOG ENTRY")
    print(f"  ts        : {entry.get('ts')}")
    print(f"  model     : {entry.get('model')}")
    print(f"  tier      : {entry.get('audience_tier')}")
    print(f"  k         : {entry.get('n_chunks_config')} (config)  "
          f"{entry.get('n_chunks_retrieved')} (retrieved)")
    print(f"  sim avg   : {entry.get('chunk_similarity_avg')}  "
          f"max={entry.get('chunk_similarity_max')}")
    if entry.get("assistant_response_preview"):
        preview = entry["assistant_response_preview"][:200]
        print(f"  response  : {preview}…" if len(entry.get("assistant_response_preview","")) > 200 else f"  response  : {preview}")
    print(f"{'─'*W}")


# ── MAIN ─────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Debug Neo4j retrieval for the Digital Twin.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python replay_retrieval.py --query "How did you get into beekeeping?"
          python replay_retrieval.py --query "..." --compare
          python replay_retrieval.py --query "..." --tier personal --k 8
          python replay_retrieval.py --replay "beekeeping"
          python replay_retrieval.py --replay "beekeeping" --compare --full
        """),
    )
    parser.add_argument("--query",   metavar="TEXT",
                        help="Run a fresh retrieval for this query")
    parser.add_argument("--replay",  metavar="TEXT",
                        help="Find message in query log and use its tier/k settings")
    parser.add_argument("--log",     metavar="PATH", default=QUERY_LOG,
                        help=f"Path to query log (default: {QUERY_LOG})")
    parser.add_argument("--tier",    default="public",
                        choices=["public", "personal", "inner_circle"],
                        help="Audience tier controlling sensitivity filter (default: public)")
    parser.add_argument("--k",       type=int, default=DEFAULT_K,
                        help=f"Number of results to retrieve (default: {DEFAULT_K})")
    parser.add_argument("--fetch-k-mult", type=int, default=4,
                        dest="fetch_k_mult",
                        help="fetch_k = k × this multiplier for Neo4j candidate pool (default: 4)")
    parser.add_argument("--compare", action="store_true",
                        help="Also run ChromaDB and show ranking comparison")
    parser.add_argument("--full",    action="store_true",
                        help="Show full chunk text (default: first 400 chars)")
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.query and not args.replay:
        print("Usage: python replay_retrieval.py --query '...' [--compare]")
        print("       python replay_retrieval.py --replay 'message substring'")
        sys.exit(1)

    query = args.query
    tier  = args.tier
    k     = args.k
    preview = None if args.full else PREVIEW_CHARS

    # Replay mode: pull settings from log entry
    if args.replay:
        entry = find_in_log(args.replay, args.log)
        if entry:
            print_log_entry(entry)
            query = query or entry.get("message", args.replay)
            tier  = entry.get("audience_tier") or tier
            k     = entry.get("n_chunks_config") or k
        else:
            query = query or args.replay

    if not query:
        print("❌  No query found.")
        sys.exit(1)

    print(f"\n  Query: {query!r}")

    # Run Neo4j
    neo4j_recs = run_neo4j(query, tier, k, fetch_k_mult=args.fetch_k_mult)
    print_neo4j_results(neo4j_recs, preview or 99_999, tier, k, args.fetch_k_mult)

    # Optional ChromaDB comparison
    if args.compare:
        if not os.path.exists(CHROMA_PATH):
            print(f"⚠️  ChromaDB not found at {CHROMA_PATH}/ — skipping comparison.")
        else:
            chroma_rows = run_chromadb(query, tier, k)
            print_chromadb_results(chroma_rows, preview or 99_999, tier, k)
            print_comparison(neo4j_recs, chroma_rows)


if __name__ == "__main__":
    main()
