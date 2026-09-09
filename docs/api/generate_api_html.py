import json, html, re, pathlib, sys

S = sys.argv[1]
OUT = sys.argv[2]
api = json.load(open(f"{S}/openapi.json", encoding="utf-8"))
roles = json.load(open(f"{S}/roles_full.json", encoding="utf-8"))
roles.setdefault("GET /health", "public")
SCHEMAS = api.get("components", {}).get("schemas", {})
e = html.escape


def deref(s):
    seen = 0
    while isinstance(s, dict) and "$ref" in s and seen < 10:
        s = SCHEMAS.get(s["$ref"].split("/")[-1], {})
        seen += 1
    return s if isinstance(s, dict) else {}


def typename(s, depth=0):
    s = deref(s)
    if depth > 4 or not s:
        return "object"
    if "anyOf" in s:
        parts = [typename(x, depth + 1) for x in s["anyOf"]]
        nn = [p for p in parts if p != "null"]
        base = nn[0] if len(nn) == 1 else " | ".join(nn)
        return base + (" | null" if "null" in parts else "")
    if s.get("type") == "array":
        return typename(s.get("items", {}), depth + 1) + "[]"
    if "enum" in s:
        return " | ".join('"%s"' % v for v in s["enum"])
    t = s.get("type", "object")
    fmt = s.get("format")
    nice = {"integer": "int", "number": "number", "boolean": "bool", "string": "string"}.get(t, t)
    return nice + (" (%s)" % fmt if fmt and fmt != "email" else "")


def constraints(s):
    s = deref(s)
    bits = []
    pairs = (("minimum", "min"), ("maximum", "max"), ("minLength", "minLen"), ("maxLength", "maxLen"))
    for k, lbl in pairs:
        if k in s:
            bits.append("%s %s" % (lbl, s[k]))
    for sub in s.get("anyOf", []):
        sub = deref(sub)
        for k, lbl in pairs:
            if k in sub and "%s %s" % (lbl, sub[k]) not in bits:
                bits.append("%s %s" % (lbl, sub[k]))
    return ", ".join(bits)


def fields(schema):
    s = deref(schema)
    if s.get("type") == "array":
        s = deref(s.get("items", {}))
    props = s.get("properties") or {}
    if not props:
        return ""
    req = set(s.get("required", []))
    rows = []
    for name, spec in props.items():
        sd = deref(spec)
        desc = spec.get("description") or sd.get("description") or ""
        c = constraints(spec)
        if c:
            desc = (desc + " · " if desc else "") + c
        rows.append(
            '<tr><td class="fname">%s</td><td class="ftype">%s</td>'
            '<td class="freq">%s</td><td class="fdesc">%s</td></tr>'
            % (e(name), e(typename(spec)), "required" if name in req else "—", e(desc))
        )
    return ('<div class="tblwrap"><table class="fields"><thead><tr><th>Field</th><th>Type</th>'
            '<th>Required</th><th>Notes</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')


ROLE_CLASS = {
    "admin": "r-admin", "perawat + admin": "r-nurse", "dokter": "r-doc",
    "any signed-in role": "r-any", "public": "r-public",
    "IoT device (X-Device-Key)": "r-device",
}
M_ORDER = {"GET": 0, "POST": 1, "PUT": 2, "PATCH": 3, "DELETE": 4}

groups = {}
for path, ops in api["paths"].items():
    for method, op in ops.items():
        tag = (op.get("tags") or ["Other"])[0]
        groups.setdefault(tag, []).append((method.upper(), path, op))
for g in groups.values():
    g.sort(key=lambda x: (x[1], M_ORDER.get(x[0], 9)))

TAG_ORDER = ["Health", "Auth", "Dashboard", "Incubators", "Telemetry", "Telemetry (legacy)",
             "Babies", "Monitoring", "Observation", "Involvement", "Aksi", "Doctor Notes",
             "Reports", "Users", "Audit"]
ordered = [t for t in TAG_ORDER if t in groups] + [t for t in groups if t not in TAG_ORDER]

TAG_NOTE = {
    "Telemetry": "The only endpoint an incubator device may reach. Authenticated by "
                 "<code>X-Device-Key</code>, never a JWT.",
    "Telemetry (legacy)": "Prototype-firmware ingest, identified by a payload label rather than a key. "
                          "Answers <b>404</b> unless <code>LEGACY_SENSOR_INGEST</code> is enabled, because "
                          "it authenticates nobody.",
    "Incubators": "Also carries device provisioning, alert thresholds, the SSE reading stream and the "
                  "chart backfill.",
    "Reports": "Per-baby clinical summary, as JSON or a generated PDF.",
    "Audit": "Append-only trail of writes.",
    "Auth": "JWT issue and introspection. Every seeded account uses the same demo password.",
}

nav, body = [], []
for tag in ordered:
    items = groups[tag]
    slug = re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")
    nav.append('<a href="#%s"><span>%s</span><span class="navcount">%d</span></a>'
               % (slug, e(tag), len(items)))
    eps = []
    for method, path, op in items:
        role = roles.get("%s %s" % (method, path), "—")
        rc = ROLE_CLASS.get(role, "r-any")
        desc = (op.get("description") or "").strip()
        summary = (op.get("summary") or "").strip()
        paras = [p.replace("\n", " ").strip() for p in desc.split("\n\n") if p.strip()]
        lead = paras[0] if paras else summary
        rest = paras[1:]

        params = op.get("parameters") or []
        pblock = ""
        if params:
            rows = "".join(
                '<tr><td class="fname">%s</td><td class="ftype">%s</td><td class="freq">%s</td>'
                '<td class="fdesc">in %s%s</td></tr>'
                % (e(p["name"]), e(typename(p.get("schema", {}))),
                   "required" if p.get("required") else "—", e(p["in"]),
                   " · " + e(p.get("description", "")) if p.get("description") else "")
                for p in params)
            pblock = ('<h4>Parameters</h4><div class="tblwrap"><table class="fields"><thead><tr>'
                      '<th>Name</th><th>Type</th><th>Required</th><th>Notes</th></tr></thead><tbody>'
                      + rows + '</tbody></table></div>')

        rb = (op.get("requestBody", {}).get("content", {})
                .get("application/json", {}).get("schema"))
        rbblock = ("<h4>Request body</h4>" + fields(rb)) if rb else ""

        rrows = []
        for code, r in sorted(op.get("responses", {}).items()):
            sch = (r.get("content") or {}).get("application/json", {}).get("schema")
            cls = "ok" if code.startswith("2") else ("warn" if code.startswith("4") else "bad")
            rrows.append('<tr><td><span class="code %s">%s</span></td><td class="fdesc">%s</td>'
                         '<td class="ftype">%s</td></tr>'
                         % (cls, e(code), e(r.get("description", "")), e(typename(sch) if sch else "—")))
        rblock = ('<h4>Responses</h4><div class="tblwrap"><table class="fields"><thead><tr>'
                  '<th>Status</th><th>Meaning</th><th>Body</th></tr></thead><tbody>'
                  + "".join(rrows) + '</tbody></table></div>')

        notes = "".join("<p>%s</p>" % e(p) for p in rest)
        more = ('<details class="more"><summary>Design notes</summary>%s</details>' % notes) if notes else ""
        leadp = ('<p class="lead">%s</p>' % e(lead)) if lead else ""
        eps.append(
            '<article class="ep" data-q="%s">'
            '<div class="epline"><span class="m m-%s">%s</span><code class="path">%s</code>'
            '<span class="role %s">%s</span></div>%s%s%s%s%s</article>'
            % (e((method + " " + path + " " + lead).lower()), method.lower(), method, e(path),
               rc, e(role), leadp, more, pblock, rbblock, rblock))
    note = '<p class="tagnote">%s</p>' % TAG_NOTE[tag] if tag in TAG_NOTE else ""
    body.append('<section id="%s" class="tag"><h2>%s</h2>%s%s</section>'
                % (slug, e(tag), note, "".join(eps)))

info = api["info"]
total = sum(len(v) for v in groups.values())

CSS = """
/* Sengaja satu tema saja: TERANG, di perangkat apa pun.
   Dashboard (web/app/globals.css) tidak mendefinisikan tema gelap sama sekali,
   sehingga selalu terang. Menghormati prefers-color-scheme di sini justru membuat
   dokumen dan aplikasi berbeda rupa pada perangkat bermode gelap - persis yang
   ingin dihindari. Setiap warna tetap ditulis eksplisit, termasuk latar body,
   supaya halaman tidak meminjam warna dasar peramban. */
:root{
  /* Diambil persis dari web/app/globals.css @theme — dokumen ini harus terlihat
     seperti aplikasinya, bukan seperti dokumen yang kebetulan bertema mirip. */
  --primary:#2563EB; --primary-dark:#1D4ED8; --accent:#0EA5E9;
  --surface:#F4F7FB; --card:#FFFFFF; --ink:#0F172A;
  --ink-muted:#64748B; --ink-faint:#94A3B8; --line:#E9EEF5; --line-strong:#D7E0EC;
  --ok:#10B981; --warn:#F59E0B; --bad:#EF4444;
  --sans:Manrope,ui-sans-serif,system-ui,-apple-system,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --radius-card:18px;
  --shadow-card:0 8px 24px -6px rgba(30,41,59,.10), 0 2px 6px -2px rgba(15,23,42,.05);
  --shadow-soft:0 4px 14px -4px rgba(16,24,40,.08);
}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{display:grid;grid-template-columns:250px minmax(0,1fr);gap:40px;
  max-width:1180px;margin:0 auto;padding:0 28px 80px}
@media(max-width:880px){
  .wrap{grid-template-columns:1fr;gap:0}
  .rail{position:static;height:auto;padding-top:10px;margin-bottom:24px}
}
header.masthead{border-bottom:1px solid var(--line);background:var(--card)}
.mast-in{max-width:1180px;margin:0 auto;padding:34px 28px 26px}
.eyebrow{font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-faint);margin:0 0 10px}
h1{font-family:var(--sans);font-weight:700;font-size:32px;line-height:1.15;margin:0 0 10px;
  text-wrap:balance;letter-spacing:-.01em}
.sub{color:var(--ink-muted);margin:0;max-width:64ch}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.chip{font-family:var(--mono);font-size:12px;border:1px solid var(--line-strong);border-radius:999px;
  padding:4px 11px;color:var(--ink-muted);background:var(--surface)}
.chip b{color:var(--ink);font-weight:600}
.auth{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px;margin-top:22px}
.auth div{border:1px solid var(--line);border-radius:var(--radius-card);
  padding:14px 17px;background:var(--surface)}
.auth h3::before{content:'';display:inline-block;width:8px;height:8px;border-radius:50%;
  background:var(--primary);margin-right:8px;vertical-align:middle}
.auth div.dev h3::before{background:var(--accent)}
.auth h3{margin:0 0 5px;font-size:13px;font-family:var(--mono);letter-spacing:.01em;font-weight:600}
.auth p{margin:0;font-size:13.5px;color:var(--ink-muted)}
.rail{position:sticky;top:0;align-self:start;height:100vh;overflow-y:auto;padding-top:34px}
.search{width:100%;font-family:var(--sans);font-size:13.5px;padding:8px 11px;border-radius:8px;
  border:1px solid var(--line-strong);background:var(--card);color:var(--ink);margin-bottom:14px}
.search:focus{outline:2px solid var(--primary);outline-offset:1px}
.rail a{display:flex;justify-content:space-between;gap:8px;text-decoration:none;
  color:var(--ink-muted);font-size:13.5px;padding:5px 9px;border-radius:6px}
.rail a:hover,.rail a:focus-visible{background:var(--card);color:var(--ink)}
.navcount{font-family:var(--mono);font-size:11.5px;color:var(--ink-faint);
  font-variant-numeric:tabular-nums}
main{padding-top:34px}
.tag{margin:0 0 46px;scroll-margin-top:16px}
.tag h2{font-family:var(--sans);font-size:21px;margin:0 0 7px;padding-bottom:9px;
  border-bottom:2px solid var(--line-strong)}
.tagnote{color:var(--ink-muted);font-size:13.5px;margin:0 0 16px;max-width:72ch}
.tagnote code{font-family:var(--mono);font-size:12.5px;background:var(--line);
  padding:1px 5px;border-radius:4px}
.ep{background:var(--card);border:1px solid var(--line);border-radius:var(--radius-card);
  padding:17px 19px;margin-bottom:12px;box-shadow:var(--shadow-soft)}
.epline{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.m{font-family:var(--mono);font-size:11.5px;font-weight:600;letter-spacing:.05em;color:#fff;
  padding:3px 8px;border-radius:5px}
.m-get{background:var(--accent)} .m-post{background:var(--ok)}
.m-put{background:var(--warn)} .m-patch{background:var(--warn)} .m-delete{background:var(--bad)}
.path{font-family:var(--mono);font-size:13.5px;font-weight:500;word-break:break-all}
.role{margin-left:auto;font-size:11.5px;font-family:var(--mono);padding:3px 9px;
  border-radius:999px;border:1px solid var(--line-strong);color:var(--ink-muted);white-space:nowrap}
.r-admin{border-color:var(--bad);color:var(--bad)}
.r-nurse{border-color:var(--primary);color:var(--primary)}
.r-doc{border-color:var(--warn);color:var(--warn)}
.r-device{border-color:var(--accent);color:var(--accent)}
.r-public{border-color:var(--ok);color:var(--ok)}
.lead{margin:10px 0 0;color:var(--ink-muted);font-size:14px;max-width:74ch}
.more{margin-top:9px}
.more summary{cursor:pointer;font-size:12.5px;color:var(--primary);font-family:var(--mono)}
.more summary:focus-visible{outline:2px solid var(--primary);outline-offset:2px}
.more p{color:var(--ink-muted);font-size:13.5px;max-width:74ch}
h4{font-family:var(--mono);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-faint);margin:18px 0 7px;font-weight:600}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
table.fields{border-collapse:collapse;width:100%;font-size:13px}
table.fields th{text-align:left;font-weight:600;font-size:11.5px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--ink-faint);padding:8px 12px;background:var(--surface);
  border-bottom:1px solid var(--line);white-space:nowrap}
table.fields td{padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
table.fields tr:last-child td{border-bottom:0}
.fname{font-family:var(--mono);font-weight:500;white-space:nowrap}
.ftype{font-family:var(--mono);color:var(--primary);font-size:12.5px}
.freq{font-size:12px;color:var(--ink-muted);white-space:nowrap}
.fdesc{color:var(--ink-muted);min-width:210px}
.code{font-family:var(--mono);font-weight:600;font-size:12.5px;font-variant-numeric:tabular-nums}
.code.ok{color:var(--ok)} .code.warn{color:var(--warn)} .code.bad{color:var(--bad)}
.empty{display:none;color:var(--ink-muted);padding:20px 0}
footer{max-width:1180px;margin:0 auto;padding:24px 28px 60px;color:var(--ink-faint);
  font-size:12.5px;border-top:1px solid var(--line);max-width:1180px}
footer code{font-family:var(--mono)}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

JS = """
const q=document.getElementById('q');
const eps=Array.from(document.querySelectorAll('.ep'));
const secs=Array.from(document.querySelectorAll('.tag'));
const empty=document.getElementById('empty');
q.addEventListener('input',function(){
  const v=q.value.trim().toLowerCase();
  let n=0;
  eps.forEach(function(el){
    const m=!v||el.dataset.q.indexOf(v)>-1;
    el.hidden=!m; if(m)n++;
  });
  secs.forEach(function(s){
    s.hidden=!Array.from(s.querySelectorAll('.ep')).some(function(el){return !el.hidden;});
  });
  empty.style.display=n?'none':'block';
});
"""

HTML = """<title>Neonatal Care API</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap">
<style>%s</style>

<header class="masthead"><div class="mast-in">
  <p class="eyebrow">Sistem Monitoring Bayi pada Inkubator</p>
  <h1>Neonatal Care API</h1>
  <p class="sub">HTTP reference for the FastAPI backend behind the NICU dashboard, the Flutter
  app and the incubator sensor rigs. Generated from the application's own OpenAPI schema, so it
  describes the code as it is deployed rather than as it is remembered.</p>
  <div class="meta">
    <span class="chip">version <b>%s</b></span>
    <span class="chip">base <b>/api/v1</b></span>
    <span class="chip"><b>%d</b> operations</span>
    <span class="chip"><b>%d</b> groups</span>
    <span class="chip">errors <b>{"detail": "…"}</b></span>
  </div>
  <div class="auth">
    <div>
      <h3>Authorization: Bearer &lt;jwt&gt;</h3>
      <p>People. Issued by <code>POST /api/v1/auth/login</code> and carrying the role — admin,
      perawat or dokter — that every endpoint below is gated on.</p>
    </div>
    <div class="dev">
      <h3>X-Device-Key: &lt;key&gt;</h3>
      <p>Incubator hardware. Minted once per incubator and stored only as a SHA-256. It resolves
      device → incubator → the baby currently assigned, which is why a rig never names a patient.</p>
    </div>
  </div>
</div></header>

<div class="wrap">
  <nav class="rail">
    <input class="search" id="q" type="search" placeholder="Filter endpoints…" aria-label="Filter endpoints">
    %s
  </nav>
  <main>
    %s
    <p class="empty" id="empty">No endpoint matches that filter.</p>
  </main>
</div>
<footer>Generated from the FastAPI OpenAPI schema. The role column is derived separately, from each
route's dependency guard in <code>app/api/deps.py</code> — the schema itself does not express it.</footer>
<script>%s</script>
""" % (CSS, e(info.get("version", "1.0.0")), total, len(groups), "".join(nav), "".join(body), JS)

pathlib.Path(OUT).write_text(HTML, encoding="utf-8")
print("  wrote %s (%s bytes, %d operations, %d groups)" % (OUT, format(len(HTML), ","), total, len(groups)))
