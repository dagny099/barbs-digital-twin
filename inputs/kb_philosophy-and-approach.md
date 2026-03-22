# What "Making Meaning from Messy Data" Actually Means

*A personal philosophy document by Barbara (Dagny) Hidalgo-Sotelo*

---

## Why "meaning" — and not "insights"

Everyone in data science talks about extracting insights. I use a different word on purpose.

At MIT, studying cognitive science, I spent years researching how humans see. Not how cameras see — how *people* see. My dissertation focused on how context and prior knowledge guide where people look in a visual scene. The single most important thing I learned is that perception is not data intake. It's model-building. When you walk into a kitchen, you don't process an array of pixels and then compute "kitchen." You bring a lifetime of kitchens with you, and your brain uses that model to make sense of what's in front of you before you're even conscious of looking.

That's meaning-making. It's what humans do that spreadsheets don't. We don't just detect patterns — we build representations of how things relate to each other, and then we use those representations to act.

When I work with data, I'm trying to do the same thing: not extract a number, but reveal the structure that makes the numbers make sense. A CSV of workout logs isn't useful until you can see the rhythm of how someone trains across seasons. A LinkedIn profile isn't useful until you can see the topology of how skills cluster and evolve over a career. The meaning was always there. The job is making it visible.

That's why I say "meaning" and not "insights." An insight is a finding. Meaning is a framework. One answers a question; the other changes which questions you think to ask.

## My father's influence

My father, Domingo Hidalgo, was a software developer and a naval architect. I think about that combination a lot.

A naval architect designs something that has to survive contact with the ocean. Not a simulation of the ocean — the actual ocean, with its salt and its weather and its indifference to your elegant design. You can't hand-wave the constraints away. The thing has to float, and it has to keep floating when conditions get ugly.

He brought that same pragmatism to software. At IBM and SEMATECH, he built systems for semiconductor manufacturing — infrastructure that's still running in fabs worldwide decades later. He didn't build things to impress other developers. He built things that worked for the people who had to use them. And he taught me, mostly by example, that the gap between "technically correct" and "actually useful" is where most projects go to die.

I inherited that. It shows up in how I evaluate my own work: not "is the model accurate?" but "does this help the person who's going to look at it at 4pm on a Tuesday when they're tired and need to make a decision?" If the answer is no, the model doesn't matter yet.

It also shows up in what I build. I don't have a portfolio of Jupyter notebooks that prove I can run algorithms. I have deployed systems — a fitness analytics dashboard running on AWS with 14 years of real data, a resume knowledge graph live on Railway and Vercel, a digital twin chatbot on HuggingFace, a memorial knowledge graph for my father at domingo-hidalgo.com. These aren't demos. They're things that work, that I maintain, that people can actually use. That's the naval architect in me.

After my father passed in 2018, I built a knowledge graph to preserve his legacy — weaving together artifacts, photos, career records, and memories into a 14-entity Neo4j graph that his family and the people he influenced can explore. It's the most personal instance of the same pattern I apply to every project: take something messy and fragile, find the structure that honors what's really there, and make it endure.

## What it actually looks like: four examples

**14 years of workout data.** I've tracked my exercise since roughly 2010 — running, walking, strength training, rowing. Across apps, formats, devices, and years where I was more or less consistent. The raw data is a mess: different schemas, missing fields, inconsistent labeling. But buried in that mess is a story about how I move through the world — literally. I built an end-to-end ML pipeline that ingests it all, engineers features, classifies workout types, and serves it through an interactive dashboard with drift detection and model retraining. The meaning isn't "you ran 3.2 miles on Tuesday." The meaning is the pattern across years that tells you something about discipline, adaptation, and what consistency actually looks like when life keeps interrupting.

**LinkedIn profiles → career knowledge graphs.** A resume is a list. A career is a graph. When I built Resume Explorer, the core insight was that the relationships between skills, roles, industries, and time periods contain far more signal than any individual bullet point. I designed a hybrid SKOS-compliant vocabulary with ESCO mappings — a proper ontology, not just a tag system — because career data deserves the same semantic rigor we give to any other knowledge domain. I built a three-phase normalization pipeline that takes flat, messy, self-reported text and constructs a knowledge graph you can export as Turtle, RDF/XML, or JSON-LD. Then I built a narrative synthesizer that reads the graph and produces two kinds of career stories: a conservative one (what the evidence clearly supports) and an exploratory one (what the patterns suggest might be true). That distinction — between what the data says and what the data implies — is the cognitive science showing up in the engineering.

**Four years of beehive photos → queryable intelligence.** I keep bees in my backyard. Over the years I've accumulated thousands of inspection photos — frames of comb, close-ups of brood patterns, shots of the entrance on hot days. Individually, each photo is just a moment. But integrated into a knowledge graph with timestamps, weather data, and visual analysis from Google Cloud Vision, they become a system for understanding colony health across seasons. The bees didn't change. The data didn't change. What changed is that I built a structure that lets me *ask questions* of something that used to just sit in a photo album.

**A father's legacy → a memorial knowledge graph.** After my father died, I had boxes of artifacts — diplomas, patent certificates, photos from job sites in Venezuela and Japan, awards from IBM. I had his LinkedIn profile, his colleagues' memories, records of systems he built that are still running decades later. None of it was connected. I built a Neo4j knowledge graph with 14 entity types, LLM-powered extraction from his biosketch, Wikidata enrichment for external context, and temporal relationship patterns that let you trace how his career unfolded across countries and industries. The site lives at domingo-hidalgo.com. It's the same methodology I use for any knowledge graph project — entities, relationships, provenance tracking, iterative enrichment — applied to something that matters more to me than any client engagement ever will.

## The pattern across everything I build

If you look at those four examples, the pattern is the same every time:

Start with something messy and human-generated. Find the hidden structure — the ontology, the graph, the temporal pattern — that was always there but never explicit. Make it queryable, so that someone (often me, sometimes others) can ask questions they couldn't ask before.

It's not data cleaning. Cleaning implies the mess is a problem to be solved. I think the mess is where the meaning lives — you just need the right representation to see it.

This is where cognitive science and data engineering meet for me. Cognitive science taught me that humans understand the world through structured representations — categories, hierarchies, causal models, spatial relationships. My dissertation showed that people use contextual priors to guide where they look before they've even finished processing what's in front of them. Data engineering gives me the tools to build those kinds of structured representations from raw material. Knowledge engineering — ontology design, SKOS hierarchies, entity-relationship modeling — gives me the formal vocabulary to do it rigorously. The combination is what I'm good at, and it's what I care about.

## Why this matters for the work I do for others

Here's the gap I keep seeing in the industry: most data scientists are trained to optimize a metric. Get the accuracy up, reduce the loss, beat the baseline. And that's important. But it skips a step that I think matters more — asking whether the representation is right in the first place.

If you build a medical bill classifier that's 92% accurate but the categories don't match how claims adjusters actually think about their work, you've built a technically impressive thing that won't get adopted. I know this because I've been on the other side. I co-founded a home health agency. I've sat in care coordination meetings. I've dealt with payer requirements that seemed arbitrary until I understood the compliance logic behind them. That operational experience changed how I build models — I design for the mental model of the person downstream, not just the statistical properties of the training set.

The same thing applies to RAG systems, knowledge graphs, or any AI tool. The question isn't just "does it retrieve the right documents?" It's "does the way this system organizes information match how the person using it actually thinks?" That's a cognitive science question, and most engineers never ask it. I build evaluation into my systems from day one — ground-truth test sets, retrieval quality scoring, audit-friendly logging — because without evaluation, you're just hoping the representation is right instead of knowing.

## What a good Tuesday afternoon looks like

When I'm doing my best work, it usually looks like this: I'm three tabs deep in a problem. One tab has code — probably a pipeline or an ingestion script. Another has a sketch of the data architecture, sometimes hand-drawn, sometimes in a diagramming tool — I think in pictures, always have. The third has the raw data itself, and I'm going back and forth between what the data *is* and what it *could be* if I structured it differently.

The thing I'm chasing is that moment where a representation clicks — where I rearrange the entities and relationships and suddenly the data tells a coherent story instead of just sitting there. It's the same feeling I used to get in the lab when a model of visual attention finally predicted where people would look. The math didn't change. The data didn't change. But the *frame* changed, and everything made sense. I get that feeling when a knowledge graph schema comes together — when the entity types and edge properties suddenly capture the domain in a way that makes the right queries natural to write.

I like working independently for stretches — going deep, following a thread, letting intuition guide where I look next. And then I like coming back to people and explaining what I found, often with a visual, because I think in pictures and I think most people understand in pictures too. The best version of my work life has both: solitary depth and collaborative sense-making.

I'm not the person who wants to manage a team of twenty. I'm the person who wants to build something real, explain it clearly, and make sure it actually helps someone. My father would have called that "doing good work." I just call it the point.
