"""Build ui_scaffold/klga.html: FAA diagram image + identifiers/topology from data/airports/klga.graph.json (venue code).
No geometry is invented or drawn: the graph's geometry fields are null and stay null.
  python3 venue/build_klga_page.py
"""
import html, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
g = json.loads((REPO / 'data/airports/klga.graph.json').read_text())
E = html.escape
surf = {s['id']: s for s in g['surfaces']}
nodes = {n['id']: n for n in g['nodes']}
img = (REPO / 'ui_scaffold/klga_faa_diagram.png').exists()
src = next(s for s in g['sources'] if s['kind'] == 'faa_diagram')
statuses = sorted({x['review']['status'] for k in ('surfaces', 'runway_ends', 'nodes', 'segments', 'hold_points', 'zones') for x in g[k]})


def ids(kind):
    return ', '.join(E(s.get('identifier') or s['id'].split(':')[-1]) for s in g['surfaces'] if s['kind'] == kind)


rows_seg = ''.join(
    f"<tr><td>{E(s['surface_id'].split(':')[-1])}</td><td>{E(s['from_node_id'].split(':')[-1])}</td><td>{E(s['to_node_id'].split(':')[-1])}</td>"
    f"<td>{E(s['topology'])}</td><td>{E(s['direction_permission'])}</td></tr>" for s in g['segments'])
rows_hold = ''.join(
    f"<tr><td>{E(h['id'].split(':')[-1])}</td><td>{E(h['protected_surface_id'].split(':')[-1])}</td><td>{E((h.get('approach_surface_id') or '').split(':')[-1])}</td>"
    f"<td>{E(h.get('physical_marking_status', ''))}</td></tr>" for h in g['hold_points'])
rows_zone = ''.join(
    f"<tr><td>{E(z['id'].split(':')[-1])}</td><td>{E(', '.join(s.split(':')[-1] for s in z['surface_ids']))}</td><td>{E(z.get('boundary_status', ''))}</td>"
    f"<td>{'yes' if z.get('usable_for_occupancy') else 'no'}</td></tr>" for z in g['zones'])
crossing_nodes = [n for n in g['nodes'] if any('RWY' in s for s in n.get('surface_ids', []))]
rows_x = ''.join(f"<tr><td>{E(n['id'].split(':')[-1])}</td><td>{E(' × '.join(s.split(':')[-1] for s in n['surface_ids']))}</td><td>{E(n['kind'])}</td></tr>" for n in crossing_nodes)
use = g['usability']

page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KLGA reference</title>
<style>
body{{margin:0;background:#0d1117;color:#e6edf5;font:14px system-ui,sans-serif;padding:16px}}
.banner{{background:#2a2110;border:1px solid #d29922;color:#f0c674;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-weight:600}}
.wrap{{display:grid;grid-template-columns:minmax(300px,1fr) minmax(320px,1fr);gap:14px}}
@media(max-width:800px){{.wrap{{grid-template-columns:1fr}}}}
.panel{{background:#151b23;border:1px solid #263040;border-radius:8px;padding:10px 12px;overflow-x:auto}}
img{{max-width:100%;background:#fff;border-radius:4px}}
table{{border-collapse:collapse;font:12px ui-monospace,monospace;margin:4px 0 12px}}td,th{{padding:3px 8px;border-bottom:1px solid #263040;text-align:left}}th{{color:#8b98a9}}
h2{{font-size:14px;margin:6px 0}}.dim{{color:#8b98a9;font-size:12px}}a{{color:#4aa3ff}}
</style></head><body>
<div class="banner">Real airport reference: FAA diagram + identifiers (draft2, expert review pending). Geometry not used for prediction; look-ahead runs only on fictional SIM-1.</div>
<div class="wrap">
<div class="panel"><h2>FAA airport diagram: {E(src['title'])}</h2>
{'<img src="klga_faa_diagram.png" alt="FAA LaGuardia airport diagram (rendered from the FAA PDF)">' if img else '<p>Diagram image not rendered (pdftoppm unavailable).</p>'}
<div class="dim">Rendered from <code>{E(src['local_path'])}</code> (sha256 {E(src['sha256'][:16])}…), source {E(src['uri'])}. Not for navigation.</div></div>
<div class="panel">
<div class="dim">Dataset {E(g['dataset_version'])} · intended use: {E(g['intended_use'])} · review status of all records: {E(', '.join(statuses))} · geometry: null everywhere</div>
<div class="dim">Usable for: {', '.join(k for k, v in use.items() if v)} · NOT usable for: {', '.join(k for k, v in use.items() if not v)}</div>
<h2>Runways</h2><div>{ids('runway')}</div>
<h2>Taxiways (identifiers read from the diagram; not exhaustive)</h2><div>{ids('taxiway')}</div>
<h2>Named areas</h2><div>{ids('named_area')}</div>
<h2>Runway-crossing topology (draft fragments)</h2>
<table><tr><th>junction</th><th>surfaces</th><th>kind</th></tr>{rows_x}</table>
<table><tr><th>segment on</th><th>from</th><th>to</th><th>topology</th><th>direction</th></tr>{rows_seg}</table>
<h2>Hold constraints (conceptual)</h2>
<table><tr><th>id</th><th>protects</th><th>approach</th><th>physical marking</th></tr>{rows_hold}</table>
<h2>Conflict-area references</h2>
<table><tr><th>id</th><th>surfaces</th><th>boundary</th><th>usable for occupancy</th></tr>{rows_zone}</table>
<div class="dim">{len(g['issues'])} open questions for a qualified reviewer: data/airports/KLGA_CHANGES_draft2.md.</div>
</div></div>
<div class="panel" style="margin-top:14px">Historical text replay (ledger only, no prediction): <a href="index.html?f=samples/LGA_2026-03-22.json">LGA_2026-03-22 in the main display</a> · <a href="nav.html">all GMAPS pages</a></div>
</body></html>
"""
(REPO / 'ui_scaffold/klga.html').write_text(page)
print('wrote ui_scaffold/klga.html', 'with image' if img else 'without image')
