# Animal Guessing Game 🐾🦖

An interactive educational game built with Gradio for identifying dog breeds, cat breeds, horse breeds, and dinosaur species using progressive clue-based learning.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Gradio](https://img.shields.io/badge/gradio-6.0+-orange.svg)](https://gradio.app/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Overview

This project demonstrates an engaging way to explore classification datasets through interactive gameplay. Users select a category (Dogs, Cats, Horses, or Dinosaurs) and receive progressively revealing clues to identify species from multiple-choice options.

**Key Features:**
- 📊 **Data-Driven**: Powered by structured Excel dataset with 4 category sheets
- 🎯 **Progressive Difficulty**: 3 composite clues that combine multiple attributes
- 🎮 **Clean UX**: Smart UI that reveals elements as the game progresses
- 📈 **Performance Scoring**: Points awarded based on efficiency (fewer clues = more points)
- 🖼️ **Visual Learning**: Species images revealed after answering

### Project Context

This project was developed as an educational tool to demonstrate:
- Interactive data exploration with Gradio
- Natural language generation from structured data
- Progressive disclosure UX patterns
- Session state management in web applications

---

## Quick Start

### Prerequisites
```bash
python >= 3.11
pandas
gradio >= 6.0
openpyxl  # For Excel file reading
```

### Installation
```bash
# Clone the repository
git clone https://github.com/dagny099/guess-animal-gradio
cd guess-animal-gradio

# Install dependencies
pip install pandas gradio openpyxl

# Run the application
python guess-animal-gradio-v2.py
```

The application will launch at `http://localhost:7860`

---

## Dataset Structure

**File**: `guess-the-animal-dataset.xlsx`

The dataset contains 4 sheets, each representing a classification category:

| Sheet Name | Answer Field | Key Attributes |
|------------|--------------|----------------|
| Dog Breed Identification | `Breed` | Country, Continent, Use, Personality, Color, Lifespan |
| Cat Breed Identification | `Breed` | Country, Continent, History, Personality, Color |
| Horse Breed Identification | `Breed` | Country, Uses, Features, Height, Weight, Color |
| Dinosaur Species Identification | `Common Name` | Location, Diet, Size, Clade, Social Behavior |

Each row represents one instance, and the `Example Image` column provides a visual reference (revealed after answering).

---

## How It Works

### Game Mechanics

1. **Select Category**: Choose from Dogs, Cats, Horses, or Dinosaurs
2. **Read Clue 1**: Receive first composite clue combining multiple attributes
3. **Make Choice**: Select from 4 multiple-choice options
4. **Request Hints**: Get up to 2 additional clues (3 total)
5. **Submit or Give Up**: Reveal answer and see the species image

### Scoring System
- ⚡ **1 clue used**: 3 points (expert)
- 🎯 **2 clues used**: 2 points (proficient)
- 📚 **3 clues used**: 1 point (learning)

Streak tracking encourages consecutive correct answers.

### Composite Clues

Instead of revealing individual attributes, clues combine related fields into natural language sentences:

**Example (Dogs):**
```
Clue 1: This species was bred in Croatia, Europe during the Early 19th century for use(s) like Companion, working
Clue 2: This species is often found in colors: White with black or liver spots
Clue 3: Personality traits associated with the species are Energetic, playful, intelligent
```

This approach simulates real-world identification scenarios where multiple characteristics inform classification decisions.

---

## Technical Architecture

### State Management
Uses Gradio's `gr.State` for session persistence:
- Score and streak maintained across rounds
- Round state tracks clue progression and answer validation
- UI visibility controlled dynamically based on game state

### UI Components
- **Chatbot**: Displays clues and feedback with auto-scroll
- **Radio Buttons**: 4-option multiple choice (optimized for single-row layout)
- **Conditional Rendering**: Components hidden until contextually relevant
- **Custom CSS**: Submit button styled with green gradient for visual distinction

### Data Pipeline
```
Excel → Pandas DataFrame → Random Sampling → Option Generation → Clue Construction → UI Rendering
```
**Known Limitations:**

1. **Image URLs**: Some images may fail to load due to access restrictions (403 errors)
2. **Dataset Size**: Categories require ≥4 entries for option generation
3. **No Persistence**: Scores reset on browser refresh (no database backend)
4. **Mobile Layout**: Radio buttons may stack on narrow screens

---

## File Overview

| File | Purpose |
|------|---------|
| `guess-animal-gradio.py` | Main application (latest version with composite clues) |
| `guess-the-animal-dataset.xlsx` | Source data (4 category sheets) |
| `README.md` | This file (user-facing documentation) |

---

## Customization

### Adding New Categories
1. Add sheet to `guess-the-animal-dataset.xlsx`
2. Update `SHEETS` dict in `guess-animal-gradio-v2.py`
3. Define clue templates in `build_composite_clue()` function

### Modifying Difficulty
- **Easier**: Reduce to 3 options, reveal more fields in Clue 1
- **Harder**: Increase to 5+ options, make clues more abstract

### Styling
Custom CSS can be modified in the `gr.Blocks(css="...")` section (line 442).


---

## Future Enhancements

- [ ] Difficulty modes (Easy/Medium/Hard)
- [ ] Persistent leaderboard with database storage
- [ ] Timed challenge mode
- [ ] User-uploaded custom datasets
- [ ] Mobile-responsive layout optimization
- [ ] Dark mode theme toggle

---

## Dependencies

```txt
pandas>=2.0.0
gradio>=6.0.0
openpyxl>=3.1.0
```

---

## Contributing

Contributions welcome! Areas of interest:
- Additional category datasets (birds, fish, plants)
- Improved clue generation algorithms
- Mobile UI optimizations
- Translation/internationalization

---

## License

MIT License - feel free to use this project for educational purposes, portfolio demonstrations, or derivative works.

---

## Acknowledgments

- Dataset compiled from public educational resources
- Built with [Gradio](https://gradio.app/) framework
- Inspired by educational quiz formats and species identification guides

---
