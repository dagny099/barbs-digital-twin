# My PhD Research and Why It Matters Now

## Document Type: Knowledge Base — Professional Positioning
## Topics: visual question answering, VQA, attention mechanisms, transformers, multimodal AI, computer vision, relevance, PhD applications, hiring

## Where My Research Sits in Today's Landscape

I was studying the computational problem of visual attention allocation between 2005 and 2010 — over a decade before transformer-based attention mechanisms became the backbone of modern AI. I don't claim I was doing the same thing, but the questions I was asking rhyme with the ones driving today's systems in ways I find genuinely exciting.

My dissertation modeled how humans combine multiple sources of information — visual saliency (bottom-up features), target features (what you're looking for), and scene context (learned priors about where things tend to be) — to decide where to look. Modern multimodal AI systems face an analogous challenge: combining low-level features with high-level semantic understanding to allocate computational attention across an input. The problems aren't identical — biological and artificial attention operate under very different constraints — but the structural parallels have given me a useful intuition for how these systems work and where they're likely to break down.

## Visual Question Answering (VQA)

My research shares deep roots with modern Visual Question Answering. In my experiments, observers were given a question (e.g. "Is there a person in this scene?") and had to search a complex visual scene to answer it. I studied how their eyes — their attention — moved through the image to find the answer, and how memory and context shaped that process.

Today's VQA systems like GPT-4V tackle a related problem computationally: given an image and a question, figure out which parts of the image are relevant to answering the question. The attention mechanism in a transformer does something loosely analogous to what I measured with eye tracking — weighting different spatial regions of the input based on their task relevance.

The key difference is that I studied this in humans, with real cognitive constraints: limited foveal resolution, sequential eye movements, memory retrieval delays. Understanding those constraints — where human attention is efficient and where it breaks — gives me a lens for thinking about where AI systems might struggle, and what architectural choices might help.

## How This Informs the Roles I'm Drawn To

For roles involving document understanding or medical image analysis: my dissertation studied how humans visually search complex scenes to answer questions. Medical document VQA — extracting answers from claims, charts, and clinical notes — is a related class of problem: directing attention to the right part of a complex visual input based on what you need to know. I don't think the methods transfer directly, but the conceptual framework — multiple sources of guidance, contextual priors, attention allocation under uncertainty — carries over meaningfully.

For roles involving knowledge graphs and contextual retrieval: my concept of "scene-specific location priors" functions like a spatial knowledge graph. The brain builds associations between a scene's identity and where things are likely to be found. My Comparative Map Analysis method was a way to evaluate how well different knowledge representations predict behavior — which resonates with what I now do when evaluating RAG retrieval quality, even though the domains are quite different.

For roles involving search and recommendation: my entire dissertation was about efficient search — specifically, how prior experience creates biased but effective search strategies. The tension between exploration (looking everywhere) and exploitation (going straight to where you think the target is) was a central theme, and that tension shows up across recommendation systems and information retrieval, even if the technical implementations diverge.

## What My PhD Gave Me

Beyond the specific research findings, my PhD trained me to think about intelligence as an information processing problem with real constraints. You have limited resources (attention, compute, memory bandwidth), rich prior knowledge, and a task to accomplish. The question is always: how do you allocate those limited resources most effectively?

That framing shapes how I approach AI engineering. Whether I'm designing a RAG pipeline, building a knowledge graph, or evaluating an ML model, I'm thinking about what information the system has, what it needs, and what's the most efficient path between those two states. Not because the biological and artificial cases are the same — they're not — but because the cognitive science training gave me a habit of asking the right structural questions.
