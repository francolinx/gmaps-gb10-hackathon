"""Whisper on PRIVATE real ATC clips (venue code, Oct 3). Text results only.

Audio stays in ~/gmaps_venue/audio_real_private (never copied, committed, uploaded or played). Two phases:
  container (offline, read-only /audio):  python3 /gmaps/venue/asr_real.py asr      -> /out/asr_real.json
  host:                                  python3 venue/asr_real.py parse <asr_real.json>
Filename content labels are UNVERIFIED human labels: never passed to Whisper or the parser.
"""
import json, re, statistics, sys, time
from pathlib import Path


def asr():
    sys.path.insert(0, '/gmaps/lib')
    import librosa, numpy as np, soundfile as sf, torch
    from gmaps_core.adapters import transcribe
    clips = sorted(Path('/audio').glob('*.wav'))
    t0 = time.perf_counter()
    transcribe({'raw': np.zeros(16000, dtype=np.float32), 'sampling_rate': 16000}, '/models/whisper')   # cold load on silence
    torch.cuda.synchronize()
    cold = round(time.perf_counter() - t0, 3)
    rows = []
    for p in clips:
        a, sr = sf.read(str(p), dtype='float32', always_2d=True)
        a = a.mean(axis=1)
        if sr != 16000:
            a = librosa.resample(a, orig_sr=sr, target_sr=16000)
        dur = len(a) / 16000
        torch.cuda.synchronize(); s0 = time.perf_counter()
        r = transcribe({'raw': np.ascontiguousarray(a), 'sampling_rate': 16000}, '/models/whisper')
        torch.cuda.synchronize(); s = time.perf_counter() - s0
        rows.append({'clip': p.name, 'audio_s': round(dur, 2), 'asr_s': round(s, 3), 'asr_text_raw': r['text']})
        print(f'{s:6.3f}s  {p.name}', flush=True)
    lat = [r['asr_s'] for r in rows]
    out = {'summary': {'n': len(rows), 'cold_load_s': cold, 'median_asr_s': round(statistics.median(lat), 3),
                       'min_asr_s': min(lat), 'max_asr_s': max(lat), 'device': torch.cuda.get_device_name(0),
                       'median_audio_s': round(statistics.median(r['audio_s'] for r in rows), 2)}, 'clips': rows}
    Path('/out/asr_real.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out['summary']))


def batch_of(name):
    if re.match(r'^\d\d_REAL_ATC_', name):
        return 'batch3_unlabelled'
    if name == '06_STOP_TRUCK1_STOP.wav':      # listed as item 06 in README.txt (batch 1) despite its all-caps name
        return 'batch1_labelled'
    if re.match(r'^\d\d_[A-Z0-9_]+\.wav$', name):
        return 'batch2_labelled'
    return 'batch1_labelled'


def label_of(name):
    if batch_of(name) == 'batch3_unlabelled':
        return None
    return re.sub(r'^\d\d_', '', name[:-4]).replace('_', ' ')


def parse_all(path):
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / 'lib'))
    from gmaps_core.airport import Airport
    from gmaps_core.parser import parse
    ap = Airport(repo / 'data/airports/klga.graph.json')
    d = json.loads(Path(path).read_text())
    for r in d['clips']:
        ev = parse(r['asr_text_raw'], 'KLGA', resolver=ap, source={'id': r['clip'], 'start_s': None, 'end_s': None})
        r['batch'], r['unverified_label'] = batch_of(r['clip']), label_of(r['clip'])
        r['parse'] = {k: ev.get(k) for k in ('speech_act', 'kind', 'actor_candidates', 'runway', 'route', 'crossing_at',
                                             'hold_constraints', 'hold_position', 'parse_path', 'asr_repairs_applied')}
        r['parse']['unresolved'] = (ev.get('uncertainty') or {}).get('unresolved')
    Path(path).write_text(json.dumps(d, indent=1))
    print(f'parsed {len(d["clips"])} clips -> {path}')


if __name__ == '__main__':
    asr() if sys.argv[1] == 'asr' else parse_all(sys.argv[2])
