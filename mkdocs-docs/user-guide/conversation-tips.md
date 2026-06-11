---
title: Conversation Tips
tags:
  - user-guide
  - visitor
---

# Conversation Tips

A few patterns that make conversations with the twin notably better.

---

## Build on Previous Turns

The twin maintains conversation context within a session. This means you can have a genuinely progressive conversation — not just a series of isolated questions.

**Example flow:**

> *"What projects demonstrate Barbara's full-stack capabilities?"*

Then:

> *"You mentioned Resume Explorer — walk me through the architecture."*

Then:

> *"How does the entity extraction part work? And is there a live demo I can explore?"*

Each turn can reference and build on the last. The twin will track what it's already said and adjust its depth accordingly.

---

## Use Follow-Up Depth

For technical or portfolio questions, the first answer is often a summary. The interesting material comes when you push:

- *"Can you go deeper on the retrieval scoring?"*
- *"What were the hardest engineering decisions?"*
- *"What would you do differently if you built this again?"*
- *"What specifically about this project shows Barbara's knowledge engineering approach?"*

---

## Project Walkthroughs

For featured projects, ask for a walkthrough explicitly:

> *"Walk me through the Concept Cartographer project"*

The twin will guide you through the architecture, tech stack, design insights, and relevant links. For some projects, interactive SVG diagrams are available.

Navigation cues like *"tell me more"*, *"what's next"*, or *"go back to the architecture"* work naturally in walkthrough mode.

---

## Contact Barbara Directly

If you'd like to get in touch — to hire, collaborate, or just introduce yourself — the twin can pass your message along:

> *"I'd like to get in touch with Barbara"*
> *"Can you send her a message for me?"*

The twin will ask for your name, email, and message, then send a notification directly. No email client needed.

---

## Rate Responses

After each response, click 👍 if it was helpful or 👎 if it missed the mark. This feedback is logged and reviewed — it directly influences which gaps get filled in the knowledge base.

---

## The "exclude my traffic" Toggle

At the bottom of the page you'll see a checkbox labeled **exclude my traffic**. It's there for Barbara — when she's testing the twin herself, she ticks it so her sessions get filtered out of the analytics that drive content decisions. Visitors can safely ignore it; leaving it on or off doesn't change the conversation at all.

Under the hood the toggle simply tags the session's log rows with `is_owner_traffic: true`, and `scripts/analyze_logs.py --exclude-owner` drops those rows (and the rest of the session) when generating reports. It resets to off on every page load.

---

## Common Patterns and What They Signal

| What you say | What the twin does |
|---|---|
| *"Tell me about yourself"* | Gives a professional overview; doesn't volunteer personal details to strangers |
| *"How does this chatbot work?"* | Describes the live system you're using — with appropriate dry wit |
| *"I'm interviewing Barbara for a role..."* | Shifts to impact-forward, recruiter-appropriate framing |
| *"What don't you know?"* | Honest about knowledge gaps — offers to flag them |
| *"Roll a die"* | Calls the `dice_roll` tool (yes, really) |
| Personal references, family phrases | Warmth increases if the twin recognizes the signal |

---

!!! tip "The system knows it's a system"
    If you ask *"how does this chatbot work?"* or *"can I try a live demo?"*, the twin will note — with light humor — that you're already using it. The conversation IS the demo.
