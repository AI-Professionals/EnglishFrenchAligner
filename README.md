# EN ↔ FR Phrase Alignment Framework

Adds a third `Alignment` column to any English/French CSV. Each cell contains
a detailed, line-by-line **phrase / clause / word / punctuation alignment**
between the two texts, e.g.:

```text
- **Death** [Noun] **<-->** **La mort** [Noun Phrase]
- **is something that** [Clause] **<-->** **est une chose qu'** [Clause]
- **we're often discouraged to talk about** [Verb Phrase / Passive] **<-->** **on nous décourage souvent de discuter** [Verb Phrase / Active]
- **,** [Punctuation] **<-->** **[omitted]** [Punctuation]
- ...
```

The original `English` and `French` columns are never modified, reordered,
or re-translated. Output is a valid CSV with the multiline `Alignment` cells
properly quoted (`\r\n` row endings, UTF-8).

> **New to this?** Read [TUTORIAL_COLAB.md](TUTORIAL_COLAB.md) — a
> click-by-click, cell-by-cell guide: what the framework does, plus a full
> Google Colab (GPU) tutorial from scratch.

---

## Two modes — one framework

| | `--method cpu` (default fallback) | `--method neural` |
|---|---|---|
| Hardware | **Any PC, no GPU** | CUDA GPU (free **T4** on Colab) |
| Dependencies | none (Python stdlib only) | `requirements-gpu.txt` |
| Speed | ~0.2 ms per row | ~1–3 s per row (batched) |
| Accuracy | good (grammar rules) | **highest** (neural word alignment) |

The two modes share the same output format and labels. The GPU mode is a
**hybrid**: a neural word aligner (AWESOME-align, built on multilingual
BERT/XLM-R) decides *which* chunks correspond, while a fast rule-based layer
still produces the grammar labels and the exact bullet format required.
`--method auto` uses the GPU when available and silently falls back to CPU —
you can run the same command on any machine.

---

## Quick start (local PC, no GPU)

```bash
git clone https://github.com/AI-Professionals/EnglishFrenchAligner
cd en_fr_align

# process a CSV whose columns are [English, French]
python run_align.py --src "French Full Dictionary - Sheet1 (2).csv" --method cpu

# validate the result (14 automated QC checks)
python run_align.py --src "French Full Dictionary - Sheet1 (2).csv" \
                    --out "French Full Dictionary - Sheet1 (2)_aligned.csv" --check
```

Output is written next to the input as `<name>_aligned.csv`. That's it —
no packages to install for CPU mode.

> Heads-up: `--method cpu` re-uses the exact engine that generated the
> already-delivered `French Full Dictionary - Sheet1 (2)_aligned.csv`
> (175,621 rows, all 14 QC checks passing). Use the Colab GPU mode below if
> you want to regenerate it with neural word alignment for even better
> chunk pairing.

---

## Uploading to GitHub

1. `cd` into this folder (`en_fr_align/`) and initialize a repo:
   ```bash
   git init
   git add .
   git commit -m "EN-FR phrase alignment framework (CPU + optional GPU)"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/en_fr_align.git
   git push -u origin main
   ```
2. (Or just drag the folder to github.com/new → "uploading an existing file".)

---

## Colab with GPU — highest accuracy

Follow these steps exactly. A free Colab **T4 GPU** takes ~30–60 min for a
175k-row file; a few thousand rows take a couple of minutes.

### Step 1 — start a GPU runtime
Open [colab.research.google.com](https://colab.research.google.com) →
**File → New notebook** → **Runtime → Change runtime type** →
Hardware accelerator: **T4 GPU** → Save.

### Step 2 — install dependencies (one cell)
```python
%pip install -q torch transformers numpy awesome-align==2.0.1
```
The first run also downloads the mBERT model (~680 MB) once; it is cached
for later runs. If `awesome-align==2.0.1` fails to build on your Python
version, the framework automatically retries the newer `Aligner` API and
then the `awesome-align` CLI — no code changes needed.

### Step 3 — get the framework and your CSV
```python
# A) clone the framework from GitHub:
!git clone https://github.com/YOUR_USERNAME/en_fr_align.git
%cd en_fr_align

# B) upload your CSV (choose one of the two lines below)
from google.colab import files
uploaded = files.upload()          # pick "French Full Dictionary - Sheet1 (2).csv"
SRC = list(uploaded.keys())[0]

# (alternative) or read it from Google Drive:
# from google.colab import drive
# drive.mount('/content/drive')
# SRC = '/content/drive/MyDrive/french/French Full Dictionary - Sheet1 (2).csv'
```

### Step 4 — run the alignment (GPU)
```python
import os
OUT = os.path.splitext(os.path.basename(SRC))[0] + '_aligned.csv'
!python run_align.py --src "{SRC}" --out "{OUT}" --method neural --batch-size 32
```
Progress prints every 2,048 rows. `--method auto` also works if you want to
test on a CPU-only Colab session.

### Step 5 — QC + download
```python
!python run_align.py --src "{SRC}" --out "{OUT}" --check
from google.colab import files
files.download(OUT)
```

Tip: for a quick sanity check on a small sample first, run
`!python run_align.py --src "{SRC}" --out "{OUT}" --method neural --limit 200`
and inspect the first rows in the notebook with `!head -40 "{OUT}"`.

---

## Command-line reference

```
python run_align.py --src FILE.csv [options]

  --src FILE            input CSV (columns: English, French)     [required]
  --out FILE            output CSV (default: <src>_aligned.csv)
  --method auto|cpu|neural
                        auto = neural if GPU available else CPU   [default: auto]
  --limit N             process only the first N data rows
  --file-chunk N        rows held in memory per chunk (neural)    [default: 2048]
  --batch-size N        neural model batch size                   [default: 32]
  --align-layer N       mBERT attention layer for alignment       [default: 8]
  --neural-weight W     how strongly the neural matrix steers
                        chunk pairing                             [default: 1.5]
  --model-name NAME     awesome-align checkpoint
                        (HF model name or local path)   [default: bert-base-multilingual-cased]
  --no-cuda             force CPU even if a GPU is present
  --check               run the 14-check QC suite on --out and exit
```

---

## How it works

```
                 ┌─────────────────────────────────────────────┐
  EN, FR rows ──▶│ 1. tokenize + classify (pure Python rules)  │
                 │ 2. chunk into phrases/clauses/punctuation   │
                 └──────────────┬──────────────────────────────┘
                                │
          ┌─────────────────────┴──────────────────────┐
          │  neural mode (GPU):                        │
          │  AWESOME-align aligns the word tokens      │
          │  of EN ↔ FR (mBERT attention)              │
          └─────────────────────┬──────────────────────┘
                                │ word-pair evidence → chunk score matrix
          ┌─────────────────────┴──────────────────────┐
          │ 3. monotone DP pairs chunks (uses neural   │
          │    matrix when present, else pure rules)   │
          │ 4. label each unit (Verb Phrase / Passive, │
          │    Relative Clause, Punctuation, ...)      │
          │ 5. punctuation aligned separately;         │
          │    omitted material → **[omitted]**        │
          └─────────────────────┬──────────────────────┘
                                ▼
                 valid CSV: English, French, Alignment
```

Key properties (from the spec): alignments are by *meaning/function* not word
position; both sides may be different phrase sizes; omitted English material
is marked `**[omitted]**`; punctuation is aligned as its own unit; the French
text is used exactly as provided — never rewritten.

---

## Quality control

`--check` re-opens the generated file and verifies all 14 requirements:
row count preserved, EN/FR columns byte-identical, exactly one new
`Alignment` column, no empty cells, every line contains `<-->` with both
sides, `[omitted]` handling, punctuation preserved, valid quoted multiline
CSV, no column spill, and reasonable unit counts per row.

```python
# ...or from Python
import qc
issues, stats = qc.check('input.csv', 'input_aligned.csv')
print(issues)          # [] = all checks pass
```

---

## Project layout

```
en_fr_align/
├── run_align.py            # CLI (cpu / neural / auto, --check)
├── align_core.py           # rule-based engine: tokenize → chunk → label → DP
├── lex_en.py, lex_fr.py    # EN/FR word-classification lexicons
├── gloss.py                # compact EN→FR glossary (DP tie-breaker)
├── neural.py               # GPU word-aligner wrapper + chunk-score glue
├── qc.py                   # 14-check validation suite
├── requirements.txt        # CPU mode: nothing needed
├── requirements-gpu.txt    # Colab GPU mode
├── colab/EnFr_Align_Colab.ipynb   # ready-to-run Colab notebook
└── tests/                  # sample.csv + smoke tests (no GPU needed)
```

---

## Notes, tuning & credits

- Rows longer than 128 words skip the neural layer (mBERT's 512-token
  limit) and are aligned by pure rules — the output stays valid.
- If a row fails on the GPU side, it silently falls back to the rule-based
  path; one bad row can never sink a batch.
- Tune `--neural-weight` (0.5–3.0) if you want the neural matrix to pull
  more or less strongly against the lexical rules.
- The neural layer uses **AWESOME-align** (Dou & Neubig, EACL 2021):
  *"Word Alignment by Fine-tuning Embeddings on Parallel Corpora"*
  — https://github.com/neulab/awesome-align
