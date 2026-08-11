# EN ↔ FR Phrase Alignment — Guide & Full Colab (GPU) Tutorial

This document has two parts:

1. **Part A — What this framework does** (the idea, the output format, the two
   modes, the project layout).
2. **Part B — Full Colab tutorial** (step by step, click by click, cell by
   cell — how to process your English/French CSV with a free GPU and get the
   highest accuracy).

> Short reference for the command line and all options: see [README.md](README.md).

---

# Part A — What this framework does

## The idea

You have a CSV with two columns:

| English | French |
|---|---|
| Death is something that we're often discouraged to talk about. | La mort est une chose dont on nous décourage souvent de discuter. |
| I like coffee. | J'aime le café. |

The framework adds a third column, `Alignment`, that contains a detailed
**phrase-by-phrase, clause-by-clause, word-by-word** alignment of the two
texts — the translation units that correspond to each other, with grammar
labels:

```text
- **Death** [Noun] **<-->** **La mort** [Noun Phrase]
- **is something that** [Clause] **<-->** **est une chose qu'** [Clause]
- **we're often discouraged to talk about** [Verb Phrase / Passive] **<-->** **on nous décourage souvent de discuter** [Verb Phrase / Active]
- **,** [Punctuation] **<-->** **[omitted]** [Punctuation]
- ...
```

The `English` and `French` columns are **never changed** — no re-translation,
no reordering, no spelling fixes. Only the new column is added, and the output
is a valid CSV with the multiline cells properly quoted.

## Two modes

| | **CPU mode** (`--method cpu`) | **GPU mode** (`--method neural`) |
|---|---|---|
| Runs on | **any PC, no GPU needed** | Google Colab **T4/V100 GPU** (free) |
| Install | nothing (Python stdlib only) | `requirements-gpu.txt` |
| Speed | ~0.2 ms per row | ~1–3 s per row (batched) |
| Accuracy | good (grammar rules) | **highest** (neural word alignment) |

- **CPU mode** decides which chunks correspond using grammar rules, word
  lists, and a matching algorithm. It is fast and needs zero installation.
- **GPU mode** is a **hybrid**: a neural word aligner (AWESOME-align, built on
  the multilingual BERT model) reads the actual meaning of each sentence and
  produces high-quality word correspondences. Those correspondences then steer
  the same rule-based engine, which still produces the labels and the exact
  bullet format. The result: better chunk pairing, same clean output.
- **`--method auto`** uses the GPU when available and falls back to CPU
  otherwise — the same command runs on any machine.

## Project layout

```
en_fr_align/
├── run_align.py            # the main program (CLI)
├── align_core.py           # rule-based engine: tokenize → chunk → label → pair
├── lex_en.py / lex_fr.py   # English / French word-classification lexicons
├── gloss.py                # compact EN→FR glossary (helps the pairing)
├── neural.py               # GPU word-aligner wrapper + scoring glue
├── qc.py                   # 14-check quality-control suite
├── colab/EnFr_Align_Colab.ipynb   # the Colab notebook (same steps as Part B)
├── tests/                  # sample.csv + smoke tests (no GPU needed)
├── requirements.txt        # CPU mode: nothing required
└── requirements-gpu.txt    # GPU mode dependencies
```

## The alignment format in detail

Each row's `Alignment` cell is a list of bullet lines. Every line has the
exact structure:

```text
- **English phrase** [English label] **<-->** **French phrase** [French label]
```

Rules that are always respected:

- **Alignment is by meaning, not word order.** English and French may use
  different constructions, and the labels can differ (e.g. English
  `Verb Phrase / Passive` ↔ French `Verb Phrase / Active`).
- **Phrases may be different sizes** on each side (a noun ↔ a noun phrase).
- **Punctuation is aligned as its own unit**: `- **.** [Punctuation] **<-->** **.** [Punctuation]`.
- **Omitted material is explicit**: `- **,** [Punctuation] **<-->** **[omitted]** [Punctuation]`.
- **Nothing is invented**: the French text is used exactly as it appears in
  your CSV.
- Common labels: `Noun`, `Noun Phrase`, `Verb`, `Verb Phrase`, `Clause`,
  `Relative Clause`, `Adverbial Clause`, `Adverbial Phrase`,
  `Prepositional Phrase`, `Gerund Phrase / Subject`, `Infinitive Phrase / Subject`,
  `Predicate Phrase`, `Conditional Clause + Relative Clause`,
  `Conjunction + Verb Phrase`, `Punctuation`, and more.

---

# Part B — Full Colab (GPU) Tutorial

This tutorial processes your CSV in Google Colab with a free GPU and the
highest-accuracy neural mode. Plan for **~30–60 minutes** for a 175,000-row
file, or a couple of minutes for a few thousand rows.

## Step 0 — Open Google Colab

1. Go to **[colab.research.google.com](https://colab.research.google.com)**.
2. Sign in with your Google account (a free Gmail account is enough).
3. Click **File → New notebook**.
4. Give it a name (top left, e.g. `EnFr-Alignment`).

## Step 1 — Turn on the GPU

1. Click **Runtime → Change runtime type**.
2. In **Hardware accelerator**, select **T4 GPU**.
3. Click **Save**.

Check that the GPU is really active by pasting this in a cell and pressing
**Shift+Enter**:

```python
!nvidia-smi
```

You should see a table with `Tesla T4` (or similar) at the top. If you see
`command not found` or an error, repeat Step 1 and wait a few seconds.

## Step 2 — Install the dependencies

In a new cell, run:

```python
%pip install -q torch transformers numpy awesome-align==2.0.1
```

What happens here:

- `torch` = the deep-learning library that runs on the GPU. (Colab already
  has it; pip keeps the existing version if it satisfies the requirement.)
- `transformers` = the model library used by AWESOME-align.
- `awesome-align` = the neural word aligner. The framework can talk to three
  different versions of its Python API automatically.

**Verify the GPU is usable from Python** (new cell):

```python
import torch
print('CUDA available:', torch.cuda.is_available())
print('GPU name:', torch.cuda.get_device_name(0))
```

Expected output:

```text
CUDA available: True
GPU name: Tesla T4
```

If `CUDA available: False`, go back to Step 1 and pick the T4 GPU.

## Step 3 — Get the framework

### Option A — clone from GitHub (recommended)

First push the `en_fr_align` folder to GitHub (see the "Uploading to GitHub"
section of the README). Then, in a Colab cell:

```python
!git clone https://github.com/YOUR_USERNAME/en_fr_align.git
%cd en_fr_align
```

Replace `YOUR_USERNAME` with your actual GitHub username. The `%cd` makes all
following cells run inside the framework folder.

### Option B — upload the folder as a zip

1. On your computer, zip the `en_fr_align` folder.
2. In a Colab cell:

```python
from google.colab import files
up = files.upload()                 # choose en_fr_align.zip
!unzip -q {list(up.keys())[0]}
%cd en_fr_align
```

### Option C — use the provided notebook

You can also open `colab/EnFr_Align_Colab.ipynb` from the repo directly in
Colab (File → Upload notebook) — it contains the same steps already filled in.

## Step 4 — Upload your CSV

The first cell downloads the model, so let's get the CSV ready first. In a
new cell:

```python
from google.colab import files
print('Select your CSV (columns: English, French):')
uploaded = files.upload()
SRC = list(uploaded.keys())[0]
print('SRC =', SRC)
```

Click **Choose Files**, pick `French Full Dictionary - Sheet1 (2).csv` (or
your file), and wait for the upload to finish. `SRC` now holds the file name.

**Prefer Google Drive?** Mount Drive and set the path instead:

```python
from google.colab import drive
drive.mount('/content/drive')
SRC = '/content/drive/MyDrive/french/French Full Dictionary - Sheet1 (2).csv'
```

Drive is a good idea for very large files because the result can be written
straight to Drive and survives Colab runtime restarts.

## Step 5 — Quick test on a small slice (recommended)

Before running all 175,000 rows, verify everything works on the first 200:

```python
OUT = 'test_aligned.csv'
!python run_align.py --src "{SRC}" --out "{OUT}" --method neural --limit 200
```

What you should see:

1. The mBERT model (~680 MB) downloads once — this can take a few minutes.
   It is cached, so later runs are instant.
2. Progress lines every 2,048 rows (here just one chunk): `200 rows done`.
3. `Wrote 200 rows to ... in ...s`.

**Preview the result** (new cell):

```python
!python run_align.py --src "{SRC}" --out "{OUT}" --check
```

You should see `QC PASSED: 0 issues`. Then look at the actual alignment cells:

```python
import csv
with open(OUT, encoding='utf-8') as f:
    for i, row in enumerate(csv.reader(f)):
        if i >= 4:
            break
        print('--- row', i, '---')
        print('EN :', row[0][:80])
        print('FR :', row[1][:80])
        print(row[2].split('\n')[0])
        print(row[2].split('\n')[1] if '\n' in row[2] else '')
```

Each `row[2]` contains one bullet per alignment unit, separated by newlines.

## Step 6 — Run the full alignment

Now process the entire file:

```python
import os
OUT = os.path.splitext(os.path.basename(SRC))[0] + '_aligned.csv'
!python run_align.py --src "{SRC}" --out "{OUT}" --method neural --batch-size 32
```

Notes:

- The output file is written **incrementally** (every 2,048 rows), so if
  Colab disconnects mid-run, all rows already written are kept in `OUT`.
- Do not open `OUT` in Excel while the run is in progress.
- Expected time on a T4 for 175,621 rows: roughly 30–60 minutes.
- To make the run more robust for very large files, write the output to
  Drive (see Step 4) so it survives runtime restarts.

## Step 7 — Quality control

Run the built-in 14-check validation:

```python
!python run_align.py --src "{SRC}" --out "{OUT}" --check
```

What the report means:

| Line | What it verifies |
|---|---|
| `rows:` | the number of data rows matches the input |
| `units total:` / `avg per row:` | how many alignment bullets were produced (typically 5–25 per sentence) |
| `punctuation units:` | punctuation aligned as its own bullets |
| `[omitted] lines:` | places where material on one side has no counterpart |
| `issues: 0` | all checks passed |

The checks include: original EN/FR columns byte-identical, exactly one new
`Alignment` column, every bullet contains `<-->`, both sides present,
`[omitted]` handled, multiline cells correctly quoted, and no text spilled
into other columns.

## Step 8 — Download the result

```python
from google.colab import files
files.download(OUT)
```

Or copy it to Drive to keep it safe:

```python
!cp "{OUT}" /content/drive/MyDrive/
```

---

# Tips, tuning, and troubleshooting

## Keep the session alive

Colab disconnects idle sessions. For long runs, keep the browser tab active
and connected. If the runtime restarts, all variables are lost — re-run
Steps 2–4 (model download is cached, so Step 2 is fast) and re-run the
alignment. Rows already written to `OUT` before the disconnect are preserved.

## Test with `--limit` first

Always validate on a slice (`--limit 200` or `--limit 2000`) before the full
run. It catches upload/install problems in seconds.

## Common errors

| Symptom | Fix |
|---|---|
| `No module named 'torch'` | The runtime restarted or is CPU-only. Re-run Step 2 and check Step 1. |
| `CUDA available: False` | Runtime → Change runtime type → T4 GPU. |
| `awesome-align` fails to install | GPU mode needs it. CPU mode still works — use `--method auto` (falls back to rules). If it installed but the in-process API errors, the framework automatically tries the two other awesome-align APIs. |
| `CUDA out of memory` | Add `--batch-size 8` (or 16) to the run command. |
| Model download is slow | It is one-time (~680 MB) and cached; be patient, or pre-run with `--limit 10`. |
| Rows with no alignment produced | Extremely long rows (> 128 words) skip the neural layer by design and are aligned by rules; check the QC report for `issues`. |
| `ERROR: input file not found` | Check `SRC` — it must be the path inside the Colab VM (e.g. `/content/...`), not a local Windows path. |

## Tuning knobs (optional)

- **`--batch-size`** — bigger = faster but more GPU memory. Start at 32;
  lower to 8 if memory errors.
- **`--align-layer`** — which attention layer of mBERT is used for alignment
  (default `8`, best for most languages).
- **`--neural-weight`** — how strongly the neural evidence steers the chunk
  pairing (default `1.5`; try `0.5`–`3.0`).
- **`--limit N`** — process only the first `N` rows.
- **`--quiet`** — fewer progress messages.

## Running locally without any GPU

You do not need Colab at all for the CPU mode:

```bash
python run_align.py --src "French Full Dictionary - Sheet1 (2).csv" --method cpu
```

Same output format, same QC, no installation.

---

# Credits

The GPU layer uses **AWESOME-align** — Dou, Z. & Neubig, G. (2021),
*Word Alignment by Fine-tuning Embeddings on Parallel Corpora*, EACL 2021.
https://github.com/neulab/awesome-align
