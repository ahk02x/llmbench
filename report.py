#!/usr/bin/env python3
"""Build RESULTS.md from JSONL and a standalone HTML edition of REPORT.md. Stdlib only.

  ./report.py            # latest row per model and GPU wins; review REPORT.md when data changes
"""
import glob, html, json, pathlib, re

HERE = pathlib.Path(__file__).parent
MOE = {"qwen3:30b-a3b", "qwen3:30b-a3b-instruct-2507-q4_K_M", "gpt-oss:20b"}
UNGRADED = {"qwen3:30b-a3b"}  # reasons out loud even with think off: the answer checkers cannot grade it, speed only
INSTRUCT = "qwen3:30b-a3b-instruct-2507-q4_K_M"  # mixture-of-experts: only a few experts run per token
NICE = {
    "mistral:latest": "mistral 7B", "mistral": "mistral 7B", "qwen2.5:7b": "qwen2.5 7B", "qwen2.5-coder:14b": "qwen2.5-coder 14B", "qwen2.5:14b": "qwen2.5 14B (4-bit)",
    "qwen2.5:14b-instruct-q3_K_M": "qwen2.5 14B (3-bit)", "qwen2.5:14b-instruct-q6_K": "qwen2.5 14B (6-bit)",
    "qwen2.5:14b-instruct-q8_0": "qwen2.5 14B (8-bit)", "qwen3:14b": "qwen3 14B", "qwen3:32b": "qwen3 32B",
    "qwen3:30b-a3b": "qwen3 30B-A3B thinking (MoE)", "qwen3:30b-a3b-instruct-2507-q4_K_M": "qwen3 30B-A3B (MoE)", "gpt-oss:20b": "gpt-oss 20B (MoE)",
}


def latest(pattern, key, gpu=None):
    """Latest row per key. gpu: substring of the run note that names the machine (e.g. "RTX 3080"),
    so two machines measured on the same date never mix. Host fields/filenames are never shown."""
    rows = {}
    for f in sorted(glob.glob(str(HERE / "results" / pattern))):
        if f.endswith(("-v2.jsonl", "-v2.events.jsonl")):
            continue  # even an interrupted v2 write cannot break this legacy publication
        if pattern == "*.jsonl" and f.endswith("-ctx.jsonl"):
            continue
        for line in pathlib.Path(f).read_text().splitlines():
            r = json.loads(line)
            # This publication describes the original experiment only. New sessions
            # require a reviewed comparison, not silent replacement of historical rows.
            if r.get("schema_version", 1) != 1:
                continue
            if gpu and gpu not in r.get("note", ""):
                continue
            if key(r) not in rows or r["ts"] >= rows[key(r)]["ts"]:
                rows[key(r)] = r
    return rows


def render_report(markdown):
    """Render the small Markdown subset used by REPORT.md without dependencies."""
    def inline(s):
        parts = re.split(r'(`[^`]+`|\[[^]]+\]\([^)]+\)|\*\*[^*]+\*\*|\*[^*]+\*)', s)
        out = []
        for p in parts:
            if p.startswith('`'):
                out.append('<code>' + html.escape(p[1:-1]) + '</code>')
            elif p.startswith('['):
                m = re.fullmatch(r'\[([^]]+)\]\(([^)]+)\)', p)
                out.append(f'<a href="{html.escape(m[2], quote=True)}">{html.escape(m[1].strip("`"))}</a>' if m else html.escape(p))
            elif p.startswith('**'):
                out.append('<strong>' + html.escape(p[2:-2]) + '</strong>')
            elif p.startswith('*'):
                out.append('<em>' + html.escape(p[1:-1]) + '</em>')
            else:
                out.append(html.escape(p))
        return ''.join(out)

    lines = markdown.splitlines(); out = []; i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip(): i += 1; continue
        if line.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[:\-| ]+\|$', lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip('|').split('|')]); i += 1
            cells = ''.join('<th scope="col">' + inline(c) + '</th>' for c in rows[0])
            body = ''
            for row in rows[2:]:
                body += '<tr>' + ''.join(('<th scope="row">' if j == 0 else '<td>') + inline(c) + ('</th>' if j == 0 else '</td>') for j, c in enumerate(row)) + '</tr>'
            prose = any(len(c) > 60 for r in rows[2:] for c in r)  # a word list, not numbers: wrap and left-align
            out.append('<div class="table-scroll" tabindex="0"><table' + (' class="prose"' if prose else '') + '><thead><tr>' + cells + '</tr></thead><tbody>' + body + '</tbody></table></div>')
            continue
        m = re.match(r'^(#{1,3}) (.+)$', line)
        if m:
            level = len(m[1]); slug = re.sub(r'[^a-z0-9]+', '-', m[2].lower()).strip('-')
            out.append(f'<h{level} id="{slug}">{inline(m[2])}</h{level}>'); i += 1; continue
        if line.startswith('- '):
            items = []
            while i < len(lines) and lines[i].startswith('- '):
                items.append('<li>' + inline(lines[i][2:]) + '</li>'); i += 1
            out.append('<ul class="findings">' + ''.join(items) + '</ul>'); continue
        paragraph = [line.strip()]; i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '|', '- ')):
            paragraph.append(lines[i].strip()); i += 1
        out.append('<p>' + inline(' '.join(paragraph)) + '</p>')
    return '\n'.join(out)


def main():
    # Select each machine's rows by the GPU named in its run note; never expose filenames or host fields.
    speed = latest("*.jsonl", lambda r: r["model"], gpu="RTX 3080")
    second_speed = latest("*.jsonl", lambda r: r["model"], gpu="RTX 2070 SUPER")
    mac_speed = latest("*.jsonl", lambda r: r["model"], gpu="Apple M3")
    ctx = latest("*-ctx.jsonl", lambda r: r["model"])
    models = sorted(speed.values(), key=lambda r: -r["short"]["gen_tps"])
    second_models = sorted(second_speed.values(), key=lambda r: -r["short"]["gen_tps"])
    mac_models = sorted(mac_speed.values(), key=lambda r: -r["short"]["gen_tps"])

    def result_row(r):
        q = r["quality"]
        trunc = sum(1 for t in q["tasks"] if t.get("truncated"))
        size = r.get("size_gb")
        share = r.get("vram_pct")
        tasks = "n/a (speed only)" if r["model"] in UNGRADED else f"{q['passed']}/{q['total']}" + (f" ({trunc} cut off)" if trunc else "")
        return (f"| {NICE.get(r['model'], r['model'])} | {size if size is not None else 'Not recorded'} | "
                f"{str(share) + '%' if share is not None else 'Not recorded'} | "
                f"{r['short']['gen_tps']} | {r['long']['gen_tps']} | {r['cold_load_s']} | {tasks} |")

    # ---------- RESULTS.md ----------
    md = ["# Results", "", "## RTX 3080 12 GB", "", "Ollama 0.32.5; measurements on 2026-11-02. Latest legacy row per model on this GPU; schema 2 sessions are excluded. "
          "Under the harness default, generation rates are medians of three calls per prompt (run count was "
          "not saved); load and tasks are single calls. The stored cold_load_s field is a first-request "
          "load duration, not a verified cold start: that historical harness did not force an unload. "
          "GPU share is Ollama's reported allocation ratio. See [REPORT.md](REPORT.md) for method and limitations.", "",
          "| model | allocation GB | GPU share | short gen tok/s | long gen tok/s | first load s | tasks |",
          "|---|---:|---:|---:|---:|---:|---|"]
    for r in models:
        md.append(result_row(r))
    md += ["", "## RTX 2070 SUPER 8 GB", "", "Ollama 0.32.1; measurements on 2026-11-05. Latest legacy row per model on this GPU; schema 2 sessions are excluded. "
           "Generation rates use the same harness default; run count was not saved. "
           "Mistral allocation and GPU share were not recorded because the earlier `/api/ps` lookup missed its `:latest` tag.", "",
           "| model | allocation GB | GPU share | short gen tok/s | long gen tok/s | first load s | tasks |",
           "|---|---:|---:|---:|---:|---:|---|"]
    for r in second_models:
        md.append(result_row(r))
    md += ["", "## Apple M3 16 GB unified", "", "Ollama 0.40.14; measurements on 2026-11-05. Latest legacy row per model on this machine; schema 2 sessions are excluded. "
           "Generation rates use the same harness default; run count was not saved. "
           "GPU share is Ollama's reported allocation ratio in a shared CPU/GPU memory pool, not a discrete VRAM boundary.", "",
           "| model | allocation GB | GPU share | short gen tok/s | long gen tok/s | first load s | tasks |",
           "|---|---:|---:|---:|---:|---:|---|"]
    for r in mac_models:
        md.append(result_row(r))
    md += ["", "## Shared tags: short generation", "", "`mistral` resolves to `mistral:latest`; "
           "model digests were not stored. A dash means the tag was not measured on that machine.", "",
           "| model | RTX 3080 12 GB share | RTX 3080 12 GB tok/s | RTX 2070 SUPER 8 GB share | RTX 2070 SUPER 8 GB tok/s | Apple M3 16 GB unified share | Apple M3 16 GB unified tok/s |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for first_tag, other_tag in (("mistral:latest", "mistral"), ("qwen2.5:7b", "qwen2.5:7b"),
                                 ("qwen2.5:14b-instruct-q3_K_M", "qwen2.5:14b-instruct-q3_K_M"),
                                 ("qwen2.5:14b", "qwen2.5:14b")):
        def pair(row):
            if row is None:
                return "— | —"
            share = row.get("vram_pct")
            return f"{str(share) + '%' if share is not None else 'Not recorded'} | {row['short']['gen_tps']}"
        md.append(f"| {NICE[first_tag]} | {pair(speed.get(first_tag))} | "
                  f"{pair(second_speed.get(other_tag))} | {pair(mac_speed.get(other_tag))} |")
    md += ["", "Main-row long-prompt `prompt_tps` is omitted: repeated identical prompts produced implausible "
           "whole-prompt rates and per-call timings were not stored. The first three RTX 3080 speed rows "
           "have no truncation flag, so their cutoff status is unknown.", "",
           "## RTX 3080 12 GB context window sweep (prompt fills about 58–60% of the window)", "",
           "One call per setting. Prompt rates are API-reported single-call observations; cache diagnostics "
           "were not stored. The MoE sweep used a thinking tag distinct from the instruct tag above.", "",
           "| model | window | prompt tokens | allocation GB | GPU share | gen tok/s | API prompt tok/s |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for m, r in sorted(ctx.items()):
        for s in r["sweep"]:
            md.append(f"| {NICE.get(m, m)} | {s['num_ctx']:,} | {s['prompt_tokens']:,} | {s['size_gb']} | {s['vram_pct']}% | {s['gen_tps']} | {s['prompt_tps']:,} |")
    (HERE / "RESULTS.md").write_text("\n".join(md) + "\n")

    # ---------- report.html ----------
    W, H, L, R, T, B = 760, 400, 58, 28, 18, 54

    def sx(v, lo, hi): return L + (v - lo) / (hi - lo) * (W - L - R)
    def sy(v, hi): return H - B - v / hi * (H - T - B)

    ymax = 160
    grid = "".join(f'<line class="g" x1="{L}" x2="{W-R}" y1="{sy(v, ymax):.1f}" y2="{sy(v, ymax):.1f}"/>'
                   f'<text class="ax" x="{L-8}" y="{sy(v, ymax)+4:.1f}" text-anchor="end">{v}</text>' for v in range(0, ymax + 1, 40))
    xt = "".join(f'<text class="ax" x="{sx(v, 40, 100):.1f}" y="{H-B+20}" text-anchor="middle">{v}%</text>' for v in range(40, 101, 10))
    pts = ""
    for r in models:
        if "vram_pct" not in r or (r["model"] == "qwen3:30b-a3b" and INSTRUCT in speed): continue
        x, y = sx(r["vram_pct"], 40, 100), sy(r["short"]["gen_tps"], ymax)
        moe = r["model"] in MOE
        tip = f"{NICE.get(r['model'], r['model'])}: {r['short']['gen_tps']} tok/s, {r['vram_pct']}% reported GPU allocation share, {r['size_gb']} GB"
        shape = (f'<path class="mk moe" d="M{x:.1f} {y-8:.1f} L{x+8:.1f} {y:.1f} L{x:.1f} {y+8:.1f} L{x-8:.1f} {y:.1f}Z"/>' if moe
                 else f'<circle class="mk dense" cx="{x:.1f}" cy="{y:.1f}" r="6.5"/>')
        pts += f'<g data-tip="{html.escape(tip)}" tabindex="0">{shape}</g>'
        # Exact labels appear in the table; point labels collide at 100% fit.
    chart1 = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-label="Scatter plot of reported GPU allocation share versus short-prompt generation speed. Exact values appear in the results table.">
{grid}<line class="g" x1="{L}" x2="{W-R}" y1="{H-B}" y2="{H-B}" style="stroke:var(--axis)"/>{xt}
<text class="ax" x="{(L+W-R)/2}" y="{H-8}" text-anchor="middle">RTX 3080 12 GB: reported GPU allocation share</text>
<text class="ax" transform="translate(14 {(T+H-B)/2}) rotate(-90)" text-anchor="middle">tokens per second (higher = faster)</text>{pts}</svg>'''

    # context sweep lines
    series = [(m, "moe" if m in MOE else "dense") for m in ctx]
    cw, cl = [2048, 8192, 16384, 32768], ["2k", "8k", "16k", "32k"]
    def cx(i): return L + 40 + i * (W - L - R - 170) / 3
    lines = ""
    for m, kind in series:
        sw = {s["num_ctx"]: s for s in ctx[m]["sweep"]}
        pl = [(cx(i), sy(sw[c]["gen_tps"], 80)) for i, c in enumerate(cw) if c in sw]
        lines += f'<polyline class="ln {kind}" points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pl)}"/>'
        for i, c in enumerate(cw):
            if c not in sw: continue
            s = sw[c]; x, y = cx(i), sy(sw[c]["gen_tps"], 80)
            tip = f"{NICE.get(m, m)} at {cl[i]} context: {s['gen_tps']} tok/s, {s['vram_pct']}% reported GPU allocation share, {s['size_gb']} GB"
            shape = (f'<path class="mk moe" d="M{x:.1f} {y-7:.1f} L{x+7:.1f} {y:.1f} L{x:.1f} {y+7:.1f} L{x-7:.1f} {y:.1f}Z"/>' if kind == "moe"
                     else f'<circle class="mk dense" cx="{x:.1f}" cy="{y:.1f}" r="5.5"/>')
            lines += f'<g data-tip="{html.escape(tip)}" tabindex="0">{shape}</g>'
    grid2 = "".join(f'<line class="g" x1="{L}" x2="{W-R}" y1="{sy(v, 80):.1f}" y2="{sy(v, 80):.1f}"/>'
                    f'<text class="ax" x="{L-8}" y="{sy(v, 80)+4:.1f}" text-anchor="end">{v}</text>' for v in range(0, 81, 20))
    xt2 = "".join(f'<text class="ax" x="{cx(i):.1f}" y="{H-B+20}" text-anchor="middle">{l}</text>' for i, l in enumerate(cl))
    chart2 = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-label="Lines: tokens per second as the context window grows from 2k to 32k, for a regular 14B model and a mixture-of-experts 30B model.">
{grid2}<line class="g" x1="{L}" x2="{W-R}" y1="{H-B}" y2="{H-B}" style="stroke:var(--axis)"/>{xt2}
<text class="ax" x="{(L+W-R)/2}" y="{H-8}" text-anchor="middle">configured context window (tokens; actual prompt counts are in the table)</text>
<text class="ax" transform="translate(14 {(T+H-B)/2}) rotate(-90)" text-anchor="middle">tokens per second</text>{lines}</svg>'''

    article = render_report((HERE / "REPORT.md").read_text())
    charts = f'''<section class="charts" aria-label="RTX 3080 12 GB benchmark charts"><h2>RTX 3080 12 GB generation speed charts</h2>
<p>Both charts show only RTX 3080 12 GB measurements. The scatter plot uses the latest legacy speed row per tag; new schema 2 sessions are excluded. The thinking MoE point overlaps the instruct point and is omitted from that plot. The context chart uses the thinking tag; each setting has one call. All three machines appear in the tables below.</p>
<div class="chart-grid"><figure><figcaption>GPU allocation share and generation speed</figcaption><div class="leg"><span><i class="d"></i>dense</span><span><i class="m"></i>MoE</span></div><div class="chart-scroll">{chart1}</div></figure>
<figure><figcaption>Generation speed by context window</figcaption><div class="leg"><span><i class="d"></i>14B Q4</span><span><i class="m"></i>30B-A3B thinking MoE</span></div><div class="chart-scroll">{chart2}</div></figure></div></section>'''
    article = article.replace('<h2 id="results">Results</h2>', charts + '<h2 id="results">Results</h2>', 1)
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Local LLM inference on two NVIDIA cards and an Apple M3</title><style>
:root{{--bg:#f7f8fa;--card:#fff;--ink:#17212d;--ink2:#516171;--line:#d7dee5;--axis:#9aa8b4;--dense:#1767a5;--moe:#bd5a27;--stripe:#f2f5f8}}
@media(prefers-color-scheme:dark){{:root{{--bg:#101820;--card:#17232d;--ink:#edf3f7;--ink2:#b9c8d3;--line:#344553;--axis:#7e94a4;--dense:#69b9ef;--moe:#f3a276;--stripe:#1c2c38}}}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.top{{background:var(--card);border-bottom:1px solid var(--line)}}.top-inner{{max-width:1120px;margin:auto;padding:13px 24px;display:flex;gap:24px;justify-content:space-between;align-items:center}}.brand{{font-size:.85rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--ink2)}}nav{{display:flex;gap:18px;flex-wrap:wrap}}a{{color:var(--dense);text-underline-offset:3px}}nav a{{text-decoration:none;font-size:.9rem;font-weight:600}}
main{{max-width:1120px;margin:auto;padding:50px 24px 100px}}h1{{font-size:clamp(2rem,5vw,3.4rem);line-height:1.12;letter-spacing:-.035em;max-width:18ch;margin:0 0 14px}}h1+p{{color:var(--ink2);font-weight:600;margin:0 0 42px}}h2{{font-size:1.65rem;line-height:1.25;letter-spacing:-.02em;margin:60px 0 16px;padding-top:8px;border-top:1px solid var(--line)}}h3{{font-size:1.15rem;margin:34px 0 12px}}p{{max-width:78ch;margin:0 0 18px}}code{{font-size:.9em;background:var(--stripe);padding:.12em .3em;border-radius:4px}}
.findings{{max-width:90ch;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;list-style:none;padding:0;margin:0}}.findings li{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 20px;line-height:1.5}}
.chart-grid{{display:grid;grid-template-columns:1fr;gap:18px}}figure{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;min-width:0;max-width:850px}}figcaption{{font-weight:700;font-size:1.05rem}}.charts>p{{color:var(--ink2)}}svg{{width:100%;height:auto;display:block}}svg text{{fill:var(--ink2);font:13px system-ui,sans-serif}}.g{{stroke:var(--line);stroke-width:1}}.mk{{stroke:var(--card);stroke-width:2}}.mk.dense{{fill:var(--dense)}}.mk.moe{{fill:var(--moe)}}.ln{{fill:none;stroke-width:2.5}}.ln.dense{{stroke:var(--dense)}}.ln.moe{{stroke:var(--moe)}}g[data-tip]:hover .mk,g[data-tip]:focus .mk{{stroke:var(--ink)}}g:focus{{outline:none}}
.leg{{display:flex;gap:20px;color:var(--ink2);font-size:.85rem;margin:4px 0 8px;flex-wrap:wrap}}.leg i{{display:inline-block;width:11px;height:11px;vertical-align:-1px;margin-right:6px}}.leg .d{{background:var(--dense);border-radius:50%}}.leg .m{{background:var(--moe);transform:rotate(45deg) scale(.85)}}
.table-scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card);margin:18px 0 22px}}table{{width:100%;border-collapse:collapse;font-size:.9rem;font-variant-numeric:tabular-nums;white-space:nowrap}}thead{{background:var(--stripe)}}th,td{{padding:10px 13px;border-bottom:1px solid var(--line);text-align:right}}th:first-child{{text-align:left}}tbody th{{font-weight:600}}tbody tr:last-child>*{{border-bottom:0}}tbody tr:hover{{background:var(--stripe)}}table.prose{{white-space:normal}}table.prose th,table.prose td{{text-align:left;vertical-align:top}}table.prose tbody th{{white-space:nowrap}}.table-scroll:focus{{outline:2px solid var(--dense);outline-offset:2px}}
#tip{{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);padding:8px 10px;border-radius:8px;font-size:14px;max-width:min(320px,80vw);display:none;z-index:9}}
@media(max-width:800px){{.chart-grid,.findings{{grid-template-columns:1fr}}.chart-scroll{{overflow-x:auto}}.chart-scroll svg{{min-width:620px}}}}
@media(max-width:520px){{main{{padding:32px 16px 70px}}.top-inner{{padding:12px 16px;display:block}}nav{{margin-top:6px;gap:12px}}h2{{margin-top:44px}}figure{{padding:14px}}.findings li{{padding:15px}}}}
</style></head><body><header class="top"><div class="top-inner"><span class="brand">llmbench / technical report</span><nav aria-label="Report sections"><a href="#the-short-version">Short version</a><a href="#follow-up-what-i-actually-reran-on-9-november">9 November follow-up</a><a href="#summary">Original experiment</a><a href="#results">Results</a><a href="#limitations-of-these-benchmarks">Limitations</a><a href="#what-i-want-local-and-frontier-models-to-do">Hybrid workflow</a><a href="#what-i-would-test-with-two-halos">Two Halos</a><a href="EVIDENCE.md">Evidence</a><a href="#further-reading">Reading</a></nav></div></header><main><article>{article}</article></main><div id="tip"></div><script>
const tip=document.getElementById('tip');document.querySelectorAll('[data-tip]').forEach(e=>{{
e.addEventListener('mousemove',v=>{{tip.textContent=e.dataset.tip;tip.style.display='block';tip.style.left=Math.max(8,Math.min(v.clientX+14,innerWidth-tip.offsetWidth-8))+'px';tip.style.top=(v.clientY+14)+'px'}});
e.addEventListener('mouseleave',()=>tip.style.display='none');
e.addEventListener('focus',()=>{{const b=e.getBoundingClientRect();tip.textContent=e.dataset.tip;tip.style.display='block';tip.style.left=Math.max(8,Math.min(b.left,innerWidth-tip.offsetWidth-8))+'px';tip.style.top=(b.bottom+8)+'px'}});
e.addEventListener('blur',()=>tip.style.display='none')}});
</script></body></html>'''
    (HERE / "report.html").write_text(page)
    print("wrote RESULTS.md and report.html;", len(models), "RTX 3080 models,", len(second_models), "RTX 2070 SUPER models,", len(mac_models), "Apple M3 models,", len(ctx), "context sweeps")


if __name__ == "__main__":
    main()
