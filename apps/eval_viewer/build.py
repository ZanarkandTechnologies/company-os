#!/usr/bin/env python3
"""Build a private static HTML dossier for an analysis-only eval run."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.eval_viewer.model import build_evidence_model


ROOT = Path(__file__).resolve().parents[2]


def render_markdown(markdown: str) -> str:
    output, paragraph, list_tag = [], [], None
    code = False
    lines = markdown.replace("\r\n", "\n").splitlines()
    if lines and lines[0].strip() == "---":
        closing = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
        if closing is not None:
            lines = lines[closing + 1:]

    def flush() -> None:
        nonlocal paragraph, list_tag
        if paragraph:
            output.append(f"<p>{html.escape(' '.join(paragraph))}</p>")
            paragraph = []
        if list_tag:
            output.append(f"</{list_tag}>")
            list_tag = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            output.append("</code></pre>" if code else "<pre><code>")
            code = not code
        elif code:
            output.append(html.escape(line) + "\n")
        elif not stripped:
            flush()
        elif match := re.match(r"^(#{1,6})\s+(.+)$", stripped):
            flush()
            level = len(match.group(1))
            output.append(f"<h{level}>{html.escape(match.group(2))}</h{level}>")
        elif match := re.match(r"^[-*]\s+(.+)$", stripped):
            if list_tag != "ul":
                flush()
                output.append("<ul>")
                list_tag = "ul"
            output.append(f"<li>{html.escape(match.group(1))}</li>")
        else:
            paragraph.append(stripped)
    flush()
    return "".join(output)


def render_evidence_html(model: dict) -> str:
    view_model = json.loads(json.dumps(model))
    for evaluation in view_model["evaluations"]:
        for output in evaluation["outputs"]:
            output["renderedHtml"] = render_markdown(str(output.get("markdown") or ""))
    safe_model = json.dumps(view_model).replace("<", "\\u003c")
    page = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Company OS evals</title>
<style>
:root{color-scheme:dark;--bg:#060606;--panel:#0d0d0d;--row:#111;--row-alt:#0b0b0b;--line:#272727;--line-strong:#3a3a3a;--ink:#d0d0ca;--muted:#777772;--peach:#f2ceb0;--lavender:#cec7ed;--mint:#b9ddcb;--pink:#e8b7c5;--yellow:#ead99d;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box;scrollbar-color:#343434 #090909;scrollbar-width:thin}*::-webkit-scrollbar{width:8px;height:8px}*::-webkit-scrollbar-track{background:#090909}*::-webkit-scrollbar-thumb{border:2px solid #090909;background:#343434}html,body{height:100%}body{margin:0;overflow:hidden;background:var(--bg);color:var(--ink);font:12px/1.45 var(--mono)}button,a{font:inherit;color:inherit}button:focus-visible,summary:focus-visible,a:focus-visible{outline:1px solid var(--lavender);outline-offset:2px}
.shell{height:100%;padding:18px 22px;display:grid;grid-template-rows:48px minmax(0,1fr);gap:10px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:0 12px;border:1px solid var(--line);background:var(--panel)}.topbar h1{margin:0;flex:0 1 auto;font-size:12px;font-weight:500;letter-spacing:.04em;text-transform:lowercase}.metrics{display:flex;align-items:center;justify-content:flex-end;gap:6px;color:var(--muted);font-size:9px}.metric-pill,.group-pill{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}.metric-pill{padding:4px 7px;border:1px solid var(--line);border-radius:999px;background:#111;color:#aaa9a3}.group-pill{padding:3px 6px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:8px}.run-link{margin-left:2px;color:var(--muted);text-decoration:none;white-space:nowrap}.run-link:hover{color:var(--lavender)}.square{display:inline-block;width:10px;height:10px;flex:0 0 10px;border:1px solid rgba(255,255,255,.16)}.metric-square{width:8px;height:8px;flex-basis:8px;border:0}.tone-peach{background:var(--peach)}.tone-lavender{background:var(--lavender)}.tone-mint{background:var(--mint)}.tone-pink{background:var(--pink)}.tone-yellow{background:var(--yellow)}
.workspace{min-height:0;display:grid;grid-template-columns:minmax(300px,40fr) minmax(520px,60fr);gap:10px}.list-panel,.inspector{min-height:0;border:1px solid var(--line);background:var(--panel)}.list-panel{overflow:auto}.list-head{position:sticky;top:0;z-index:4;display:grid;grid-template-columns:1fr 90px;padding:8px 11px;border-bottom:1px solid var(--line);background:#0a0a0a;color:var(--muted);font-size:9px;text-transform:lowercase}.feature-group{border-bottom:1px solid var(--line)}.feature-toggle{position:sticky;top:31px;z-index:3;width:100%;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 11px;border:0;border-bottom:1px solid var(--line);background:#0b0b0b;text-align:left;cursor:pointer}.feature-label{min-width:0;display:flex;align-items:center;gap:8px;font-weight:700}.toggle-glyph{width:8px;color:var(--muted);font-size:8px}.feature-rows.hidden{display:none}.feature-button{position:relative;width:100%;min-height:66px;display:grid;grid-template-columns:3px 11px minmax(0,1fr) auto;gap:10px;align-items:center;padding:9px 11px 9px 0;border:0;border-bottom:1px solid #1c1c1c;background:var(--row);text-align:left;cursor:pointer}.feature-button:nth-child(even){background:var(--row-alt)}.feature-button:hover,.feature-button[aria-current=true]{outline:1px solid var(--line-strong);outline-offset:-1px;background:#151515}.rail{align-self:stretch;background:transparent}.feature-button[aria-current=true] .rail{background:var(--peach)}.weekly .feature-button[aria-current=true] .rail{background:var(--lavender)}.meeting .feature-button[aria-current=true] .rail{background:var(--mint)}.feature-copy{min-width:0}.feature-copy b{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}.feature-copy small{display:block;margin-top:5px;overflow:hidden;color:var(--muted);font-size:9px;text-overflow:ellipsis;white-space:nowrap}.status-pill{min-width:68px;padding:3px 6px;border-radius:2px;color:#171714;font-size:8px;font-weight:800;letter-spacing:.04em;text-align:center;text-transform:uppercase}.status-pill.pass{background:var(--mint)}.status-pill.fail{background:var(--pink)}.status-pill.needs_information{background:var(--yellow)}.status-pill.not_run{background:#aaa}.status-pill.unjudged{background:var(--lavender)}
.inspector{overflow:auto}.inspector-head{position:sticky;top:0;z-index:3;display:flex;justify-content:space-between;gap:12px;padding:12px;border-bottom:1px solid var(--line);background:#0a0a0a}.kicker{margin:0 0 5px;color:var(--muted);font-size:9px}.title-row{display:flex;align-items:center;gap:8px}.inspector h2{margin:0;font-size:13px}.close{display:none;border:0;background:transparent;color:var(--muted);font-size:18px;cursor:pointer}.status-strip{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--line)}.status-note{color:var(--muted);font-size:9px}.inspector section{margin:0;padding:12px;border-top:1px solid var(--line)}.inspector h3{margin:0 0 8px;color:#92928e;font-size:9px;letter-spacing:.08em;text-transform:uppercase}.task-copy{margin:0;color:#c9c9c3}.record{margin-top:7px;border:1px solid var(--line);background:#0a0a0a}.record>summary{min-height:42px;display:grid;grid-template-columns:10px minmax(0,1fr) auto;gap:9px;align-items:center;padding:7px 8px;background:#101010;cursor:pointer}.record[open]>summary{border-bottom:1px solid var(--line)}.record>summary:hover{background:#141414}.record-identity{min-width:0}.record-identity small{display:block;color:var(--muted);font-size:8px;text-transform:uppercase}.record-identity b{display:block;overflow:hidden;color:#deded8;font-size:10px;text-overflow:ellipsis;white-space:nowrap}.record-state{padding:3px 6px;border:1px solid var(--line-strong);color:#b7b7b1;font-size:8px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;white-space:nowrap}.state-at-risk,.state-blocked{border-color:#766d47;color:var(--yellow)}.state-done,.state-final,.state-complete,.state-on-track,.state-processed{border-color:#426152;color:var(--mint)}.record pre{max-height:320px;margin:0;padding:9px;overflow:auto;color:#b7b7b2;font:9px/1.55 var(--mono);overflow-wrap:anywhere;white-space:pre-wrap}.case-list{margin:0;padding:0;list-style:none}.case-list li{padding:7px 0;border-bottom:1px solid #202020}.case-list li:last-child{border-bottom:0}.case-list b{display:block;color:#c9c9c3}.case-list small{display:block;margin-top:3px;color:var(--muted)}
.evaluation-workbench{display:grid;grid-template-columns:1fr;gap:8px}.evaluation-output,.evaluation-criteria{min-width:0;border:1px solid var(--line);background:#090909}.evaluation-output>header,.evaluation-criteria>header{display:grid;gap:2px;padding:9px 10px;border-bottom:1px solid var(--line);background:#101010}.evaluation-output>header b,.evaluation-criteria>header b{color:#deded8;font-size:10px}.evaluation-output>header span,.evaluation-criteria>header span{color:var(--muted);font-size:8px}.output-list{display:grid;gap:8px;padding:8px}.output{display:grid;grid-template-columns:10px minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px;border:1px solid #3e3a50;color:var(--lavender);text-decoration:none}.output:hover{background:#15131b}.output-copy{min-width:0}.output-copy b{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.output-copy small{display:block;margin-top:3px;color:var(--muted)}.markdown-preview{padding:10px;border:1px solid var(--line);background:#0b0b0b;color:#c8c8c2}.markdown-preview h1,.markdown-preview h2,.markdown-preview h3,.markdown-preview h4{margin:14px 0 7px;color:#deded8;font-size:11px}.markdown-preview h1:first-child,.markdown-preview h2:first-child{margin-top:0}.markdown-preview p{margin:7px 0}.markdown-preview ul{margin:7px 0;padding-left:18px}.markdown-preview pre{overflow:auto;padding:9px;border:1px solid var(--line);white-space:pre-wrap}.empty{margin:8px;padding:9px;border:1px dashed var(--line);color:var(--muted)}.expected-summary{margin:0;padding:9px 10px;border-bottom:1px solid var(--line);color:#aaa9a4}.check-list{display:grid;gap:6px;margin:0;padding:8px;list-style:none}.check{display:grid;grid-template-columns:10px minmax(0,1fr) auto;gap:8px;align-items:start;padding:8px;border:1px solid var(--line);background:#0c0c0c}.check strong{padding:2px 5px;border:1px solid var(--line);font-size:7px;letter-spacing:.07em}.check.pass strong{color:var(--mint)}.check.fail{border-color:#573944;background:#110b0d}.check.fail strong{color:var(--pink)}.check.needs_information strong,.check.unjudged strong{color:var(--yellow)}
@media(max-width:900px){body{overflow:auto}.shell{height:auto;min-height:100%;padding:10px;grid-template-rows:auto minmax(calc(100vh - 92px),auto)}.topbar{min-width:0;min-height:54px;padding:8px 10px;overflow:hidden}.metrics{flex-wrap:wrap}.run-link{width:100%;text-align:right}.workspace{display:block;min-width:0}.list-panel{width:100%;min-height:calc(100vh - 92px);overflow-x:hidden}.inspector{position:fixed;inset:0;z-index:20;display:none;border:0}.inspector.open{display:block}.close{display:block;min-width:44px;min-height:44px}.feature-toggle{top:31px}}
@media(max-width:560px){.topbar{align-items:flex-start;flex-direction:column;gap:7px}.metrics{justify-content:flex-start}.run-link{width:auto;text-align:left}.feature-button{grid-template-columns:3px 11px minmax(0,1fr) 68px;gap:8px}}
</style>
</head>
<body>
<main class="shell">
  <header class="topbar"><h1>company os — setup evaluation</h1><div class="metrics" id="metrics"></div></header>
  <div class="workspace">
    <section class="list-panel" aria-label="Evaluation checks"><div class="list-head"><span>evals · grouped by automation</span><span>result</span></div><div id="features"></div></section>
    <aside id="detail" class="inspector" aria-live="polite"></aside>
  </div>
</main>
<script type="application/json" id="evidence-model">__MODEL_JSON__</script>
<script>
const model=JSON.parse(document.getElementById('evidence-model').textContent);
const metrics=document.getElementById('metrics');const featureList=document.getElementById('features');const detail=document.getElementById('detail');
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
const tones=['peach','lavender','mint','pink','yellow'];
function statusLabel(value){return value==='pass'?'PASSED':value==='fail'?'FAILED':value==='needs_information'?'NEEDS INFO':value==='not_run'?'NOT RUN':'UNJUDGED'}
function stateClass(value){return 'state-'+String(value||'').toLowerCase().replace(/[^a-z0-9]+/g,'-')}
function cadenceLabel(value){return value==='daily'?'PM Daily':value==='weekly'?'PM Weekly':'Unknown automation'}
const metricData=[['mint',model.metrics.evaluations.passed+'/'+model.metrics.evaluations.total+' evals'],['peach',model.metrics.checks.passed+'/'+model.metrics.checks.total+' checks'],['yellow',model.metrics.outputs.total+'/'+model.metrics.outputs.total+' outputs']];
metrics.innerHTML=metricData.map(([tone,label])=>'<span class="metric-pill"><i class="square metric-square tone-'+tone+'"></i>'+esc(label)+'</span>').join('')+'<span class="metric-pill"><i class="square metric-square tone-yellow"></i>'+esc(String(model.runStatus).replaceAll('_',' '))+'</span>'+(model.activityLogAvailable?'<a class="run-link" href="activity.jsonl">log ↗</a>':'')+'<a class="run-link" href="eval-receipt.json">receipt ↗</a>';
function render(index,openMobile=true){
  const f=model.evaluations[index];document.querySelectorAll('.feature-button').forEach((button,i)=>button.setAttribute('aria-current',String(i===index)));const tone=tones[index%tones.length];
  const outputs=f.outputs.length?'<div class="output-list">'+f.outputs.map(row=>'<a class="output" href="'+esc(row.url)+'"><i class="square tone-lavender"></i><span class="output-copy"><b>'+esc(row.label)+' ↗</b><small>'+esc(row.kind)+' · '+esc(String(row.state).replaceAll('_',' '))+'</small></span></a><div class="markdown-preview">'+row.renderedHtml+'</div>').join('')+'</div>':'<p class="empty">No human-facing output was recorded for this eval.</p>';
  const checks=f.assertions.length?'<ul class="check-list">'+f.assertions.map(row=>'<li class="check '+row.status+'"><i class="square tone-'+(row.status==='pass'?'mint':row.status==='fail'?'pink':'yellow')+'"></i><span>'+esc(row.assertion)+'</span><strong>'+esc(row.status==='pass'?'MET':row.status==='fail'?'MISS':'PENDING')+'</strong></li>').join('')+'</ul>':'<p class="empty">No assertion result was available.</p>';
  detail.innerHTML='<header class="inspector-head"><div><p class="kicker">'+esc(cadenceLabel(f.cadence))+' · '+esc(f.id)+(f.showcase?' · showcase':'')+'</p><div class="title-row"><i class="square tone-'+tone+'"></i><h2>'+esc(f.name)+'</h2></div></div><button class="close" type="button" aria-label="Close inspector">×</button></header><div class="status-strip"><span class="status-pill '+f.status+'">'+statusLabel(f.status)+'</span><span class="status-note">'+esc(f.statusNote)+'</span></div><section><h3>Description</h3><p class="task-copy">'+esc(f.description)+'</p></section><section><h3>Expected behavior</h3><p class="task-copy">'+esc(f.claim)+'</p></section><section><h3>Resultant artifacts</h3>'+outputs+'</section><section><h3>Assertion review</h3><div class="evaluation-workbench"><article class="evaluation-criteria"><header><b>Expected criteria</b><span>'+f.assertions.filter(row=>row.status==='pass').length+'/'+f.assertions.length+' met after the shared run</span></header>'+checks+'</article></div></section>';
  detail.querySelector('.close').addEventListener('click',()=>{detail.classList.remove('open');document.body.classList.remove('inspector-open')});detail.scrollTop=0;if(openMobile){detail.classList.add('open');document.body.classList.add('inspector-open')}
}
function group(cadence,label,tone){
  const indexes=model.evaluations.map((feature,index)=>({feature,index})).filter(row=>row.feature.cadence===cadence);if(!indexes.length)return;const section=document.createElement('section');section.className='feature-group '+cadence;
  section.innerHTML='<button class="feature-toggle" type="button" aria-expanded="true"><span class="feature-label"><span class="toggle-glyph">▼</span><i class="square tone-'+tone+'"></i><span>'+esc(label)+'</span></span><span class="group-pill">'+indexes.filter(row=>row.feature.status==='pass').length+'/'+indexes.length+' passed</span></button><div class="feature-rows"></div>';
  const rows=section.querySelector('.feature-rows');indexes.forEach(({feature,index})=>{const button=document.createElement('button');button.className='feature-button';button.type='button';button.innerHTML='<span class="rail"></span><i class="square tone-'+tone+'"></i><span class="feature-copy"><b>'+esc(feature.name)+'</b><small>'+esc(feature.description)+'</small></span><span class="status-pill '+feature.status+'">'+statusLabel(feature.status)+'</span>';button.addEventListener('click',()=>render(index,true));rows.appendChild(button)});
  section.querySelector('.feature-toggle').addEventListener('click',event=>{const open=event.currentTarget.getAttribute('aria-expanded')==='true';event.currentTarget.setAttribute('aria-expanded',String(!open));event.currentTarget.querySelector('.toggle-glyph').textContent=open?'▶':'▼';rows.classList.toggle('hidden',open)});featureList.appendChild(section)
}
group('daily','PM Daily','peach');group('weekly','PM Weekly','lavender');render(0,false);
</script>
</body>
</html>'''
    return page.replace("__MODEL_JSON__", safe_model)


def build_static_evidence_viewer(*, out_dir: Path, eval_run_root: Path) -> dict:
    run = eval_run_root.resolve()
    destination = out_dir.resolve()
    model = build_evidence_model(project_root=ROOT, eval_run_root=run)
    destination.mkdir(parents=True, exist_ok=True)
    copied = {"eval-receipt.json"}
    if model["activityLogAvailable"]:
        copied.add("activity.jsonl")
    copied.update(output["url"] for row in model["evaluations"] for output in row["outputs"])
    for relative in copied:
        source = (run / relative).resolve()
        target = destination / relative
        if source == target.resolve():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        os.chmod(target, 0o600)
    model_path = destination / "model.json"
    index_path = destination / "index.html"
    model_path.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    index_path.write_text(render_evidence_html(model), encoding="utf-8")
    os.chmod(model_path, 0o600)
    os.chmod(index_path, 0o600)
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--eval-run", type=Path, required=True)
    args = parser.parse_args()
    model = build_static_evidence_viewer(out_dir=args.out.resolve(), eval_run_root=args.eval_run.resolve())
    print(json.dumps({"out_dir": str(args.out.resolve()), "metrics": model["metrics"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
