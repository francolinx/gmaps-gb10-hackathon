"""Text normalisation for ATC phraseology (prepared library, stdlib only).

Order matters:
  1. known ASR repairs (from phraseology_grammar.json asr_repairs_observed)
  2. callsign extraction happens in parser.py on the repaired text BEFORE phonetics are collapsed,
     so 'Delta 520' (airline) is not turned into taxiway D.
  3. number words -> digits, runway suffix words -> L/R/C
  4. ICAO phonetics -> letters; identical adjacent phonetics -> double letter (AA);
     phonetic + single digit -> letter+digit (D1) for numbered taxiways.
Nothing here guesses: unknown words pass through unchanged.
"""
import re

NUMBER_WORDS = {'ZERO': '0', 'OH': '0', 'ONE': '1', 'TWO': '2', 'THREE': '3', 'TREE': '3', 'FOUR': '4',
                'FIVE': '5', 'FIFE': '5', 'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9', 'NINER': '9'}
PHONETICS = {'ALPHA': 'A', 'ALFA': 'A', 'BRAVO': 'B', 'CHARLIE': 'C', 'DELTA': 'D', 'ECHO': 'E', 'FOXTROT': 'F',
             'GOLF': 'G', 'HOTEL': 'H', 'INDIA': 'I', 'JULIET': 'J', 'JULIETT': 'J', 'KILO': 'K', 'LIMA': 'L',
             'MIKE': 'M', 'NOVEMBER': 'N', 'OSCAR': 'O', 'PAPA': 'P', 'QUEBEC': 'Q', 'ROMEO': 'R', 'SIERRA': 'S',
             'TANGO': 'T', 'UNIFORM': 'U', 'VICTOR': 'V', 'WHISKEY': 'W', 'XRAY': 'X', 'X-RAY': 'X', 'YANKEE': 'Y',
             'ZULU': 'Z'}
SUFFIX = {'LEFT': 'L', 'RIGHT': 'R', 'CENTER': 'C', 'CENTRE': 'C'}
FILLERS = {'UH', 'UM', 'ER', 'AH', 'OKAY', 'OK', 'PLEASE', 'JUST'}
# Words after which a following bare number is a runway designator.
RUNWAY_CONTEXT = {'RUNWAY', 'CROSS', 'CROSSING', 'ACROSS', 'OF', 'ON', 'TO', 'LAND', 'TAKEOFF', 'SHORT'}

ASR_REPAIRS = [
    ('host short of', 'hold short of'), ('host runway', 'hold short runway'), ('i should mic', 'hold short of mike'),
    ('hold your text to wake kila', 'hold short of kilo'), ('kila', 'kilo'), ('boarding the takeoff', 'aborting the takeoff'),
    ('retracted on runway', 'rejecting on runway'), ('crossing for adelva', 'crossing 4 at delta'),
    ('adelva', 'at delta'), ('clear for takeoff', 'cleared for takeoff'), ('clear to land', 'cleared to land'),
]


def repair(text: str):
    """Apply observed ASR repairs. Returns (text, list_of_repairs_applied) so the change is auditable."""
    low = ' ' + text.lower() + ' '
    applied = []
    for bad, good in ASR_REPAIRS:
        if bad in low:
            low = low.replace(bad, good)
            applied.append((bad, good))
    return low.strip(), applied


def tokenize(text: str):
    t = text.upper()
    t = t.replace('-', ' ').replace('/', ' ')
    t = re.sub(r'([,.;:?!])', r' \1 ', t)
    t = re.sub(r"[^A-Z0-9,.;:?!' ]", ' ', t)
    return [w for w in t.split() if w not in FILLERS]


def collapse_numbers(tokens):
    """ONE THREE -> 13 ; 3 3 LEFT -> 33L (only when preceded by runway context or followed by a suffix)."""
    out = []
    i = 0
    while i < len(tokens):
        w = tokens[i]
        if w in NUMBER_WORDS or re.fullmatch(r'\d', w):
            digits = []
            j = i
            while j < len(tokens) and (tokens[j] in NUMBER_WORDS or re.fullmatch(r'\d', tokens[j])):
                digits.append(NUMBER_WORDS.get(tokens[j], tokens[j]))
                j += 1
            num = ''.join(digits)
            if j < len(tokens) and tokens[j] in SUFFIX and len(num) <= 2:
                num += SUFFIX[tokens[j]]
                j += 1
            out.append(num)
            i = j
            continue
        if re.fullmatch(r'\d{1,2}', w) and i + 1 < len(tokens) and tokens[i + 1] in SUFFIX:
            out.append(w + SUFFIX[tokens[i + 1]])
            i += 2
            continue
        m = re.fullmatch(r'(\d{1,2})([LRC])', w)
        out.append(w if not m else m.group(1) + m.group(2))
        i += 1
    return out


def collapse_phonetics(tokens):
    """DELTA -> D ; ALPHA ALPHA -> AA ; DOUBLE ALPHA -> AA ; DELTA 1 -> D1 (single digit only)."""
    out = []
    i = 0
    while i < len(tokens):
        w = tokens[i]
        if w == 'DOUBLE' and i + 1 < len(tokens) and tokens[i + 1] in PHONETICS:
            out.append(PHONETICS[tokens[i + 1]] * 2)
            i += 2
            continue
        if w in PHONETICS:
            letter = PHONETICS[w]
            if i + 1 < len(tokens) and tokens[i + 1] == w:
                out.append(letter * 2)
                i += 2
                continue
            if i + 1 < len(tokens) and re.fullmatch(r'\d', tokens[i + 1]):
                out.append(letter + tokens[i + 1])
                i += 2
                continue
            out.append(letter)
            i += 1
            continue
        out.append(w)
        i += 1
    return out


def canonical_runway(token: str):
    """'4' -> '04', '33L' -> '33L'. Returns None if not a runway-shaped token (1..36 + optional suffix)."""
    m = re.fullmatch(r'(\d{1,2})([LRC]?)', token or '')
    if not m:
        return None
    n = int(m.group(1))
    if not 1 <= n <= 36:
        return None
    return f'{n:02d}{m.group(2)}'


def normalize(text: str):
    """Full normalisation (used on the part of the utterance left after callsigns were removed)."""
    repaired, applied = repair(text)
    toks = collapse_phonetics(collapse_numbers(tokenize(repaired)))
    return ' '.join(toks), applied
