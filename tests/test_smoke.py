# -*- coding: utf-8 -*-
"""Lightweight smoke tests — no GPU, no model download, a few seconds.

Covers:
  1. full CPU CSV pipeline on tests/sample.csv + QC suite passes;
  2. the hybrid glue (chunk-score matrix from word pairs -> align_chunked)
     exercised with a synthetic pair set so the GPU path is validated
     structurally even on machines without CUDA.
"""
import csv
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import run_align            # noqa: E402
import qc                   # noqa: E402
from align_core import (tokenize, classify_en, classify_fr, chunk_en,  # noqa: E402
                        chunk_fr, align_chunked)
from neural import chunk_scores, word_tokens  # noqa: E402

LINE_RE = re.compile(
    r'^- \*\*(.+?)\*\* \[([^\]]+)\] \*\*<-->\*\* \*\*(.+?)\*\* \[([^\]]+)\]$')


def _rows(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.reader(f))


def test_cpu_pipeline():
    src = os.path.join(HERE, 'sample.csv')
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, 'sample_aligned.csv')
        run_align.run(src, out, method='cpu')
        issues, stats = qc.check(src, out, verbose=False)
        assert issues == [], issues[:3]
        rows = _rows(out)
        orig = _rows(src)
        assert len(rows) == len(orig)
        assert rows[0] == orig[0] + ['Alignment']
        for r in rows[1:]:
            assert len(r) == 3, 'column spill'
            assert r[0] == orig[rows.index(r)][0]
            assert r[1] == orig[rows.index(r)][1]
            assert r[2].strip(), 'empty alignment'
            for ln in r[2].split('\n'):
                assert LINE_RE.match(ln), 'malformed: %r' % ln
        assert stats['units'] >= len(rows) - 1
        print('test_cpu_pipeline: OK (%d rows, %d units)' % (len(rows) - 1,
                                                             stats['units']))


def test_hybrid_glue():
    """align_chunked with a neural chunk-score matrix must produce valid output."""
    en = "The book that you gave me is interesting."
    fr = "Le livre que tu m'as donné est intéressant."
    et = tokenize(en)
    ft = tokenize(fr)
    for t in et:
        if t['kind'] == 'word':
            t['cls'] = classify_en(t['text'])
    for t in ft:
        if t['kind'] == 'word':
            t['cls'] = classify_fr(t['text'])
    en_chunks, fr_chunks = chunk_en(et), chunk_fr(ft)
    # synthetic neural pairs: link each EN word to the same-position FR word
    ew, fw = word_tokens(et), word_tokens(ft)
    pairs = {(i, min(i, len(fw) - 1)) for i in range(len(ew))}
    mat = chunk_scores(et, ft, en_chunks, fr_chunks, pairs)
    align = align_chunked(en, fr, et, ft, en_chunks, fr_chunks,
                          neural=mat, wn=1.5)
    assert align.strip()
    for ln in align.split('\n'):
        assert LINE_RE.match(ln), 'malformed: %r' % ln
    # the same row must also work without any neural matrix
    align2 = align_chunked(en, fr, et, ft, en_chunks, fr_chunks)
    assert align2.strip()
    print('test_hybrid_glue: OK (neural=%d chunks, matrix=%dx%d)'
          % (len(en_chunks), len(mat), len(mat[0]) if mat else 0))


if __name__ == '__main__':
    test_cpu_pipeline()
    test_hybrid_glue()
    print('All smoke tests passed.')
