# Semantic analysis process (short)

End-to-end view: from Reddit collection to structured signals, themes, and the visualization layer in this folder.

## Very simple view (five steps, left → right)

Plain-language version of what the analysis does. **Large type** in the diagram below (works best in viewers that honor Mermaid `themeVariables`, e.g. GitHub, many IDEs).

```mermaid
%%{init: {'themeVariables': {'fontSize': '36px'}}}%%
flowchart LR
    A["Gather Reddit<br/>posts & comments"]
    B["Read the text:<br/>mood + facts"]
    C["Auto-group<br/>similar topics"]
    D["Save tables<br/>& summaries"]
    E["Bar chart +<br/>word cloud"]

    A --> B --> C --> D --> E
```

- **Gather** — download threads and replies about floaters (and related queries).
- **Read the text** — run sentiment (VADER) and rule-based tags (severity, lifestyle, quotes, etc.).
- **Auto-group** — TF-IDF + KMeans finds clusters of “what people talk about together.”
- **Save** — write CSV rows and JSON so nothing is trapped in memory.
- **Show** — scripts in this folder turn the saved data into pictures you can share.

## Combined pipeline

Single top-down flow: one **collect** node; up to **three** parallel branches for grouped semantic analysis; then merged **artifacts**; then merged **deliverables** (regex/QoL bars + word cloud).

```mermaid
%%{init: {'themeVariables': {'fontSize': '32px'}}}%%
flowchart TD
    L1["Collect — Reddit API · posts + comments"]

    L2A["Sentiment — VADER · compound + label"]
    L2B["Structured signals — analyze_text · severity emotion lifestyle medical age quotes"]
    L2C["Themes — TF-IDF · KMeans · top terms"]

    L3["Artifacts — CSV rows + summary.json + theme reports"]

    L4["Deliver — regex + QoL bar chart · floater word cloud · PNGs"]

    L1 --> L2A
    L1 --> L2B
    L1 --> L2C

    L2A --> L3
    L2B --> L3
    L2C --> L3

    L3 --> L4
```

Implementation: `analyze_text` covers **sentiment** and **structured signals**; `build_themes` covers **TF-IDF / KMeans themes**. **Deliver** step uses `grouped_trends_graph.py` and `floater_word_cloud.py` in this folder.

## Files

| File | Role |
|------|------|
| `grouped_trends_graph.py` | Regex buckets + QoL counts → dual-panel bar chart |
| `floater_word_cloud.py` | Floater-topic text → B&W word cloud PNG |
| `SEMANTIC_ANALYSIS_PROCESS.md` | This diagram |

Core NLP/theming implementation (TF-IDF, KMeans, `analyze_text`) lives under `jacob_folder/reddit_scrapping/reddit_scrapping/` — see repo root `SEMANTIC_ANALYSIS.md` for detail.
