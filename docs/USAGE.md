## Usage

### For Recruiters & Employers

Ask the digital twin about:
- Barbara's technical skills and certifications
- Specific projects and their technical implementations
- Professional experience and achievements
- Educational background (UT Austin, MIT PhD)
- Research publications and contributions

**Example queries:**
- "What experience do you have with data governance?"
- "Tell me about your fitness dashboard project"
- "What certifications do you hold?"
- "Describe your work at Inflective"

### For Developers

The digital twin can explain:
- Technical architecture of specific projects
- Code implementations and design decisions
- Tech stack choices and trade-offs
- Development workflows and best practices

**Example queries:**
- "How does the beehive tracker handle metadata?"
- "What graph database technologies have you used?"
- "Explain the architecture of your fitness dashboard"

### For General Users

Learn about:
- Barbara's journey from cognitive science to data science
- Her research on visual attention and eye movements
- Personal projects and hobbies (beekeeping, running, etc.)
- Philosophy and approach to learning/building

## Customizing Suggested Questions

The example questions shown in the Gradio interface can be easily customized in `app.py`.

### Quick Edit

Edit the `CURATED_EXAMPLES` list (around line 43 in `app.py`):

```python
CURATED_EXAMPLES = [
    "💼 Your professional question here",
    "🔗 Your bridge question here",
    "💭 Your personal question here",
]
```

### Question Categories

The interface uses three visual categories with color-coding:

| Icon | Category | Color | Purpose |
|------|----------|-------|---------|
| 💼 | Professional | Soft Blue | Career, technical skills, work experience |
| 🔗 | Bridge | Soft Teal | Questions connecting personal and professional |
| 💭 | Personal | Soft Purple | Interests, hobbies, philosophy, learning |

**Current distribution:** 3 professional + 3 bridge + 3 personal = 9 questions total

### Full Question Banks

Two complete question sets are stored as constants for reference and evaluation testing:

- **`RECRUITER_PROMPTS`** (10 questions): Professional/hiring-focused questions
- **`FRIENDLY_PROMPTS`** (10 questions): Casual/personal questions from friends

You can pull questions from these banks or write your own.

### Updating Colors

If you change the number of questions or reorder them, update the CSS selectors in `custom_css` (around line 205 in `app.py`) to match:

```python
/* Professional questions (positions 1-3) */
.examples button:nth-child(1),
.examples button:nth-child(2),
.examples button:nth-child(3) { ... }

/* Bridge questions (positions 4-6) */
.examples button:nth-child(4),
.examples button:nth-child(5),
.examples button:nth-child(6) { ... }

/* Personal questions (positions 7-9) */
.examples button:nth-child(7),
.examples button:nth-child(8),
.examples button:nth-child(9) { ... }
```

The `:nth-child(N)` numbers must match the position of each question in the list.
