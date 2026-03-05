# Resume Explorer: Where It's Going and Why
*Barbara Hidalgo-Sotelo — Written for Digital Twin Knowledge Base*

---

## The Question I'm Really Trying to Answer

The MVP of Resume Explorer shows you *what's in* a resume as a knowledge graph. The roadmap is about answering the harder question: *so what?* 

A graph that just displays your career history is interesting but not particularly useful on its own. What becomes powerful is when that graph can be enriched with context from the world, searched with the precision of a database and the flexibility of natural language, and used to make genuinely interpretable recommendations — not "our algorithm thinks you'd be good at X" but "here are the three specific paths through your career graph that suggest X."

That's the north star. The roadmap is the path there.

---

## Why I Sequenced It This Way

The order matters and it's not arbitrary. I spent real time thinking through dependencies.

**Enrichment has to come first.** If you try to build semantic search or recommendations on top of graph nodes that just say "Google" or "Python" — raw strings with no stable identity — you get brittle, noisy results. Before you can search well or recommend well, you need your entities to *mean something* beyond their string labels. That means linking them to external knowledge bases with real, dereferenceable URIs.

**Semantic search builds on enrichment.** Once your "MIT" node is linked to Wikidata's MIT (with type, location, endowment, founding date attached), your embeddings are richer. Your search recall improves. And critically, you can blend embedding similarity with graph-structure filters in ways that aren't possible when your nodes are just strings.

**Recommendations come last** because they're the most complex and benefit from everything upstream. Graph-based recommendations that cite specific paths are only *explainable* if those paths are built on enriched, validated entities. Do it out of order and you get opaque outputs you can't justify to a user.

---

## Milestone 0: Getting the Foundation Right

Before any of the interesting stuff, I need to nail the basics: stable URI schemes for every entity, SHACL validation shapes to enforce consistency, and reliable IRI export. This is unglamorous work but it's the kind of thing that prevents everything downstream from drifting.

I've seen enough data pipelines collapse in the middle because nobody thought carefully about entity identity at the start. In a graph system it's especially painful — a string mismatch means two nodes that should be the same entity become disconnected islands. The foundation milestone is insurance against that.

---

## Milestone 1: Linked Open Data Enrichment

The goal here is entity alignment — connecting Resume Explorer's internal nodes to external knowledge bases. The plan:

Start with **Wikidata** (broad coverage, multilingual labels, actively maintained) and **DBpedia** (more stable URIs, better for long-running pipelines) for universities, companies, and skills. Mix both; prefer sources with clear licensing.

Matching strategy I care about: deterministic rules before fuzzy matching. Exact name plus country or industry filter gets you most of the way there with zero false positives. Fuzzy matching improves coverage but introduces risk — I'd gate it behind confidence scores and a manual review queue rather than auto-merging.

Once entities are aligned, pull high-value attributes: organization type, headquarters location, industry codes (NAICS/ISIC), enrollment size, founding dates, aliases. Store enrichment in **named graphs** so it's clearly separated from the canonical resume data — this makes rollback clean and provenance transparent.

The output of this milestone is a graph where "MIT" isn't a string — it's a node with a Wikidata URI, linked to location data, type information, and whatever else the knowledge base carries.

---

## Milestone 2: Semantic Search and Embeddings

Once the graph is enriched, I want to make it searchable in a way that blends two complementary approaches.

**Embedding-based search** gives you flexibility — "find roles similar to my current one" works even if you don't know the exact terms. But embeddings alone are imprecise and can't enforce graph constraints like "only skills used within the last three years" or "only roles in the biotech industry."

**Graph-structure filters** give you precision but require you to know what you're looking for.

The design I want: **hybrid retrieval** that layers both. Your query hits the embedding index first for recall, then graph filters narrow for precision. And crucially — every search result comes back with the supporting triples that justified it. Not just "here's a result" but "here's *why* this result."

That explainability requirement shapes the whole architecture. It means I can't use a black-box embedding system alone. It means the graph structure has to be queryable alongside the vector index. It's more complex to build but it's the only version I'd actually trust.

---

## Milestone 3: Graph-Based Recommendations

This is where the whole thing becomes genuinely useful for career intelligence.

The idea is to materialize *derived relations* — things that aren't explicit in the resume but emerge from the graph structure. "Skill co-usage" (which skills tend to appear together in similar roles). "Role progression" (common paths between job titles). "Project similarity" (roles that share significant skill overlap). These derived relations become the signals for recommendations.

Recommendation types I want to ship:
- **Next roles**: given your current graph, what's the most common adjacent position?
- **Skills to deepen**: which skills appear in roles you're targeting but are underrepresented in your graph?
- **Certification gaps**: which certifications are associated with roles at the next level that you don't have?

The crucial design constraint: every recommendation cites the specific graph paths that drove it. "We suggest deepening your Kubernetes experience because: (1) it appears in 73% of Staff Engineer roles, (2) you've used Docker in 4 of your last 5 roles (strong adjacent signal), (3) your most recent role is missing it." That's a recommendation you can act on. That's the difference between career intelligence and a random suggestion engine.

---

## What This Reflects About How I Build

The sequencing of this roadmap — enrich first, search second, recommend third — reflects something I try to apply consistently: **don't optimize on top of a weak foundation**. Better embeddings on top of noisy, ambiguous entities don't solve the problem. Better recommendation algorithms on top of imprecise retrieval don't solve the problem. Get the semantics right first, then layer intelligence on top.

The explainability constraint isn't a nice-to-have. It's a design requirement I set at the start and that shapes every architectural choice. I think this comes directly from my background in cognitive science — I'm deeply skeptical of systems that produce outputs humans can't interrogate. A career recommendation system that can't explain itself isn't a tool, it's a magic 8-ball.

The long-term vision: a public SPARQL endpoint backed by the enriched graph, so Resume Explorer's data can talk to any other semantic web system. That's the version where interoperability stops being a technical choice and becomes genuinely useful infrastructure.
