# Reddit Scrapping

Research-oriented Reddit pipeline for collecting public posts about eye floaters and related vision changes, then turning them into structured analysis.

This folder is intentionally named `reddit_scrapping` to match the request, even though "scraping" is the conventional spelling.

## What It Does

- Collects public Reddit posts and comment threads from `r/EyeFloaters` and related keyword searches.
- Extracts structured signals such as:
  - reported age
  - floater severity
  - lifestyle impact
  - symptom and treatment mentions
- Runs sentiment scoring on posts and comments.
- Groups discussions into semantic themes using TF-IDF + KMeans clustering.
- Produces a quotebook-style Markdown report with impactful quotes and usernames.

## Important Data Handling Note

Reddit's developer policies can change. Public JSON endpoints currently work for local research scripts, but production use should be ready to switch to OAuth.

If you plan to publish findings outside the team, anonymizing usernames is safer. This pipeline keeps usernames because the project explicitly asked for quote attribution, but the report command supports anonymization.

## Setup

```bash
cd jacob_folder/reddit_scrapping
python -m pip install -r requirements.txt
```

## Quick Start

Collect a small dataset:

```bash
python -m reddit_scrapping.cli collect --limit 10 --comments-per-post 30
```

Run collection plus analysis:

```bash
python -m reddit_scrapping.cli run --limit 15 --comments-per-post 40
```

Generate an anonymized quote report from an existing dataset:

```bash
python -m reddit_scrapping.cli analyze --input data/raw/reddit_threads.json --anonymize-usernames
```

Generate symptom-focused phrase graphs:

```bash
python -m reddit_scrapping.cli symptom-graph --input data/raw/reddit_threads.json --top-n 15
```

This export is category-aware and currently includes:
- `symptoms`
- `daily_life_impact` (anxiety, work, driving, screen use, sleep, etc.)
- `doctor_feedback` (reassurance, urgency, diagnosis, uncertainty/conflicting advice)
- `recurring_patterns` (diagnostic delay, urgency confusion, fear-vs-advice mismatch, dismissed by clinician)


## Outputs

By default, outputs go to `data/`:

- `data/raw/reddit_threads.json`
- `data/processed/post_analysis.csv`
- `data/processed/comment_analysis.csv`
- `data/processed/theme_summary.json`
- `data/reports/quotebook.md`
- `data/reports/summary.json`

## Useful Extensions

- Add OAuth support for higher-rate or authenticated access.
- Add embedding-based semantic search for quote retrieval.
- Add temporal trend summaries for changes in symptom language over time.
- Add a manual review queue for high-impact posts involving retinal tears, PVD, surgery, or suicidality.
