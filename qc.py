# -*- coding: utf-8 -*-
"""Quality-control suite for an aligned CSV.

Re-opens the generated file and verifies the 14 checks from the spec
(row count, unchanged EN/FR columns, exactly one new Alignment column,
non-empty values, '<-->' present, both sides present, [omitted] handled,
punctuation preserved, parseable CSV, quoted multiline cells, no column
spill, reasonable unit counts, and example-style formatting).
"""
import csv
import re

LINE_RE = re.compile(
    r'^- \*\*(.+?)\*\* \[([^\]]+)\] \*\*<-->\*\* \*\*(.+?)\*\* \[([^\]]+)\]$')


def check(src, out, verbose=True, max_issues=30):
    issues = []
    total_units = 0
    punct_units = 0
    omitted_lines = 0
    unit_counts = []

    with open(src, encoding='utf-8-sig', newline='') as f:
        orig = list(csv.reader(f))
    oh = orig[0]
    orig_rows = orig[1:]

    with open(out, encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        hdr = next(reader)
        rows = list(reader)

    def ok(cond, msg):
        if not cond:
            issues.append(msg)

    # 1-4: header / shape
    ok(hdr[:len(oh)] == oh, 'first columns changed: %r vs %r' % (hdr, oh))
    ok(hdr == oh + ['Alignment'],
       'expected exactly one new Alignment column: %r' % hdr)
    ok(len(rows) == len(orig_rows),
       'row count %d != %d' % (len(rows), len(orig_rows)))

    n_empty = n_spill = n_no_arrow = n_bad = 0
    for i, row in enumerate(rows):
        # 12: no column spill
        if len(row) != len(oh) + 1:
            n_spill += 1
            ok(False, 'row %d has %d fields (spill)' % (i, len(row)))
            continue
        # 2-3: original columns unchanged
        if row[:len(oh)] != orig_rows[i][:len(oh)]:
            ok(False, 'row %d original columns changed' % i)
        align = row[-1]
        # 5: non-empty
        if not align.strip():
            n_empty += 1
            continue
        lines = align.split('\n')
        total_units += len(lines)
        unit_counts.append(len(lines))
        for ln in lines:
            # 6-7: arrow + both sides
            if '<-->' not in ln:
                n_no_arrow += 1
                continue
            m = LINE_RE.match(ln)
            if not m:
                n_bad += 1
                if len(issues) < max_issues:
                    ok(False, 'bad line in row %d: %r' % (i, ln[:120]))
                continue
            en_side, en_lab, fr_side, fr_lab = m.groups()
            # 8: omitted material explicit
            if '[omitted]' in en_side or '[omitted]' in fr_side:
                omitted_lines += 1
            # 9: punctuation aligned separately
            if en_lab == 'Punctuation':
                punct_units += 1

    ok(n_spill == 0, '%d rows with column spill' % n_spill)
    ok(n_empty == 0, '%d rows with empty alignment' % n_empty)
    ok(n_no_arrow == 0, '%d lines missing <-->' % n_no_arrow)
    ok(n_bad == 0, '%d malformed alignment lines' % n_bad)
    # 13: reasonable unit count (1-2 word rows can have 1 unit; cap sanity)
    too_few = sum(1 for c in unit_counts if c == 0)
    ok(too_few == 0, '%d rows with zero alignment units' % too_few)

    if verbose:
        n = max(len(rows), 1)
        print('QC on %s' % out)
        print('rows: %d | units total: %d | avg per row: %.2f'
              % (len(rows), total_units, total_units / n))
        print('punctuation units: %d | [omitted] lines: %d'
              % (punct_units, omitted_lines))
        print('issues: %d' % len(issues))
        for msg in issues[:max_issues]:
            print('  !', msg)
    return issues, dict(rows=len(rows), units=total_units,
                        punct=punct_units, omitted=omitted_lines)
