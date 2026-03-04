# Google Takeout — Location History Explorer (Streamlit)

A lightweight Streamlit utility for *peeking* and *summarizing* your Google Takeout **Location History (Timeline)** without loading multi‑hundred‑MB files into memory.

**Key features**

- Choose your local **Takeout** directory.
- Summarize the huge `Records.json` using a **streaming parser** (`ijson`) or a fast **head-only peek**.
- Report: file sizes, overall date span, total records (streaming mode), first/last timestamps, accuracy summary.
- Summarize **Semantic Location History** (year/month JSONs): counts of `timelineObjects`, earliest/latest timestamps encountered, per‑file sizes.
- Side‑car caching: once a full scan finishes, a lightweight summary JSON is saved next to the data so subsequent runs are instant.

> ⚠️ **Privacy first**: Your data never leaves your machine. The app only reads files you point it to and optionally writes a small JSON summary alongside them for caching.

## Quick start

```bash
# 1) Create a virtual environment (recommended)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run the app
streamlit run app.py
```

Then paste the absolute path to your **Takeout** folder (the one that contains `Location History (Timeline)/`).
If you only have sample files (e.g., `Records_sm.json`), point the "Advanced → Override Records.json path" field to that file.

## Expected Takeout structure (example)

```
Takeout/
  Location History (Timeline)/
    Records.json
    Semantic Location History/
      2019/2019_JANUARY.json
      ...
```

## Notes on performance

- **Quick scan** reads only a small head of `Records.json` to determine earliest date & schema shape.
- **Full scan** uses `ijson` to count **all** records and min/max timestamps with **constant memory**. On a ~400MB file, this can take a few minutes depending on disk speed.
- Semantic files are handled per‑file with streaming; you can stop early and resume later thanks to caching.

## Caching

We write a `Records.summary.json` and `Semantic.summary.json` next to the source files (same folder). Delete these if you want a fresh scan.

---

MIT License
