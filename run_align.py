# -*- coding: utf-8 -*-
"""Command-line driver for EN<->FR phrase alignment.

Examples
--------
Pure CPU (runs on any PC, no GPU, no extra dependencies)::

    python run_align.py --src data.csv --out data_aligned.csv --method cpu

GPU-hybrid (best accuracy; run in Colab with a T4/V100 GPU)::

    python run_align.py --src data.csv --out data_aligned.csv --method neural

Automatic (use GPU when available, else CPU)::

    python run_align.py --src data.csv --out data_aligned.csv

Validate a generated file::

    python run_align.py --src data.csv --out data_aligned.csv --check

The input CSV must have at least two columns: English, French.  A third
`Alignment` column is appended; original columns are never modified.
"""
import argparse
import csv
import os
import sys
import time

from align_core import (tokenize, classify_en, classify_fr, chunk_en,
                        chunk_fr, align_chunked, align_pair)
from neural import NeuralAligner, chunk_scores, word_tokens
import qc


def _prepare(toks_en, toks_fr):
    """Classify + chunk both sides; return chunks."""
    for t in toks_en:
        if t['kind'] == 'word':
            t['cls'] = classify_en(t['text'])
    for t in toks_fr:
        if t['kind'] == 'word':
            t['cls'] = classify_fr(t['text'])
    return chunk_en(toks_en), chunk_fr(toks_fr)


def run(src, out, method='auto', limit=None, file_chunk=2048, batch_size=32,
        align_layer=8, wn=1.5, model_name='bert-base-multilingual-cased',
        no_cuda=False, verbose=True):
    t0 = time.time()

    neural = None
    if method in ('auto', 'neural'):
        neural = NeuralAligner(model_name=model_name, align_layer=align_layer,
                               batch_size=batch_size, no_cuda=no_cuda,
                               verbose=verbose)
        if not neural.available:
            if method == 'neural':
                sys.exit('ERROR: %s' % neural.err)
            if verbose:
                print('WARNING: %s -> falling back to CPU mode' % neural.err,
                      flush=True)
            neural = None

    n_in = 0
    with open(src, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        if len(header) < 2:
            sys.exit('ERROR: input CSV must have at least 2 columns, got %r'
                     % header)
        with open(out, 'w', encoding='utf-8', newline='') as g:
            writer = csv.writer(g, lineterminator='\r\n')
            writer.writerow(header + ['Alignment'])

            if neural is None:
                # ---------------- pure CPU streaming path ----------------
                for i, row in enumerate(reader):
                    if limit is not None and i >= limit:
                        break
                    if len(row) < 2:
                        sys.exit('ERROR: row %d has %d fields, expected 2'
                                 % (i + 1, len(row)))
                    en, fr = row[0], row[1]
                    writer.writerow([en, fr, align_pair(en, fr)])
                    n_in += 1
                    if i % 25000 == 0 and i:
                        print('  %d rows done (%.1fs)' % (i, time.time() - t0),
                              flush=True)
            else:
                # ---------------- GPU-hybrid chunked path ----------------
                pend_en, pend_fr, pend_toks, pend_rows = [], [], [], []
                i = 0
                for row in reader:
                    if limit is not None and i >= limit:
                        break
                    if len(row) < 2:
                        sys.exit('ERROR: row %d has %d fields, expected 2'
                                 % (i + 1, len(row)))
                    en, fr = row[0], row[1]
                    pend_rows.append((en, fr))
                    et = tokenize(en)
                    ft = tokenize(fr)
                    pend_toks.append((et, ft))
                    pend_en.append([t['text'] for t in word_tokens(et)])
                    pend_fr.append([t['text'] for t in word_tokens(ft)])
                    i += 1
                    if len(pend_rows) >= file_chunk:
                        n_in += _flush_neural(writer, pend_rows, pend_toks,
                                              pend_en, pend_fr, neural, wn)
                        print('  %d rows done (%.1fs)'
                              % (n_in, time.time() - t0), flush=True)
                        pend_en, pend_fr, pend_toks, pend_rows = [], [], [], []
                if pend_rows:
                    n_in += _flush_neural(writer, pend_rows, pend_toks,
                                          pend_en, pend_fr, neural, wn)

    print('Wrote %d rows to %s in %.1fs' % (n_in, out, time.time() - t0))
    return out


def _flush_neural(writer, rows, toks, en_w, fr_w, neural, wn):
    """Word-align one file-chunk on the GPU and write its rows."""
    pair_sets = neural.align_batch(en_w, fr_w)
    for k, (en, fr) in enumerate(rows):
        et, ft = toks[k]
        en_chunks, fr_chunks = _prepare(et, ft)
        mat = chunk_scores(et, ft, en_chunks, fr_chunks, pair_sets[k])
        align = align_chunked(en, fr, et, ft, en_chunks, fr_chunks,
                              neural=mat, wn=wn)
        writer.writerow([en, fr, align])
    return len(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='EN<->FR phrase alignment with optional GPU acceleration')
    ap.add_argument('--src', required=True, help='input CSV (EN, FR columns)')
    ap.add_argument('--out', default=None,
                    help='output CSV (default: <src>_aligned.csv)')
    ap.add_argument('--method', choices=('auto', 'cpu', 'neural'),
                    default='auto',
                    help='cpu = rule-based only (no GPU); neural = GPU word '
                         'alignment + rule-based labels; auto = neural if '
                         'available')
    ap.add_argument('--limit', type=int, default=None,
                    help='only process the first N data rows')
    ap.add_argument('--file-chunk', type=int, default=2048,
                    help='rows held in memory per chunk in neural mode')
    ap.add_argument('--batch-size', type=int, default=32,
                    help='neural model batch size')
    ap.add_argument('--align-layer', type=int, default=8,
                    help='attention layer used for word alignment (mBERT)')
    ap.add_argument('--neural-weight', type=float, default=1.5,
                    help='how strongly the neural matrix steers chunk pairing')
    ap.add_argument('--model-name',
                    default='bert-base-multilingual-cased',
                    help='awesome-align checkpoint (HF model name or path)')
    ap.add_argument('--no-cuda', action='store_true',
                    help='force CPU even if a GPU is present')
    ap.add_argument('--check', action='store_true',
                    help='run the QC suite on --out and exit')
    ap.add_argument('--quiet', action='store_true', help='less output')
    args = ap.parse_args(argv)

    src = os.path.abspath(args.src)
    if not os.path.exists(src):
        sys.exit('ERROR: input file not found: %s' % src)
    out = args.out or os.path.splitext(src)[0] + '_aligned.csv'
    out = os.path.abspath(out)

    if args.check:
        issues, stats = qc.check(src, out, verbose=not args.quiet)
        print('QC %s: %d issues' % ('PASSED' if not issues else 'FAILED',
                                    len(issues)))
        sys.exit(1 if issues else 0)

    run(src, out, method=args.method, limit=args.limit,
        file_chunk=args.file_chunk, batch_size=args.batch_size,
        align_layer=args.align_layer, wn=args.neural_weight,
        model_name=args.model_name, no_cuda=args.no_cuda,
        verbose=not args.quiet)
    issues, _ = qc.check(src, out, verbose=not args.quiet)
    sys.exit(1 if issues else 0)


if __name__ == '__main__':
    main()
