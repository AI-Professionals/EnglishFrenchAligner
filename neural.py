# -*- coding: utf-8 -*-
"""Optional GPU-accelerated word-alignment layer.

Uses AWESOME-align (a neural word aligner built on multilingual BERT /
XLM-R) to get high-quality word correspondences between the English and
French sides of each row.  Those word pairs are converted into a chunk-level
score matrix which is fed into the rule-based dynamic program, so the
*chunk pairing* follows the neural model while the grammar labels and the
required bullet format stay rule-based.

Hardware:
  - Designed for a CUDA GPU (the free T4 on Google Colab is plenty).
  - `NeuralAligner.available` is False if torch / awesome-align / CUDA are
    missing, in which case the pipeline silently falls back to the pure
    rule-based engine (stdlib only, runs on any PC without a GPU).
"""

import subprocess
import tempfile
import os

# mBERT has a 512-subword limit; rows longer than this skip the neural layer
# and are handled entirely by the rule-based engine.
MAX_WORDS = 128

_MISSING_MSG = (
    "neural aligner unavailable: torch/awesome-align not installed or no GPU. "
    "Install requirements-gpu.txt and run in a GPU runtime (see README).")


class NeuralAligner:
    """Word-aligner wrapper.

    Backends, tried in order:
      1. in-process ``AlignExtractor`` (PyPI ``awesome-align`` 2.0.1);
      2. ``awesome_align.aligner.Aligner`` (newer master-branch API);
      3. the ``awesome-align`` CLI via subprocess (works with any version).
    """

    def __init__(self, model_name='bert-base-multilingual-cased',
                 align_layer=8, softmax=True, threshold=1e-3,
                 batch_size=32, device='auto', no_cuda=False, verbose=False):
        self.model_name = model_name
        self.align_layer = align_layer
        self.softmax = softmax
        self.threshold = threshold
        self.batch_size = batch_size
        self.verbose = verbose
        self.available = False
        self.api = None
        self.err = ''
        self._backend = None
        self._init_backend(device=device, no_cuda=no_cuda)

    # ------------------------------------------------------------------ setup
    def _init_backend(self, device='auto', no_cuda=False):
        try:
            import torch
            self.torch = torch
            if device == 'auto':
                device = 'cuda' if (torch.cuda.is_available() and not no_cuda) \
                    else 'cpu'
            self.device = device
        except Exception as e:  # no torch at all
            self.err = 'torch not installed: %s' % e
            return
        if not self._try_extractor_api():
            if not self._try_aligner_class():
                if not self._try_cli():
                    self.err = self.err or _MISSING_MSG

    def _try_extractor_api(self):
        """PyPI awesome-align 2.0.1: AlignExtractor.extract_wordpairs."""
        try:
            from awesome_align import model_utils, alignment
            model = model_utils.BertForTokenClassification.from_pretrained(
                self.model_name)
            tokenizer = model_utils.BertTokenizer.from_pretrained(
                self.model_name)
            if self.device.startswith('cuda'):
                model = model.cuda()
            self._backend = alignment.AlignExtractor(
                model, tokenizer, align_layer=self.align_layer,
                use_softmax=self.softmax)
            self.api = 'extractor'
            self.available = True
            return True
        except Exception as e:
            self.err = 'AlignExtractor backend failed: %s' % e
            return False

    def _try_aligner_class(self):
        """Newer master-branch API: awesome_align.aligner.Aligner."""
        try:
            from awesome_align.aligner import Aligner
            self._backend = Aligner(
                model_name_or_path=self.model_name,
                align_layer=self.align_layer,
                batch_size=self.batch_size,
                no_cuda=not self.device.startswith('cuda'))
            self.api = 'aligner'
            self.available = True
            return True
        except Exception as e:
            self.err = 'Aligner backend failed: %s' % e
            return False

    def _try_cli(self):
        """Any version: run the awesome-align CLI over a temp pair file."""
        try:
            import shutil
            if shutil.which('awesome-align'):
                self.api = 'cli'
                self.available = True
                return True
            self.err = 'awesome-align CLI not found on PATH'
        except Exception as e:
            self.err = 'CLI probe failed: %s' % e
        return False

    # --------------------------------------------------------------- inference
    def align_batch(self, en_word_lists, fr_word_lists):
        """Word-align a batch of sentences.

        Args:
            en_word_lists: list of lists of EN word strings.
            fr_word_lists: list of lists of FR word strings (same order/length).

        Returns:
            list (same length) of sets of (i, j) pairs; i indexes the EN word
            list, j the FR word list.  Rows that are too long, empty, or that
            fail on the GPU side come back as empty sets (rule-based fallback).
        """
        n = len(en_word_lists)
        out = [set() for _ in range(n)]
        if not self.available:
            return out
        ok_idx, src, tgt = [], [], []
        for k in range(n):
            if not en_word_lists[k] or not fr_word_lists[k]:
                continue
            if (len(en_word_lists[k]) > MAX_WORDS or
                    len(fr_word_lists[k]) > MAX_WORDS):
                continue
            ok_idx.append(k)
            src.append(en_word_lists[k])
            tgt.append(fr_word_lists[k])
        if not ok_idx:
            return out
        try:
            if self.api == 'extractor':
                res = self._extract(src, tgt)
            elif self.api == 'aligner':
                res = self._aligner_run(src, tgt)
            else:
                res = self._cli_run(src, tgt)
            for k, pairs in zip(ok_idx, res):
                out[k] = pairs
        except Exception as e:
            if self.verbose:
                print('neural batch failed (%s); falling back per row' % e,
                      flush=True)
            # per-row retry so one bad row cannot sink the whole batch
            for k in ok_idx:
                try:
                    if self.api == 'extractor':
                        res = self._extract([src[ok_idx.index(k)]],
                                            [tgt[ok_idx.index(k)]])
                    elif self.api == 'aligner':
                        res = self._aligner_run([src[ok_idx.index(k)]],
                                                [tgt[ok_idx.index(k)]])
                    else:
                        res = self._cli_run([src[ok_idx.index(k)]],
                                            [tgt[ok_idx.index(k)]])
                    out[k] = res[0]
                except Exception:
                    pass
        return out

    # ---------------------------------------------------------- backends
    def _extract(self, src, tgt):
        raw = self._backend.extract_wordpairs(src, tgt, self.threshold)
        return [self._normalize(r) for r in raw]

    def _aligner_run(self, src, tgt):
        """New Aligner API: write temp files, read back 'i-j' pair lines."""
        lines = [' '.join(s) + ' ||| ' + ' '.join(t)
                 for s, t in zip(src, tgt)]
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False,
                                         encoding='utf-8') as fin:
            fin.write('\n'.join(lines))
            data = fin.name
        outp = data + '.out'
        try:
            self._backend.align(data_file=data, output_file=outp)
            return self._parse_pair_file(outp, len(src))
        finally:
            for p in (data, outp):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def _cli_run(self, src, tgt):
        lines = [' '.join(s) + ' ||| ' + ' '.join(t)
                 for s, t in zip(src, tgt)]
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False,
                                         encoding='utf-8') as fin:
            fin.write('\n'.join(lines))
            data = fin.name
        outp = data + '.out'
        cmd = ['awesome-align',
               '--output_file', outp,
               '--model_name_or_path', self.model_name,
               '--data_file', data,
               '--extraction', 'softmax' if self.softmax else 'entmax15',
               '--align_layer', str(self.align_layer),
               '--softmax_threshold', str(self.threshold),
               '--batch_size', str(self.batch_size)]
        if not self.device.startswith('cuda'):
            cmd.append('--no_cuda')
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return self._parse_pair_file(outp, len(src))
        finally:
            for p in (data, outp):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    @staticmethod
    def _normalize(sent_result):
        """Accept list-of-triples or numpy rows; return set of (i, j)."""
        pairs = set()
        for row in sent_result:
            if row is None:
                continue
            try:
                i, j, sc = int(row[0]), int(row[1]), float(row[2])
            except (TypeError, ValueError, IndexError):
                continue
            pairs.add((i, j))
        return pairs

    @staticmethod
    def _parse_pair_file(path, n_rows):
        out = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                pairs = set()
                for tok in line.strip().split():
                    if '-' in tok:
                        try:
                            a, b = tok.split('-')
                            pairs.add((int(a), int(b)))
                        except ValueError:
                            pass
                out.append(pairs)
        while len(out) < n_rows:
            out.append(set())
        return out[:n_rows]


# ---------------------------------------------------------------------------
# glue: neural word pairs -> chunk-level score matrix for the rule-based DP
# ---------------------------------------------------------------------------
def word_tokens(toks):
    """Word tokens (in order) from a tokenize() output list."""
    return [t for t in toks if t['kind'] == 'word']


def word_lists_from_texts(texts, tokenizer):
    """[(en_text, fr_text)] -> (en_word_lists, fr_word_lists, en_toks, fr_toks)."""
    en_w, fr_w, en_t, fr_t = [], [], [], []
    for en, fr in texts:
        et = tokenizer(en)
        ft = tokenizer(fr)
        en_t.append(et)
        fr_t.append(ft)
        en_w.append([t['text'] for t in word_tokens(et)])
        fr_w.append([t['text'] for t in word_tokens(ft)])
    return en_w, fr_w, en_t, fr_t


def chunk_scores(en_toks, fr_toks, en_chunks, fr_chunks, pairs):
    """E x F float matrix: how many neural word pairs link chunk i to chunk j.

    en_chunks/fr_chunks come from chunk_en()/chunk_fr() (each chunk is a
    (lead, [token dicts]) pair); the token dicts are the same objects as in
    en_toks/fr_toks, so we index words by object identity.
    """
    E, F = len(en_chunks), len(fr_chunks)
    score = [[0.0] * F for _ in range(E)]
    if not pairs:
        return score
    en_w = word_tokens(en_toks)
    fr_w = word_tokens(fr_toks)
    en_pos = {id(t): k for k, t in enumerate(en_w)}
    fr_pos = {id(t): k for k, t in enumerate(fr_w)}
    # word index -> chunk index
    en_of = {}
    for ci, (_, toks) in enumerate(en_chunks):
        for t in toks:
            if t['kind'] == 'word':
                en_of[en_pos[id(t)]] = ci
    fr_of = {}
    for cj, (_, toks) in enumerate(fr_chunks):
        for t in toks:
            if t['kind'] == 'word':
                fr_of[fr_pos[id(t)]] = cj
    for (a, b) in pairs:
        if a in en_of and b in fr_of:
            score[en_of[a]][fr_of[b]] += 1.0
    return score
