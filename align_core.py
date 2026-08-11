# -*- coding: utf-8 -*-
"""Core EN<->FR alignment engine.

Pure Python + regex; no ML, no GPU.  Pipeline per row:
  tokenize -> classify -> chunk -> label -> DP-align chunks -> align
  punctuation -> interleave -> format bullets.
"""
import re

from lex_en import (ARTICLES, DETS, PREPS, CONJ, SUBORD, REL, INF, PRONS,
                    PRONAUX, AUX, AUXNEG, NEG, ADVS, VERBS, NOUNS, ADJS,
                    INTERJ, MW_EN)
from lex_fr import (ARTICLES as FA, PREPS as FP, CONJ as FC, SUBORD as FS,
                    REL as FR_, PRONS as FPR, AUX as FAUX, NEG as FNEG,
                    REFL, ADVS as FADV, VERBS as FVERB, ADJS as FADJ,
                    INTERJ as FINTERJ, INTER_FR, MW_FR, FR_PREFIX, INF_END,
                    INF_IRREG, DETS_FR, NOUNS_FR)
from gloss import GLOSS

# ---------------------------------------------------------------------------
# punctuation classes
FINAL_PUNCT = set('.!?…‽؟')
INTERNAL_PUNCT = set(',;:()[]{}«»\"\'`-—–/\\*&%#@+=|~^<>')

BOUNDARY = {'article', 'det', 'quant', 'prep', 'inf', 'conj', 'subord',
            'rel', 'int', 'idiom', 'interj', 'expletive', 'num'}
NO_SPLIT_PREV = {'pron', 'pronaux', 'rel', 'subord', 'int', 'conj', 'aux',
                 'auxneg', 'adv', 'neg', 'refl'}
SUBJECT_EN = {'i', 'he', 'she', 'it', 'we', 'they'}
SUBJECT_REL = {'i', 'you', 'he', 'she', 'it', 'we', 'they', 'one'}
SUBJECT_FR = {'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles',
              'ce', 'ça', 'cela', 'celui', 'celle', 'ceux', 'celles'}

BE_FORMS = {'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            "i'm", "you're", "he's", "she's", "it's", "we're", "they're",
            "there's", "here's", "that's", "what's", "who's"}
IRREG_PP = set("""told seen given gone done made found known taken brought
thought bought caught taught built sent spent felt kept left lost met paid
put read said sold stood understood won written spoken broken chosen driven
eaten fallen forgotten gotten hidden held led meant run sung swum woken worn
thrown drawn grown blown flown shown heard laid lain risen shaken shot shut
sat slept slid spun split spread sprung stuck stung struck swung torn upset
wept wrung become come begun bitten ridden fought knelt swung taught""".split())
IRREG_PP.discard('wound')
GERUND_EXC = {'morning', 'evening', 'thing', 'king', 'ring', 'spring',
              'swing', 'wing', 'sting', 'building', 'clothing', 'drawing',
              'meaning', 'meeting', 'painting', 'reading', 'seating',
              'setting', 'shopping', 'feeling', 'ending', 'lighting',
              'flooring', 'ceiling', 'wedding', 'housing', 'packaging',
              'parking', 'plumbing', 'roofing', 'siding', 'wiring',
              'staffing', 'wording', 'writing', 'living', 'dying', 'being'}

WS = r"\s\xa0\u2009\u202f"
TOK_RE = re.compile(
    r"(?P<num>[0-9]+(?:[.,][0-9]+)*)"
    r"|(?P<word>[\w]+(?:['\u2019\-][\w]+)*)"
    r"|(?P<punct>[^\w" + WS + r"])"
)

# ---------------------------------------------------------------------------
# classification

def _derive_3sg(v):
    if v == 'be':
        return 'is'
    if v == 'do':
        return 'does'
    if v == 'have':
        return 'has'
    if v == 'go':
        return 'goes'
    if v == 'say':
        return 'says'
    if v.endswith('y'):
        return v[:-1] + 'ies'
    if v.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return v + 'es'
    return v + 's'


VERBS3 = {_derive_3sg(v) for v in VERBS}

IRREG_PT = set("""was were did had said made went got took came saw knew thought told gave
found felt left met paid ran sat stood lost kept began became brought wrote led
understood spoke read spent grew won bought taught caught built sent fell cut ate
drank slept woke sang lay hid stole threw hit shut broke flew drove rode swam dove
slid tore wore chose swore fought hurt misled forgot stuck clung held shot arose
froze burst thrust bit knelt bent rose drew reset heard meant hung dug swung clung
sped crept dealt leapt smelt spilt knelt leant dreamt shone shone swore swore""".split())


def classify_en(text):
    t = text.lower()
    if t in ('what', 'when', 'where', 'why', 'how'):
        return 'int'
    if t in REL:
        return 'rel'
    if t in ARTICLES:
        return 'article'
    if t in DETS:
        return 'det'
    if t == 'to':
        return 'inf'
    if t in PREPS:
        return 'prep'
    if t in CONJ:
        return 'conj'
    if t in SUBORD:
        return 'subord'
    if t in PRONAUX:
        return 'pronaux'
    if t in AUXNEG:
        return 'auxneg'
    if t in AUX:
        return 'aux'
    if t in PRONS:
        return 'pron'
    if t in NEG:
        return 'neg'
    if t in ADVS:
        return 'adv'
    if t in INTERJ:
        return 'interj'
    if t in VERBS or t in VERBS3 or t in IRREG_PT:
        return 'verb'
    if t in NOUNS:
        return 'noun'
    if t in ADJS:
        return 'adj'
    if t.isdigit():
        return 'num'
    if t.endswith('ing') and len(t) > 4 and t not in GERUND_EXC:
        return 'gerund'
    if t.endswith('ed') and len(t) > 4 and t not in ('red', 'led', 'fed'):
        return 'verb'
    if t.endswith('ly') and len(t) > 4:
        return 'adv'
    if t.endswith(('tion', 'ness', 'ment', 'ity', 'ance', 'ence', 'hood',
                   'ship', 'ism', 'dom', 'th', 'er', 'or', 'ist')):
        return 'noun'
    if t.endswith(('ful', 'ous', 'ive', 'able', 'ible', 'less', 'al', 'ic',
                   'ish')):
        return 'adj'
    return 'other'


def classify_fr(text):
    t = text.lower()
    if t in FINTERJ:
        return 'interj'
    if t in INTER_FR:
        return 'int'
    if t in FADV:
        return 'adv'
    if t in FNEG:
        return 'neg'
    if t in REFL:
        return 'refl'
    if t in FAUX:
        return 'aux'
    if t in FVERB:
        return 'verb'
    if t in FADJ:
        return 'adj'
    if t in FPR:
        return 'pron'
    if t in DETS_FR:
        return 'det'
    if t in NOUNS_FR:
        return 'noun'
    if t in FR_:
        return 'rel'
    if t in FS:
        return 'subord'
    if t in FC:
        return 'conj'
    if t in FP:
        return 'prep'
    if t in FA:
        return 'article'
    if t.isdigit():
        return 'num'
    for pref, cls in FR_PREFIX:
        if t.startswith(pref):
            return cls
    if t.endswith(INF_END) and len(t) > 3 and t not in ('mer', 'fer', 'hiver', 'ver'):
        return 'verb'
    if t in INF_IRREG:
        return 'verb'
    if t.endswith(('ez', 'ons', 'ent', 'ais', 'ait', 'aient', 'ions', 'iez')) and len(t) > 3:
        return 'verb'
    if t.endswith(('eux', 'euse', 'ive', 'ique', 'able', 'ible', 'al', 'el',
                   'aire', 'ois', 'ais', 'ain', 'ien', 'iste', 'atif',
                   'itive', 'ante', 'ente', 'eille')) and len(t) > 4:
        return 'adj'
    if t.endswith('s') and len(t) > 4:
        return 'noun'
    return 'other'


def mw_lookup(words, i, mw, mw_max):
    n = len(words)
    for L in range(min(mw_max, n - i), 1, -1):
        key = tuple(w['text'].lower().replace('\u2019', "'") for w in words[i:i + L])
        if key in mw:
            return L, mw[key]
    return 1, None


# ---------------------------------------------------------------------------
# tokenizer

def tokenize(s):
    toks = []
    for m in TOK_RE.finditer(s):
        kind = 'word' if (m.lastgroup == 'word' or m.lastgroup == 'num') else 'punct'
        toks.append({'start': m.start(), 'end': m.end(),
                     'text': m.group(0), 'kind': kind})
    # merge runs of the same punctuation character (e.g. '...', '!!')
    merged = []
    for t in toks:
        if (t['kind'] == 'punct' and merged and merged[-1]['kind'] == 'punct'
                and len(t['text']) == 1 and merged[-1]['text'][-1] == t['text']):
            prev = merged[-1]
            prev['end'] = t['end']
            prev['text'] = prev['text'] + t['text']
        else:
            merged.append(t)
    return merged


def split_punct(toks):
    finals, internals = [], []
    for t in toks:
        if t['kind'] == 'punct':
            ch = t['text'][-1]
            if ch in FINAL_PUNCT:
                finals.append(t)
            else:
                internals.append(t)
    return finals, internals


def word_indices(toks):
    return [i for i, t in enumerate(toks) if t['kind'] == 'word']


# ---------------------------------------------------------------------------
# chunking

DET_AFTER_VERB = {'article', 'det', 'quant'}


def _chunk(words, punct_before, mw, mw_max, no_split, boundary, subject):
    """Split a word-token list into chunks; each chunk is (lead_class, toks)."""
    n = len(words)
    chunks = []
    start = 0
    prev_boundary = False
    cur_lead = None
    i = 0
    while i < n:
        mlen, mcls = mw_lookup(words, i, mw, mw_max)
        if mlen > 1:
            cls = mcls
        else:
            cls = words[i]['cls']
        force = punct_before[i]
        prev = words[i - 1]['cls'] if i > 0 else None
        starts = False
        if i == start:
            starts = True
        elif force:
            starts = True
        elif prev_boundary:
            starts = False
        elif cls in boundary:
            if cls in DET_AFTER_VERB and prev in ('verb', 'aux', 'auxneg'):
                starts = False          # keep the noun phrase glued to the verb
            else:
                starts = True
        elif cls in ('aux', 'auxneg', 'verb'):
            starts = not (prev in no_split)
        elif cls == 'pron':
            starts = prev in ('verb', 'aux', 'auxneg') \
                and words[i]['text'].lower() in subject
        else:
            starts = False
        if starts and i > start:
            chunks.append((cur_lead, words[start:i]))
            start = i
        if starts:
            cur_lead = cls
        prev_boundary = cls in boundary
        i += mlen
    chunks.append((cur_lead, words[start:n]))
    return chunks


def _punct_before(words, toks, n):
    punct_before = [False] * n
    wi = 0
    for t in toks:
        if t['kind'] == 'word':
            wi += 1
        elif 0 < wi < n:
            punct_before[wi] = True
    return punct_before


def chunk_en(toks):
    words = [t for t in toks if t['kind'] == 'word']
    if not words:
        return []
    pb = _punct_before(words, toks, len(words))
    return _chunk(words, pb, MW_EN, 4, NO_SPLIT_PREV, BOUNDARY, SUBJECT_EN)


def chunk_fr(toks):
    words = [t for t in toks if t['kind'] == 'word']
    if not words:
        return []
    pb = _punct_before(words, toks, len(words))
    return _chunk(words, pb, MW_FR, 4, NO_SPLIT_PREV, BOUNDARY, SUBJECT_FR)


# ---------------------------------------------------------------------------
# helpers for labels

def has_verb(toks):
    return any(t['cls'] in ('verb', 'aux', 'auxneg') for t in toks)


def has_rel_en(toks):
    for t in toks:
        if t['cls'] in ('rel', 'int'):
            return True
    for i in range(len(toks) - 1):
        if toks[i]['cls'] in ('noun', 'other') and \
                toks[i + 1]['text'].lower() in SUBJECT_REL:
            return True
    return False


def has_rel_fr(toks):
    return any(t['cls'] == 'rel' for t in toks)


def has_participle(toks):
    for t in toks:
        low = t['text'].lower()
        if low in IRREG_PP:
            return True
        if low.endswith('ed') and len(low) > 4 and low not in ('red', 'led', 'fed'):
            return True
    return False


def has_passive(toks):
    be = any(t['text'].lower() in BE_FORMS for t in toks)
    pp = has_participle(toks)
    return be and pp


def is_fr_infinitive(text):
    t = text.lower()
    if t in INF_IRREG:
        return True
    if t.endswith(INF_END) and len(t) > 3 and t not in ('mer', 'fer', 'hiver', 'ver'):
        return True
    return False


def is_en_verbish(tok):
    if tok['cls'] in ('verb', 'aux'):
        return True
    return tok['text'].lower() in VERBS


# ---------------------------------------------------------------------------
# labels

def label_en(toks, sentence_initial=False, lead=None):
    n = len(toks)
    if n == 0:
        return 'Phrase'
    low = toks[0]['text'].lower()
    cls0 = lead or toks[0]['cls']
    if low in INTERJ or cls0 == 'interj':
        return 'Interjection'
    if cls0 == 'num':
        return 'Numeral' if n == 1 else 'Noun Phrase'
    if cls0 == 'conj':
        rest = label_en(toks[1:], False) if n > 1 else 'Phrase'
        return 'Conjunction + ' + rest
    if cls0 == 'idiom':
        return 'Adverbial Phrase'
    if cls0 == 'expletive':
        return 'Clause'
    if cls0 in ('prep', 'inf'):
        if low == 'to' and n > 1 and is_en_verbish(toks[1]):
            return 'Infinitive Phrase'
        if low in ('since', 'after', 'before', 'until', 'once') and has_verb(toks):
            return 'Adverbial Clause'
        base = 'Prepositional Phrase'
        if has_rel_en(toks):
            base += ' + Relative Clause'
        elif has_participle(toks):
            base += ' + Participle'
        return base
    if cls0 in ('article', 'det', 'quant'):
        base = 'Noun Phrase'
        if has_rel_en(toks):
            base += ' + Relative Clause'
        return base
    if cls0 == 'rel':
        if sentence_initial and low in ('who', 'whom', 'whose', 'which'):
            return 'Interrogative Clause'
        if sentence_initial and low == 'that':
            return 'Clause'
        if low == 'that' and n > 1 and toks[1]['cls'] in ('noun', 'adj', 'other'):
            return 'Noun Phrase'
        return 'Relative Clause'
    if cls0 == 'int':
        if sentence_initial:
            return 'Interrogative Clause'
        if low in ('when', 'where', 'why', 'how'):
            return 'Adverbial Clause'
        return 'Clause'
    if cls0 == 'subord':
        if low == 'if':
            return 'Conditional Clause'
        return 'Adverbial Clause'
    if cls0 in ('pron', 'pronaux'):
        return 'Clause' if n > 1 else 'Pronoun'
    if cls0 in ('aux', 'auxneg'):
        if has_passive(toks):
            return 'Verb Phrase / Passive'
        return 'Verb Phrase' if n > 1 else 'Verb'
    if cls0 == 'neg':
        if has_verb(toks):
            return 'Verb Phrase'
        if n == 1 or toks[1]['cls'] == 'adv':
            return 'Adverbial Phrase'
        return 'Noun Phrase'
    if cls0 == 'adv':
        if has_verb(toks):
            return 'Verb Phrase'
        return 'Adverbial Phrase'
    if cls0 == 'gerund':
        base = 'Gerund Phrase'
        if sentence_initial:
            base += ' / Subject'
        return base
    if cls0 == 'verb':
        if has_passive(toks):
            return 'Verb Phrase / Passive'
        return 'Verb' if n == 1 else 'Verb Phrase'
    if cls0 == 'noun':
        return 'Noun' if n == 1 else 'Noun Phrase'
    if cls0 == 'adj':
        return 'Adjective' if n == 1 else 'Adjective Phrase'
    return 'Noun' if n == 1 else 'Noun Phrase'


def label_fr(toks, sentence_initial=False, lead=None):
    n = len(toks)
    if n == 0:
        return 'Phrase'
    low = toks[0]['text'].lower()
    cls0 = lead or toks[0]['cls']
    if low in FINTERJ or cls0 == 'interj':
        return 'Interjection'
    if cls0 == 'num':
        return 'Numeral' if n == 1 else 'Noun Phrase'
    if cls0 == 'conj':
        rest = label_fr(toks[1:], False) if n > 1 else 'Phrase'
        return 'Conjunction + ' + rest
    if cls0 == 'idiom':
        return 'Adverbial Phrase'
    if cls0 == 'expletive':
        return 'Clause'
    if cls0 == 'prep':
        if low in ('de', "d'", 'à') and n > 1 and is_fr_infinitive(toks[1]['text']):
            base = 'Infinitive Phrase'
            if sentence_initial:
                base += ' / Subject'
            return base
        base = 'Prepositional Phrase'
        if has_rel_fr(toks):
            base += ' + Relative Clause'
        return base
    if cls0 in ('article', 'det'):
        base = 'Noun Phrase'
        if n == 1 and low.startswith('l\'') and is_fr_infinitive(low[2:]):
            return 'Infinitive Phrase'
        if has_rel_fr(toks):
            base += ' + Relative Clause'
        return base
    if cls0 == 'rel':
        if sentence_initial:
            return 'Interrogative Clause'
        if low in ('que', 'qu\''):
            return 'Clause'
        return 'Relative Clause'
    if cls0 == 'int':
        return 'Interrogative Clause' if sentence_initial else 'Clause'
    if cls0 == 'subord':
        if low == 'si':
            return 'Conditional Clause'
        return 'Adverbial Clause'
    if cls0 == 'pron':
        if low == 'on' and n > 1:
            return 'Verb Phrase / Active'
        return 'Clause' if n > 1 else 'Pronoun'
    if cls0 == 'refl':
        if n > 1 and is_fr_infinitive(toks[1]['text']):
            base = 'Infinitive Phrase'
            if sentence_initial:
                base += ' / Subject'
            return base
        return 'Clause' if n > 1 else 'Pronoun'
    if cls0 in ('aux', 'verb'):
        return 'Verb Phrase' if n > 1 else 'Verb'
    if cls0 == 'neg':
        if has_verb(toks):
            return 'Verb Phrase'
        if n == 1 or toks[1]['cls'] == 'adv':
            return 'Adverbial Phrase'
        return 'Noun Phrase'
    if cls0 == 'adv':
        if has_verb(toks):
            return 'Verb Phrase'
        return 'Adverbial Phrase'
    if cls0 == 'adj':
        return 'Adjective Phrase' if n > 1 else 'Adjective'
    return 'Noun' if n == 1 else 'Noun Phrase'


# ---------------------------------------------------------------------------
# chunk alignment (monotone DP with bigram + glossary bonus)

_GLOSS_CACHE = {}


def gloss_bonus(en_text, fr_text):
    """Count EN words whose glossary gloss appears as a word in the FR text."""
    key = (en_text, fr_text)
    if key in _GLOSS_CACHE:
        return _GLOSS_CACHE[key]
    score = 0.0
    tb = fr_text.lower()
    for w in en_text.lower().split():
        glosses = GLOSS.get(w)
        if not glosses:
            continue
        for g in glosses:
            low = g.lower()
            if len(low) <= 2:
                continue
            if low in tb.split():  # whole-word match on the French side
                score += 1.0
                break
    _GLOSS_CACHE[key] = score
    return score

def dice(text_a, text_b):
    """Dice coefficient over lowercase character bigrams; in [0, 1]."""
    a = text_a.lower()
    b = text_b.lower()
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ba = set(zip(a, a[1:]))
    bb = set(zip(b, b[1:]))
    if not ba or not bb:
        return 0.0
    return 2.0 * len(ba & bb) / (len(ba) + len(bb))


def _neural_rect(neural, i, ni, j, nj):
    """Sum of neural chunk-score matrix over the rectangle [i,ni) x [j,nj)."""
    s = 0.0
    for a in range(i, ni):
        row = neural[a]
        for b in range(j, nj):
            s += row[b]
    return s


def align_chunk_runs(en_chunks, fr_chunks, en_text, fr_text, lam=2.0, mu=4.0,
                     neural=None, wn=1.5):
    E, F = len(en_chunks), len(fr_chunks)
    if E == 0 or F == 0:
        return []
    cap = min(max(E, F), 6)
    ew = [len(c[1]) for c in en_chunks]
    fw = [len(c[1]) for c in fr_chunks]
    # conjunction chunks act as barriers: a unit may start at one but not
    # merge across it (prevents e.g. 'de penser' + 'mais j'ai pris conscience')
    en_bar = [c[0] == 'conj' for c in en_chunks]
    fr_bar = [c[0] == 'conj' for c in fr_chunks]
    # precompute unit text spans for dice scoring
    espan = [(c[1][0]['start'], c[1][-1]['end']) for c in en_chunks]
    fspan = [(c[1][0]['start'], c[1][-1]['end']) for c in fr_chunks]
    INF = float('inf')
    dp = [[INF] * (F + 1) for _ in range(E + 1)]
    ch = [[None] * (F + 1) for _ in range(E + 1)]
    dp[0][0] = 0.0
    for i in range(E + 1):
        for j in range(F + 1):
            cur = dp[i][j]
            if cur == INF:
                continue
            for di in range(1, cap + 1):
                ni = i + di
                if ni > E:
                    break
                for dj in range(1, cap + 1):
                    nj = j + dj
                    if nj > F:
                        break
                    if any(en_bar[i + 1:ni]) or any(fr_bar[j + 1:nj]):
                        continue
                    sw = sum(ew[i:ni]) - sum(fw[j:nj])
                    cost = sw * sw + lam * (di + dj - 2)
                    if mu:
                        ta = en_text[espan[i][0]:espan[ni - 1][1]]
                        tb = fr_text[fspan[j][0]:fspan[nj - 1][1]]
                        cost -= mu * dice(ta, tb)
                        cost -= 3.0 * gloss_bonus(ta, tb)
                    if neural is not None:
                        cost -= wn * _neural_rect(neural, i, ni, j, nj)
                    nd = cur + cost
                    if nd < dp[ni][nj]:
                        dp[ni][nj] = nd
                        ch[ni][nj] = (di, dj)
    if dp[E][F] == INF:
        return [(0, E, 0, F)]
    units = []
    i, j = E, F
    while i > 0 or j > 0:
        di, dj = ch[i][j]
        i -= di
        j -= dj
        units.append((i, i + di, j, j + dj))
    units.reverse()
    return units


# ---------------------------------------------------------------------------
# main alignment for one pair

def _sentence_initial(toks, chunk, full_toks):
    """True if chunk starts a new sentence (start of text or after final punct)."""
    first = chunk[0]
    pos = full_toks.index(first)
    if pos == 0:
        return True
    prev = full_toks[pos - 1]
    return prev['kind'] == 'punct' and prev['text'][-1] in FINAL_PUNCT


def _chunk_text(chunk):
    return chunk[0]['start'], chunk[-1]['end']


def _fmt(en_text, en_label, fr_text, fr_label):
    if en_text is None:
        en_text = '[omitted]'
    if fr_text is None:
        fr_text = '[omitted]'
    return "- **%s** [%s] **<-->** **%s** [%s]" % (en_text, en_label,
                                                  fr_text, fr_label)


def align_pair(en, fr, neural=None):
    """Align one EN/FR pair end to end.

    neural: optional E x F matrix of chunk-level scores (e.g. from a neural
    word aligner on GPU); higher score = stronger evidence that chunk i
    (EN) corresponds to chunk j (FR).  None = pure rule-based pairing.
    """
    en_toks = tokenize(en)
    fr_toks = tokenize(fr)
    for t in en_toks:
        if t['kind'] == 'word':
            t['cls'] = classify_en(t['text'])
    for t in fr_toks:
        if t['kind'] == 'word':
            t['cls'] = classify_fr(t['text'])
    en_chunks = chunk_en(en_toks)
    fr_chunks = chunk_fr(fr_toks)
    return align_chunked(en, fr, en_toks, fr_toks, en_chunks, fr_chunks,
                         neural=neural)


def align_chunked(en, fr, en_toks, fr_toks, en_chunks, fr_chunks, neural=None,
                  wn=1.5):
    """Chunk-to-bullets given already-tokenized/chunked sides.

    Used by align_pair and by the hybrid driver, which tokenizes and chunks
    once, runs the neural word aligner on the word lists, then calls this
    with the resulting chunk-score matrix.
    """
    en_final, en_int = split_punct(en_toks)
    fr_final, fr_int = split_punct(fr_toks)

    units = []  # (key, final_flag, en_text, en_label, fr_text, fr_label)

    # -- word chunks --
    if en_chunks and fr_chunks:
        # special case: EN leading 'please' <-> FR trailing 's'il vous plaît'
        en0 = en_chunks[0]
        fr_last = fr_chunks[-1]
        if (len(en0[1]) == 1 and en0[1][0]['text'].lower() == 'please'
                and len(fr_last[1]) == 3 and fr_last[1][0]['text'].lower() == "s'il"
                and fr_last[1][2]['text'].lower() == 'plaît'):
            es, ee = _chunk_text(en0[1])
            fs, fe = _chunk_text(fr_last[1])
            units.append((0.0, 0, en[es:ee], 'Interjection',
                          fr[fs:fe], 'Interjection'))
            en_chunks = en_chunks[1:]
            fr_chunks = fr_chunks[:-1]
    if en_chunks and fr_chunks:
        pairs = align_chunk_runs(en_chunks, fr_chunks, en, fr, neural=neural,
                                 wn=wn)
        for (ei, ei2, fj, fj2) in pairs:
            en_c = [t for c in en_chunks[ei:ei2] for t in c[1]]
            fr_c = [t for c in fr_chunks[fj:fj2] for t in c[1]]
            en_s, en_e = _chunk_text(en_c)
            fr_s, fr_e = _chunk_text(fr_c)
            key = float(ei)
            en_lead = en_chunks[ei][0]
            fr_lead = fr_chunks[fj][0]
            en_lab = label_en(en_c, _sentence_initial(en_toks, en_c, en_toks), en_lead)
            fr_lab = label_fr(fr_c, _sentence_initial(fr_toks, fr_c, fr_toks), fr_lead)
            units.append((key, 0, en[en_s:en_e], en_lab, fr[fr_s:fr_e], fr_lab))
    elif en_chunks:
        for c in en_chunks:
            s, e = _chunk_text(c[1])
            lab = label_en(c[1], False, c[0])
            units.append((0.0, 0, en[s:e], lab, None, lab))
    elif fr_chunks:
        for c in fr_chunks:
            s, e = _chunk_text(c[1])
            lab = label_fr(c[1], False, c[0])
            units.append((0.0, 0, None, lab, fr[s:e], lab))

    # -- punctuation: internal (pair by order) --
    def _punct_key(toks, chunk_list, p):
        """Return float key for a punctuation token based on word position."""
        nw = 0
        for t in toks:
            if t['kind'] == 'word':
                if t['start'] > p['start']:
                    break
                nw += 1
        # find chunk index containing word nw-1
        seen = 0
        for ci, c in enumerate(chunk_list):
            if nw - 1 < seen + len(c[1]):
                return float(ci) + 0.5
            seen += len(c[1])
        return float(len(chunk_list)) - 0.5 if chunk_list else -0.5

    k = min(len(en_int), len(fr_int))
    for i in range(k):
        p1, p2 = en_int[i], fr_int[i]
        key = _punct_key(en_toks, en_chunks, p1)
        units.append((key, 0, en[p1['start']:p1['end']], 'Punctuation',
                      fr[p2['start']:p2['end']], 'Punctuation'))
    for p1 in en_int[k:]:
        key = _punct_key(en_toks, en_chunks, p1)
        units.append((key, 0, en[p1['start']:p1['end']], 'Punctuation',
                      None, 'Punctuation'))
    for p2 in fr_int[k:]:
        key = _punct_key(fr_toks, fr_chunks, p2)
        units.append((key, 0, None, 'Punctuation',
                      fr[p2['start']:p2['end']], 'Punctuation'))

    # -- punctuation: final (pair by order) --
    k = min(len(en_final), len(fr_final))
    for i in range(k):
        p1, p2 = en_final[i], fr_final[i]
        key = _punct_key(en_toks, en_chunks, p1)
        units.append((key, 1, en[p1['start']:p1['end']], 'Punctuation',
                      fr[p2['start']:p2['end']], 'Punctuation'))
    for p1 in en_final[k:]:
        key = _punct_key(en_toks, en_chunks, p1)
        units.append((key, 1, en[p1['start']:p1['end']], 'Punctuation',
                      None, 'Punctuation'))
    for p2 in fr_final[k:]:
        key = _punct_key(fr_toks, fr_chunks, p2)
        units.append((key, 1, None, 'Punctuation',
                      fr[p2['start']:p2['end']], 'Punctuation'))

    units.sort(key=lambda u: (u[0], u[1]))
    lines = [_fmt(u[2], u[3], u[4], u[5]) for u in units]
    return '\n'.join(lines)
