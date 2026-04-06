# Intellectual Foundations

## Document Type: Knowledge Base — Philosophy and Approach
## Topics: intellectual foundations, MIT, cognitive science, Bayesian reasoning, David Marr, contextual priors, uncertainty, systems thinking, consulting, transformation, readiness, methodology, frameworks, how I think
## Cross-references: See also kb_dissertation_overview.md (research details), kb_dissertation_philosophy.md (how PhD shaped building), kb_dissertation_modern_relevance.md (connections to modern AI)

## Why this document exists

If you look across my career, the technologies change constantly. MATLAB turns into Python. Eye tracking turns into retrieval. Research turns into consulting. Knowledge graphs turn into AI applications. What stays stable is not the stack. It's the set of ideas I keep returning to when I need to understand a system well enough to improve it.

This document is about those ideas. It complements my dissertation and philosophy documents — those cover what I studied and how it shaped my building instincts. This one goes deeper into the intellectual frameworks themselves.

## MIT and the cognitive science foundation

MIT shaped me less by giving me a single doctrine and more by training a way of thinking. My PhD work sat inside cognitive science, computer vision, and computational modeling, and it pushed me toward a view of intelligence as something structured rather than magical.

The most durable lesson I carried forward is that intelligent behavior is rarely about reacting to raw input. It is about using representations, constraints, and prior knowledge to decide what matters.

That idea showed up in my dissertation on eye movements in familiar scenes. People did not search by treating every pixel equally. They used context, expectations, and memory to guide attention efficiently. Years later, I still find myself applying the same lens when I think about retrieval systems, evaluation frameworks, knowledge graphs, and AI interfaces. The domain changed. The logic did not.

## Bayesian reasoning — decisions under uncertainty

One of the MIT-flavored ideas that stayed with me is Bayesian reasoning, even outside formal statistics. The core intuition is simple: intelligent systems have to make decisions under uncertainty, and they do that by combining what they already believe with what new evidence suggests.

What mattered to me was not just the formula. It was the worldview behind it.

People are constantly forming hypotheses about causes, categories, intentions, and likely outcomes, then revising those hypotheses as new information arrives. That perspective helped formalize something I already found intuitively true: humans learn from sparse, messy, incomplete information by bringing structure to it. We do not just absorb data. We interpret it through models.

That way of thinking still influences how I build. In AI and retrieval work, I am often asking some version of the same question: what assumptions is this system bringing to the problem, what evidence is it using, and how should confidence change as new information comes in?

Concretely, this shows up when I'm designing a RAG system and asking "what prior knowledge should the system bring to a query before it retrieves anything?" or when I'm evaluating a classifier and thinking about base rates rather than just accuracy. The Bayesian instinct is to always ask: what did you believe before, and what changed?

## David Marr — levels of analysis

Another foundational influence is David Marr's framework for understanding information-processing systems.

Marr's core insight was that to understand a system, you need to ask at least three different questions: What is the system trying to do, and why? How does it do that computationally or algorithmically? How is that process physically realized?

I come back to that framework all the time because it prevents shallow analysis.

In modern AI, it is easy to collapse these levels. People jump straight from architecture to hype, or from implementation details to claims about intelligence. Marr reminds me to separate purpose, method, and realization. I use that habit constantly, whether I am thinking about a human attention experiment, a retrieval pipeline, a knowledge graph schema, or an enterprise workflow.

A concrete example: when someone asks me about a RAG system, I naturally decompose it into Marr's levels. The computational level is "retrieve the most relevant context for a given query." The algorithmic level is "embed the query, find nearest neighbors in vector space, inject top-k chunks." The implementation level is "ChromaDB, OpenAI embeddings, a Gradio interface." Each level has its own failure modes. Most debugging happens when people conflate them — blaming the embedding model (implementation) when the real problem is the chunking strategy (algorithm) or an unclear definition of relevance (computation).

## Context, priors, and structured representation

A through-line across my work is that context matters more than people often want it to.

In my dissertation, scene context was a stronger predictor of where people looked than raw visual saliency. In later technical work, I kept seeing the same thing in different form: a data point without context is not very useful, and a system without a good representation usually produces shallow output no matter how impressive the surface layer looks.

That is part of why I am drawn to ontologies, taxonomies, schema design, and graph structures. They are not just technical artifacts to me. They are ways of making context explicit so a person or system can reason with it more effectively.

In my Resume Explorer project, for example, the difference between a flat list of skills and a SKOS-structured taxonomy of those skills is the difference between "Barbara knows Python" and "Barbara uses Python as an implementation tool within a broader practice of knowledge engineering that connects to semantic web standards." The graph carries the context that a list cannot.

## Evaluation as a first-class discipline

Research trained me to think of evaluation as part of the design problem, not something you bolt on at the end.

That stayed with me from MIT onward. If I build a retrieval system, I want to know what success means before I optimize it. If I build a classifier, I want to know how the outputs will be interpreted downstream. If I build a knowledge graph, I want to know whether the representation supports the actual questions people need to ask.

This is one place where my academic training and later consulting work fit together very naturally. In my dissertation, I developed Comparative Map Analysis — a method for evaluating spatial patterns in eye movement data. The method was as important as the finding. I carry that instinct into every project: the evaluation harness ships with the system, not after it.

## The consulting layer — systems in real hands

Later in my career, especially through consulting and transformation work, I became more sensitive to something academic environments do not always force you to confront: a system is not successful just because it is technically correct. It has to work in the hands of real people under real constraints.

That sounds obvious, but it changes how you define success. It pushes you toward questions of readiness, accountability, role clarity, interpretability, and operational reality. It also makes you suspicious of elegant artifacts that fail at the point of use.

One consulting influence that crystallized this was the Assert methodology at Inflective, which frames transformation not as task completion but as readiness for real operation. The emphasis on target state, current reality, operational readiness, and stakeholder alignment resonated because it treats method as a way of making reality visible — not as ceremony around execution. It also emphasizes human qualities like certainty, candor, and caring alongside technical competencies, which is a more honest way to think about whether a system will actually be adopted.

That influence fits well with my earlier training. MIT gave me a way to think about representations, priors, constraints, and evaluation. Consulting reinforced that none of those matter if the resulting system is not usable, trusted, and operationally real for the people who depend on it.

## How these influences come together

If I had to summarize the combined effect of these influences, I would put it this way. I tend to look at messy domains by asking: What is the real problem here? What representation would make that problem legible? What prior assumptions are shaping interpretation? What evidence would actually update our confidence? What does success look like in lived, operational terms? How would we evaluate whether the system is helping?

That is true whether I am working on eye-tracking research, a medical workflow, a RAG pipeline, a semantic data model, or a digital twin. The surfaces change. The intellectual scaffolding does not.
