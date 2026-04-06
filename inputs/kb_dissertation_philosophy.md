# How My PhD Shaped How I Build

## Document Type: Knowledge Base — Philosophy and Approach
## Topics: cognitive science, systems thinking, design philosophy, research methodology, building, approach, why, thinking style

## The Cognitive Science Lens

People sometimes ask why a cognitive scientist ended up building AI systems and knowledge graphs. For me, there was never a gap to bridge — cognitive science is the study of how intelligent systems process information, and I started with the biological version. The questions transfer even when the substrates don't.

My PhD trained me to look at any complex system and ask: What representations is it using? What are the constraints? Where are the bottlenecks? How does prior experience change its behavior? I developed those instincts studying human vision, but I've found they serve me well when I'm designing a data pipeline or debugging a retrieval system. Not because the systems are equivalent, but because the *habit of asking* those questions tends to surface the right issues.

## From Eye Tracking to Information Design

In my dissertation, I literally tracked where people looked, millisecond by millisecond, to understand their information-seeking strategies. That gave me a deep respect for how much behavior reveals about underlying processes. When I build systems now, I think about the user's cognitive journey — not just "does this system return the right answer" but "does it present information in a way that matches how people actually seek and process it?"

This shows up in my Digital Twin project: I didn't just build a chatbot that retrieves documents. I designed the retrieval and response flow around how different types of visitors — hiring managers, collaborators, old friends — would naturally explore my portfolio. The system's information architecture reflects what I learned about attention: people don't scan everything uniformly. They bring expectations, they look for landmarks, and the right design anticipates that.

## Comparative Map Analysis and the Evaluation Habit

One of the contributions I'm proudest of from the dissertation was Comparative Map Analysis — a method for comparing spatial patterns across different observers and conditions. Developing that method taught me something I carry into every project: the hardest part isn't building the thing, it's figuring out how to tell whether it's working.

When I build a knowledge graph, I build an evaluation harness alongside it. When I design a RAG system, I think about retrieval quality metrics from the start. The question "how would I know if this is actually good?" comes before "how do I build it?" — and that's a direct inheritance from my research training. In science, you can't publish a finding without a rigorous comparison condition. I try to hold my engineering work to a similar standard.

## Context Is Everything

My dissertation showed that scene context — the general knowledge that "kitchens have counters, offices have desks" — was the single strongest predictor of where people would look. Stronger than visual saliency. Stronger than the target's own features. Context dominated.

This finding shaped how I think about data and meaning. A data point without context is like a pixel without a scene — technically present but practically opaque. This is part of why I'm drawn to knowledge graphs: they make context explicit and structured. And it's part of why my tagline is "making meaning from messy data" — because meaning emerges when you can connect a piece of information to the web of relationships that gives it significance.

## The "Delayed Search" Insight

My delayed-search experiments showed something counterintuitive: people searched *more* effectively when you made them wait before starting to look. The extra time allowed deeper memory retrieval, so their first eye movement was more likely to go directly to the target.

There's a principle here I keep coming back to in system design: the most efficient path isn't always the fastest start. Taking time to retrieve the right context, assemble the right priors, before generating a response — that's often what makes a system feel intelligent rather than just reactive. I think about this when I'm designing retrieval strategies, when I'm structuring a prompt, when I'm deciding how much context to inject before letting a model generate. Rushing to output isn't the same as being fast.

## Why I Build Things People Actually Use

My dissertation generated interesting scientific findings, but the impact I'm most drawn to is translational — taking principles about how people process information and using them to build systems that work *with* how people think. My projects span knowledge graphs, conversational AI, data visualization, and portfolio tools. They're different in subject matter but share a throughline: making complex information accessible and meaningful to the people who need it. That impulse started in the lab, watching people search for things in cluttered scenes, and it hasn't changed.
