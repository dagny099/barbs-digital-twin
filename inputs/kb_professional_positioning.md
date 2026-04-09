# Professional Positioning

*A positioning document by Barbara (Dagny) Hidalgo-Sotelo*

---

## What I do

I'm a consultant who codes, an engineer who communicates, and a strategist with proof. That combination is rarer than it sounds.

Most people in AI come from one of three backgrounds: they're pure technical (can build but struggle to explain tradeoffs to a VP), pure consulting (great slides but can't implement), or sales-adjacent (strong demos but limited architectural depth). I've worked across all three, and I bring all three to every engagement. I take projects from fuzzy requirements through architecture, implementation, and deployment — and I can present the results to a C-suite or debug the pipeline myself, depending on what the situation needs.

My primary focus is applied AI and GenAI systems. I build RAG architectures, knowledge graphs, evaluation frameworks, and LLM-powered applications that solve real problems for real users. My secondary lens is evaluation and decision support — turning messy system behavior into defensible metrics, experiments, and actionable decisions. These aren't separate identities; they're two sides of the same coin. Building a good AI system *is* an evaluation problem, and good evaluation requires understanding what the system is actually doing.


## What sets me apart

There's a gap I keep noticing in how AI teams are staffed. Data scientists understand models but not the operational reality of the people who'll use them. Domain experts understand workflows but can't architect systems. Consultants can scope projects but can't ship code. I've been on all three sides, and I solve the integration problem between them.

Here's what that looks like concretely:

I co-founded a home health agency. I've sat in care coordination meetings, dealt with payer requirements, built an EMR system from scratch, and navigated HIPAA compliance operationally — not theoretically. When I later built an ML classifier for medical bill adjudication that processed 4M+ bills annually and hit 92% accuracy, I didn't just optimize a metric. I designed the classification scheme around how claims adjusters actually think about their work, because I'd been on the other side of that workflow.

I've led Lean Six Sigma workshops and co-facilitated C-level design discussions at a healthcare technology company. I've built Python utilities for federal data governance teams and designed integrations between ServiceNow, Drupal, and PowerBI for a regulatory agency. I've mentored research staff at UT Austin on a 1,000-participant longitudinal study. And in the last year and a half, I've built and deployed a portfolio of GenAI applications — RAG systems, knowledge graph pipelines, multi-LLM platforms, a memorial knowledge graph — that are live and running, not sitting in notebooks.

That breadth isn't diffusion. It's the same skill applied in different contexts: take something messy, find the structure that makes it useful, and build a system that the people downstream can actually work with.

## Three strengths I'd want an employer to feel quickly

If someone spent only a few minutes with my background, there are three things I'd most want them to come away with.

### 1. I bridge business problems, technical design, and evaluation

One of the most useful things about my background is that I can contribute at multiple points in the process without losing the thread. The consultant in me helps clarify the actual business problem and translate pain points into decisionable goals. The engineer in me can design a technical approach that makes sense within real constraints. And the data scientist in me wants to know whether the system is actually working and whether the results tie back to the original objective. I am often most valuable in the spaces where those functions would otherwise drift apart.

### 2. I bring a systems-level mindset to messy real-world problems

I tend to approach complex problems holistically rather than forcing them into one technical frame too early. That means I care about context, dependencies, downstream users, and the realities of the domain before I rush to solution mode. I also have the patience and curiosity to deepen my understanding of a problem space, which matters because a lot of real-world AI and data work fails when people optimize for elegance before they understand the terrain.

### 3. I care about communication, adoption, and building knowledge that lasts

I do not think a project is successful just because the model runs or the architecture looks clever. I care whether people can understand it, use it, and continue getting value from it over time. Whether I'm building an app for beekeepers, designing a retrieval system, or helping stakeholders navigate transformation, I want the result to create durable value rather than a short-lived artifact. Good systems should not only function — they should make knowledge more usable and decisions more grounded for the people downstream.


## The cognitive science angle

My PhD at MIT was in cognitive science — specifically, how humans guide their attention through visual scenes. My dissertation, cited over 430 times, showed how people use contextual priors and learned scene structure to decide where to look before they've even finished processing what's in front of them. I built computational models that predicted gaze patterns based on scene context and task demands.

What MIT gave me was bigger than one dissertation topic. It trained me to think in terms of structured representations, contextual priors, reasoning under uncertainty, and rigorous evaluation. David Marr's levels-of-analysis framework still shapes how I break problems apart: what is the system trying to do, how does it do it, and how is that process actually realized? That habit carries directly into how I think about AI systems, retrieval pipelines, and knowledge representations now.

Later consulting work reinforced the operational side of that same mindset. I became even more focused on whether a system is not just technically sound, but usable, trusted, and ready for real-world performance. That's part of why I care so much about evaluation, downstream decision-making, and the fit between a representation and the people who need to work with it.
That research shapes every system I build, even when I'm not thinking about it explicitly. The core insight is that humans don't process raw information — they build structured representations of the world and use those representations to act. When I design a RAG system, I'm not just optimizing retrieval metrics. I'm asking whether the way the system organizes and presents information matches how the person using it actually thinks. When I build a knowledge graph, I'm asking whether the entity and relationship structure captures the mental model of the domain expert, not just the statistical properties of the data.

There's a direct parallel between how I studied visual attention and how I design retrieval systems. In my research, a person searching for a coffee mug in a kitchen photo doesn't scan every pixel — they use their model of "kitchen" to jump straight to the counter. A well-designed RAG system should work the same way: the representation of the knowledge space should guide retrieval toward the right region before the similarity calculation even runs. That's the cognitive science showing up in the engineering.

This isn't an academic nicety. It's the difference between a system that tests well and a system that gets adopted. I've seen technically excellent tools fail because they organized information in a way that didn't match the user's mental model of their own work. The cognitive science training means I catch that mismatch early, before it becomes an adoption problem.

## The knowledge engineering angle

Here's something most AI engineers can't do: design an ontology.

When I built Resume Explorer, I didn't just feed resumes into an LLM and plot the output. I designed a hybrid SKOS-compliant vocabulary combining four namespaces — SKOS Core for concept organization, ESCO for the European skills and occupations standard, schema.org for structured data, and a custom namespace for resume-specific properties. The system extracts entities using provider-agnostic LLM pipelines, normalizes them through a three-phase ESCO-anchored process, and exports the resulting knowledge graph as Turtle, RDF/XML, or JSON-LD. It supports SPARQL queries for skill gap analysis and hierarchical skill classification following the ESCO taxonomy.

For the Weaving Memories project — a memorial knowledge graph for my late father — I designed a 14-entity schema with temporal relationship patterns, provenance tracking on every node and edge, and Wikidata enrichment pipelines that connect local entities to the Linked Open Data ecosystem.

This is knowledge engineering, not just "using a database." I design schemas that capture the right entities, relationships, and properties for a domain. I think about what queries the data needs to answer *before* I decide how to store it. And I anchor to formal standards (SKOS, ESCO, schema.org, RDF) when the domain warrants interoperability — which it usually does.

Most AI engineers treat the data layer as plumbing. I treat it as design. The representation *is* the product.

## The four problems I solve

**Turning messy, human-generated data into structured knowledge.** Resumes into career graphs. Beehive inspection photos into queryable intelligence. Fourteen years of workout logs into a fitness analytics pipeline. A father's legacy artifacts into a memorial knowledge graph. The pattern is always the same: start with something unstructured and inconsistent, find the ontology or graph or temporal pattern that was always there, and make it queryable. I've anchored this work to formal standards (ESCO for skills taxonomy, SKOS for knowledge organization, schema.org for structured data) when the domain warrants it, and I've built custom schemas when it doesn't.

**Building retrieval systems that actually surface the right information.** RAG isn't just "put documents in a vector store and hope for the best." I've built modular RAG architectures with evaluation harnesses (Poolula Platform), GraphRAG systems with citation-grounded retrieval (podcast knowledge graph on Neo4j), and a digital twin chatbot that required designing the knowledge base *for* retrieval — writing project briefs specifically shaped to improve how the system answers questions. The retrieval quality work is where the cognitive science really shows up: I think about retrieval as a model of how someone searches for information, not just a similarity calculation.

**Designing knowledge representations that match how people actually think.** This is the problem underneath the other three. Whether I'm building a skill taxonomy, a clinical workflow classifier, or a memorial timeline, the question is always: does this representation capture how the domain expert — the claims adjuster, the beekeeper, the family member exploring a legacy — actually understands their world? I design ontologies, schema, and graph structures with that question front and center. The CDMP certification and DCAM accreditation reflect this as a deliberate professional focus, not a side interest.

**Shipping deployed systems, not just prototypes.** My portfolio isn't notebooks and slide decks. Resume Explorer runs on Flask/Railway with a React frontend on Vercel. The Digital Twin is live on HuggingFace. The Weaving Memories memorial is deployed at domingo-hidalgo.com with a Flask API and React frontend. ConvoScope is deployed on AWS EC2 with a custom domain, SSL, and monitoring. My fitness analytics dashboard is a production ML pipeline with drift detection and model retraining workflows. I maintain these systems. They're not demos — they're infrastructure I use and that others can use.

## How I work

My ideal working pattern is: go deep independently for a stretch — research the right approach, prototype, follow a technical thread — and then come back to people and explain what I found, usually with a diagram or a visual, because I think in pictures and I think most people understand in pictures too. I'm not the person who wants to manage a team of twenty. I'm the person who wants to build something real, explain it clearly, and make sure it actually helps someone.

I'm strongest when I have autonomy to explore the solution space combined with regular touchpoints where I translate what I've learned into something the team can act on. I like helping teams understand each other better — bridging between the technical side that's thinking in architectures and the business side that's thinking in outcomes. That's what I did at Inflective, at Metric5, and at BALEX. It's what I do in my independent work. It's the through-line.

I build evaluation into my systems from the start, not as an afterthought. Poolula has a built-in evaluation harness that scores responses against ground-truth expectations. ConvoScope captures latency and token-cost metrics to guide prompt compression tradeoffs. The Digital Twin has an evaluation framework designed around five dimensions — voice fidelity, specificity, accuracy, narrative arc, and follow-up magnetism. This isn't quality assurance; it's a design philosophy. You can't improve what you don't measure, and you can't measure what you haven't thought to evaluate.

## Credentials and certifications

My formal credentials include a PhD in Cognitive Science from MIT, a BS in Electrical Engineering and a BS in Biology from UT Austin (Dean's Scholars program). I hold current certifications in Azure AI Engineer Associate (2024), Certified Data Management Professional (CDMP Associate, 2024), AWS Certified Cloud Practitioner (2023), and DCAM v2 Accreditation (2022). My dissertation research has been cited over 430 times.

These credentials matter for two reasons: the cloud certifications show I invest in staying current with the platforms I build on, and the CDMP/DCAM certifications reflect a genuine professional focus on data governance and metadata management that most AI engineers don't have. The combination of AI engineering skills with data governance literacy and knowledge engineering capability is something organizations increasingly need as they move from AI experiments to AI operations.

## Where I add the most value

I'm most valuable in environments where the problem isn't just "build a model" but "figure out what to build, build it, and make sure the people who need it can actually use it." That means organizations standing up their first RAG systems, teams trying to make sense of unstructured knowledge, companies where the gap between what the data science team builds and what the business team needs is wider than it should be. It also means anywhere that needs proper knowledge representation — ontology design, graph schema, taxonomy alignment — as the foundation for AI that actually works.

I'm less well-suited for roles that are purely about scaling existing systems to millions of users or optimizing an already-well-defined model. My strength is the zero-to-one work — going from a messy, ambiguous problem to a working system that people trust. Once it's running and the question is "make it 10x faster," that's a different skillset.

I'm honest about that boundary because I think it matters. Knowing where you add the most value — and where you don't — is how you build trust with the people who hire you.
