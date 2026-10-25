"""Build the main site: config + copy + each live industry's published data + web/ -> dist/ (static, no framework).

Numbers are never typed into the copy. They come from each live industry site's published aggregates
(for cafés: <café site>/data/insights.json), read at build time, so the front door always matches the industry
sites. pipeline/check.py then refuses any page that shows a number the data doesn't contain.

Usage: python pipeline/build.py [--data cafes=path/to/insights.json]
"""
import argparse, hashlib, html, json, re, shutil, sys, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parent.parent
WEB, DIST, CACHE = ROOT / "web", ROOT / "dist", ROOT / ".cache"
E = html.escape

PHOTOS = {
    "hawa-mahal-sky": ("The Hawa Mahal's pink sandstone face against a pale morning sky, Jaipur", "Nikunj Mundra", "https://unsplash.com/photos/W3qWtMNwRf0", 3200, 3706),
    "jantar-field": ("The instruments of Jantar Mantar below Nahargarh, Jaipur", "Ibrahim Rifath", "https://unsplash.com/photos/ZCa9LzaG_9M", 3200, 2134),
    "patrika-gate-sky": ("Patrika Gate against a clear sky, Jaipur", "Swaroop Satheesh", "https://unsplash.com/photos/n8r8CLJUo2o", 3200, 5689),
}
GRADE = {"Strong": 3, "Moderate": 2, "Weak": 1}


class BuildError(Exception):
    pass


# ---------- addresses: everything follows brand.domain ----------
def addresses(cfg):
    dom = (cfg["brand"].get("domain") or "").strip().strip("/").removeprefix("https://").removeprefix("http://")
    base = f"https://{dom}" if dom else cfg["now"]["base_url"].rstrip("/")
    for ind in cfg["industries"]:
        if ind["status"] == "candidate":
            ind["url"] = ""
        elif dom and ind.get("subdomain"):
            ind["url"] = f"https://{ind['subdomain']}.{dom}"
        else:
            ind["url"] = (ind.get("now_url") or "").rstrip("/")
    return dom, base


# ---------- data: each live industry's published aggregates ----------
def load_data(cfg, overrides):
    out = {}
    for ind in cfg["industries"]:
        if ind["status"] != "live" or not ind.get("data"):
            continue
        src = overrides.get(ind["key"])
        if src:
            raw = Path(src).read_text(encoding="utf-8")
        else:
            src = f"{ind['url']}/{ind['data']}"
            try:
                with urllib.request.urlopen(src, timeout=60) as r:
                    raw = r.read().decode("utf-8")
            except Exception as e:
                raise BuildError(f"could not read {ind['key']} data from {src}: {e}")
        d = json.loads(raw)
        d["_source"] = str(src)
        CACHE.mkdir(exist_ok=True)                       # check.py reads exactly what this build read
        (CACHE / f"{ind['key']}.json").write_text(raw, encoding="utf-8")
        out[ind["key"]] = d
    return out


def nice(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def tokens(cfg, data):
    T = {"brand": cfg["brand"]["name"]}
    for key, d in data.items():
        for k, v in (d.get("tokens") or {}).items():
            T[f"{key}.{k}"] = str(v)
        if key == "cafes":
            T["cafes.findings"] = str(len(findings(d)))
            T["cafes.updated"] = nice(d["meta"]["captured_on"])
    return T


def findings(d):
    I = d["insights"]
    return {f["id"]: f for f in (I.get("findings") or []) + ((I.get("survey") or {}).get("findings") or [])}


def num(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return f"{v:,}" if isinstance(v, int) else str(v)


# ---------- copy ----------
def fill(text, T, missing):
    """Escape the copy, set **lead-ins** in bold, swap {{token}} for its value. Unknown tokens are recorded, never guessed."""
    out = []
    for part in re.split(r"({{\s*[\w.]+\s*}})", text):
        m = re.fullmatch(r"{{\s*([\w.]+)\s*}}", part)
        if not m:
            out.append(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", E(part)))
        elif T.get(m.group(1)) in (None, "", "—"):
            missing.append(m.group(1))
            out.append("—")
        else:
            out.append(f'<span class="n">{E(T[m.group(1)])}</span>')
    return "".join(out)


def plain(text, T, missing):
    """For attributes and metadata: same tokens, no markup."""
    def sub(m):
        k = m.group(1)
        if k not in T:
            missing.append(k)
            return "—"
        return T[k]
    return re.sub(r"{{\s*([\w.]+)\s*}}", sub, text).replace("**", "")


def asset(name):
    """name?v=<content hash>: a new deploy changes the address, so no browser keeps an old copy."""
    src = WEB / name
    return f"{name}?v={hashlib.sha1(src.read_bytes()).hexdigest()[:10]}"


def pic(name, sizes, cls="", eager=False):
    alt, *_, w, h = PHOTOS[name]
    srcset = lambda ext: ", ".join(f"img/{name}-{s}.{ext} {s}w" for s in (900, 1600, 2400))
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<picture class="{cls}"><source type="image/webp" srcset="{srcset("webp")}" sizes="{sizes}">'
            f'<img src="img/{name}-1600.jpg" srcset="{srcset("jpg")}" sizes="{sizes}" width="{w}" height="{h}" alt="{E(alt)}" {load}></picture>')


def entities(s):
    """Email addresses as character references: readable to people, a little harder for scrapers."""
    return "".join(f"&#{ord(c)};" for c in s)


# ---------- the page ----------
def build(overrides):
    cfg = yaml.safe_load((ROOT / "site.config.yaml").read_text(encoding="utf-8"))
    C = yaml.safe_load((ROOT / "content" / "copy.yaml").read_text(encoding="utf-8"))
    dom, base = addresses(cfg)
    data = load_data(cfg, overrides)
    if "cafes" not in data:
        raise BuildError("the café index is the proof on this page; its data is required")
    T = tokens(cfg, data)
    F = findings(data["cafes"])
    missing = []
    f = lambda s: fill(s, T, missing)
    p = lambda s: plain(s, T, missing)
    brand, au = cfg["brand"]["name"], cfg["author"]
    ind = {i["key"]: i for i in cfg["industries"]}
    cafe = ind["cafes"]["url"]
    jewel = ind.get("jewellery", {})
    candidates = [i for i in cfg["industries"] if i["status"] == "candidate"]
    today = datetime.now(timezone.utc).date().isoformat()

    for group in ("hero_rotation", "proof"):
        for fid in cfg["findings"][group]:
            if fid not in F:
                raise BuildError(f"findings.{group}: '{fid}' is not in the café index's published findings")
            if not isinstance(F[fid].get("value"), (int, float)):
                raise BuildError(f"finding '{fid}' has no published value")

    mail = f"mailto:{au['email']}?subject={quote(au.get('email_subject', brand))}"
    sub = cfg.get("subscribe") or {}
    fields = sub.get("fields") or {}
    live_form = sub.get("provider") == "google_form" and sub.get("action") and all(fields.get(k) for k in ("name", "contact", "industries"))

    # ---------- head ----------
    title, desc = p(C["meta"]["title"]), p(" ".join(C["meta"]["description"].split()))
    person = {"@type": "Person", "@id": f"{base}/#author", "name": au["name"], "url": au["linkedin"], "sameAs": [au["linkedin"]],
              "jobTitle": "Data analyst", "image": f"{base}/img/sarthak-street-800.jpg",
              "homeLocation": {"@type": "City", "name": "Jaipur"}, "knowsAbout": ["Market research", "Data analysis", "Jaipur"]}
    sites = [i for i in cfg["industries"] if i["status"] == "live"]
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": f"{base}/#site", "name": brand, "url": f"{base}/", "inLanguage": "en-IN",
         "description": desc, "publisher": {"@id": f"{base}/#author"}},
        {"@type": "WebPage", "@id": f"{base}/#page", "url": f"{base}/", "name": title, "description": desc,
         "isPartOf": {"@id": f"{base}/#site"}, "about": {"@type": "City", "name": "Jaipur"},
         "primaryImageOfPage": f"{base}/og.jpg", "dateModified": today},
        person,
        {"@type": "ItemList", "name": f"{brand}: industry sites", "itemListElement": [
            {"@type": "ListItem", "position": n + 1, "item": {"@type": "WebSite", "name": i["name"], "url": f"{i['url']}/"}}
            for n, i in enumerate(sites)]},
    ]}
    og_alt = p(C["meta"]["og_alt"])
    head = f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{base}/">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="author" content="{E(au['name'])}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{E(brand)}">
<meta property="og:locale" content="en_IN">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{base}/">
<meta property="og:image" content="{base}/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{E(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{base}/og.jpg">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#f5f5f2">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script>document.documentElement.classList.add("js");setTimeout(function(){{if(!window.__pulse)document.documentElement.classList.remove("js","motion")}},3000)</script>
<link rel="preload" href="fonts/literata.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{asset('v2.css')}">
<link rel="stylesheet" href="{asset('master.css')}">
<script src="{asset('v2.js')}" defer></script>
<script src="{asset('master.js')}" defer></script>
</head>"""

    nav = "".join(f'<a href="{h}">{E(t)}</a>' for h, t in C["nav"])
    act_h, act_t = C["nav_action"]
    bar = (f'<header class="bar"><a class="wordmark" href="./">{E(brand)}</a><nav class="bar-links" aria-label="Main">{nav}</nav>'
           f'<details class="menu"><summary aria-label="Open the menu">Menu</summary><nav class="menu-panel" aria-label="Main">{nav}'
           f'<a href="{act_h}">{E(act_t)}</a></nav></details><a class="btn" href="{act_h}">{E(act_t)}</a></header>')

    # ---------- hero ----------
    rot_ids = cfg["findings"]["hero_rotation"]
    rot = [{"id": i, "value": num(F[i]["value"]), "unit": F[i].get("unit", ""), "headline": F[i]["headline"]} for i in rot_ids]
    h0 = rot[0]
    H = C["hero"]
    sub_lines = "<br>".join(E(s) for s in H["sub"].split("|"))
    hero = f"""<section class="hero" id="top" aria-labelledby="hero-h">
  <figure class="hero-pic" aria-hidden="true">{pic("hawa-mahal-sky", "(max-width: 900px) 100vw, 55vw", eager=True)}</figure>
  <div class="hero-copy">
    <div class="hero-top">
      <h1 id="hero-h" class="hero-h">{E(H['headline'])}</h1>
      <p class="hero-sub">{sub_lines}</p>
    </div>
    <div class="hero-fig" data-rot data-base="{cafe}/">
      <p class="hero-from">{E(H['from'])}</p>
      <a class="rot-link" href="{cafe}/insights/#f-{h0['id']}"><span class="hero-num">{E(h0['value'])}<small>{E(h0['unit'])}</small></span>
      <span class="hero-cap">{E(h0['headline'])}</span></a>
      <div class="rot-ctrl" data-ui hidden><span class="rot-bar" aria-hidden="true"><i></i></span>
        <button type="button" class="rot-btn">Pause</button><span class="rot-count" aria-hidden="true"></span></div>
    </div>
    <script type="application/json" id="rot-data">{json.dumps(rot, ensure_ascii=False)}</script>
    <div class="hero-foot"><p class="hero-act"><a class="btn" href="{cafe}/">{E(H['primary'])}</a><a class="btn btn-ghost" href="#updates">{E(H['secondary'])}</a></p>
    <p class="hero-meta">{f(H['meta'])} · <a class="rot-how" href="{cafe}/insights/#f-{h0['id']}">{E(H['how'])}</a></p></div>
  </div>
  <div class="hero-obj hero-still">
    <figure class="hero-side" data-drift>{pic("jantar-field", "(max-width: 900px) 100vw, 45vw", eager=True)}</figure>
    <p class="relief-note">{f(H['pic_note'])}</p>
  </div>
</section>"""

    # ---------- the problem, and the promise ----------
    I = C["intro"]
    intro = f"""<section class="intro" aria-label="Why this exists">
  <p class="lead reveal">{f(' '.join(I['lead'].split()))}</p>
  <div class="cols">{''.join(f'<p class="reveal">{f(c)}</p>' for c in I['cols'])}</div>
</section>"""

    # ---------- the industries, live and next ----------
    R = C["industries"]["rows"]
    rows = [f'<li class="reveal ix-live"><a href="{cafe}/"><span class="ix-name">{E(ind["cafes"]["short"])}</span>'
            f'<span class="ix-tag"><i class="dot"></i>{E(R["cafes"]["tag"])}</span><span class="ex-p">{f(" ".join(R["cafes"]["text"].split()))}</span>'
            f'<span class="best-go">{E(R["cafes"]["go"])}</span></a></li>']
    if jewel:
        rows.append(f'<li class="reveal ix-soon"><a href="#jewellery"><span class="ix-name">{E(jewel["short"])}</span>'
                    f'<span class="ix-tag">{E(R["jewellery"]["tag"])}</span><span class="ex-p">{f(" ".join(R["jewellery"]["text"].split()))}</span>'
                    f'<span class="best-go">{E(R["jewellery"]["go"])}</span></a></li>')
    if candidates:
        rows.append(f'<li class="reveal ix-next"><a href="#next"><span class="ix-name">{" · ".join(E(c["short"]) for c in candidates)}</span>'
                    f'<span class="ix-tag">{E(R["candidates"]["tag"])}</span><span class="ex-p"></span>'
                    f'<span class="best-go">{E(R["candidates"]["go"])}</span></a></li>')
    board = f"""<section class="explore" id="industries" aria-labelledby="industries-h">
  <header class="ch-head reveal"><h2 id="industries-h">{E(C['industries']['headline'])}</h2><p>{f(C['industries']['lede'])}</p></header>
  <ul class="best-list ex-list ix-list">{''.join(rows)}</ul>
</section>"""

    # ---------- live now: the café index ----------
    K = C["cafes"]
    inside = "".join(f'<li class="reveal"><a href="{cafe}/{h}"><span class="best-name">{E(t)}</span><span class="ex-p">{f(d)}</span>'
                     f'<span class="best-go">Open</span></a></li>' for h, t, d in K["inside"])
    cafes = f"""<section class="live" id="cafes" aria-labelledby="cafes-h">
  <div class="live-copy reveal">
    <p class="eyebrow"><i class="dot"></i>{E(K['eyebrow'])}</p>
    <h2 id="cafes-h">{E(K['headline'])}</h2>
    <p class="lead">{f(' '.join(K['lede'].split()))}</p>
    <p class="live-act"><a class="btn" href="{cafe}/">{E(K['action'])}</a></p>
    <p class="live-note">{f(K['note'])}</p>
  </div>
  <ul class="best-list live-list">{inside}</ul>
</section>"""

    # ---------- proof ----------
    P = C["proof"]
    cards = []
    for fid in cfg["findings"]["proof"]:
        x = F[fid]
        g = GRADE.get(x.get("grade"), 0)
        cards.append(f"""<article class="pr reveal">
    <p class="pr-num"><span class="n">{E(num(x['value']))}</span><small>{E(x.get('unit', ''))}</small></p>
    <p class="pr-head">{E(x['headline'])}</p>
    <p class="pr-limit"><b>{E(P['limit'])}</b> {E(x.get('limit', ''))}</p>
    <p class="pr-foot"><span class="ev" data-g="{g}"><i></i><i></i><i></i></span>{E(P['grades'].get(x.get('grade'), ''))} · <a href="{cafe}/insights/#f-{fid}">{E(P['how'])}</a></p>
  </article>""")
    proof = f"""<section class="proof" id="proof" aria-labelledby="proof-h">
  <header class="ch-head reveal"><h2 id="proof-h">{E(P['headline'])}</h2><p>{f(' '.join(P['lede'].split()))}</p></header>
  <div class="pr-grid">{''.join(cards)}</div>
  <p class="pr-all reveal"><a class="btn" href="{cafe}/insights/"><span>{f(P['all'])}</span></a></p>
</section>
<figure class="band reveal" data-drift>{pic("patrika-gate-sky", "100vw")}<figcaption>{E(C['band_caption'])}</figcaption></figure>"""

    # ---------- coming soon: jewellery ----------
    J = C["jewellery"]
    jewellery = f"""<section class="soon" id="jewellery" aria-labelledby="jewellery-h">
  <div class="soon-copy reveal">
    <p class="eyebrow">{E(J['eyebrow'])}</p>
    <h2 id="jewellery-h">{E(J['headline'])}</h2>
    <p class="lead">{f(' '.join(J['lede'].split()))}</p>
  </div>
  <div class="soon-side reveal">
    <p class="soon-asks">{E(J['asks'])}</p>
    <ol class="soon-qs">{''.join(f'<li>{f(q)}</li>' for q in J['questions'])}</ol>
    <p class="soon-act"><a class="btn" href="#updates" data-pick="jewellery">{E(J['action'])}</a></p>
    <p class="soon-note">{f(J['note'])}</p>
  </div>
</section>"""

    # ---------- what comes after ----------
    N = C["next"]
    nxt = f"""<section class="next" id="next" aria-labelledby="next-h">
  <header class="ch-head reveal"><h2 id="next-h">{E(N['headline'])}</h2><p>{f(' '.join(N['lede'].split()))}</p></header>
  <ul class="chips reveal">{''.join(f'<li>{E(c["short"])}</li>' for c in candidates)}</ul>
  <p class="reveal"><a class="btn" href="#updates" data-pick="next">{E(N['action'])}</a></p>
</section>"""

    # ---------- free updates ----------
    U = C["updates"]
    fn = lambda k, fallback: E(fields.get(k) or fallback)
    no_js = (f'action="{E(sub["action"])}" method="post" target="_blank"' if live_form      # how the form posts without master.js
             else f'action="{entities("mailto:" + au["email"])}" method="post" enctype="text/plain"')
    picks = "".join(f'<label class="pick"><input type="checkbox" name="{fn("industries", "industries")}" value="{E(v)}" data-key="{k}"{" checked" if k == "cafes" else ""}><span>{E(v)}</span></label>'
                    for k, v in U["picks"].items())
    updates = f"""<section class="updates" id="updates" aria-labelledby="updates-h">
  <div class="up-copy reveal">
    <h2 id="updates-h">{E(U['headline'])}</h2>
    <p>{f(' '.join(U['lede'].split()))}</p>
  </div>
  <form class="sign reveal" {no_js} data-provider="{'google_form' if live_form else 'email'}" data-action="{E(sub.get('action', '') if live_form else '')}"
    data-to="{entities(au['email'])}" data-subject="{E(brand)}: updates" data-thanks="{E(U['thanks'])}" data-thanks-email="{E(U['thanks_email'])}" novalidate>
    <label class="field"><span>{E(U['name'])}</span><input type="text" name="{fn('name', 'name')}" autocomplete="name" required maxlength="80"></label>
    <label class="field"><span>{E(U['contact'])}</span><input type="tel" name="{fn('contact', 'contact')}" autocomplete="tel" inputmode="tel" required maxlength="16" placeholder="{E(U['contact_hint'])}"></label>
    <fieldset class="picks"><legend>{E(U['pick'])}</legend>{picks}</fieldset>
    <label class="field field-q"><span>{E(U['question'])}</span><textarea name="{fn('question', 'question')}" rows="3" maxlength="1000" placeholder="{E(U['question_hint'])}"></textarea></label>
    <button class="btn" type="submit">{E(U['send'])}</button>
    <p class="up-note">{f(' '.join(U['note'].split()))}</p>
    <p class="up-status" role="status" aria-live="polite"></p>
  </form>
</section>"""

    # ---------- who's behind it ----------
    A = C["about"]
    about = f"""<section class="who" id="about" aria-labelledby="about-h">
  <div class="who-side">
    <picture class="who-photo reveal"><source type="image/webp" srcset="img/sarthak-street-400.webp 400w, img/sarthak-street-800.webp 800w" sizes="(max-width: 900px) 240px, 380px">
    <img src="img/sarthak-street-800.jpg" srcset="img/sarthak-street-400.jpg 400w, img/sarthak-street-800.jpg 800w" sizes="(max-width: 900px) 240px, 380px" width="800" height="1542" alt="{E(au['name'])}" loading="lazy" decoding="async"></picture>
  </div>
  <div class="who-text reveal">
    <h2 id="about-h">{E(A['headline'])}</h2>
    {''.join(f'<p>{f(" ".join(x.split()))}</p>' for x in A['paras'])}
  </div>
</section>"""

    # ---------- ask a question ----------
    Q = C["contact"]
    mail_e = entities(mail)
    contact = f"""<section class="contact" id="contact" aria-labelledby="contact-h">
  <div class="c-intro reveal"><h2 id="contact-h">{E(Q['headline'])}</h2>{''.join(f'<p>{f(" ".join(x.split()))}</p>' for x in Q['paras'])}</div>
  <div class="c-card reveal" data-ui>
    <p class="c-k">{E(Q['email'])}</p>
    <p class="c-email"><a href="{mail_e}">{entities(au['email'])}</a></p>
    <p class="c-acts"><a class="btn" href="{mail_e}">{E(Q['write'])}</a><button type="button" class="c-copy-btn" data-copy="{entities(au['email'])}">{E(Q['copy'])}</button></p>
    <p class="c-k">{E(Q['linkedin'])}</p>
    <p class="c-acts"><a class="btn btn-ln" href="{au['linkedin']}" rel="noopener" target="_blank">{E(au['name'])} on LinkedIn</a></p>
    <p class="c-copied" role="status" aria-live="polite"></p>
  </div>
</section>"""

    # ---------- footer ----------
    Fo = C["footer"]
    credits = "; ".join(f'<a href="{u}" rel="noopener" target="_blank">{E(who)}</a>' for _, who, u, *_ in PHOTOS.values())
    explore = "".join(f'<a href="{i["url"]}/">{E(i["name"])}</a>' for i in sites)
    footer = f"""<footer class="foot">
  <a class="foot-name" href="./">{E(brand)}</a>
  <div class="ft-cols"><div><p class="ft-h">{E(Fo['explore'])}</p>{explore}<a href="#jewellery">{E(jewel.get('name', ''))} (coming soon)</a></div>
  <div><p class="ft-h">{E(Fo['learn'])}</p><a href="#about">About</a><a href="#proof">Findings</a><a href="https://github.com/sarthakkk23/jaipur-index" rel="noopener">Source code</a></div>
  <div><p class="ft-h">{E(Fo['stay'])}</p><a href="#updates">Free updates</a><a href="{mail_e}">Email</a><a href="{au['linkedin']}" rel="noopener">LinkedIn</a></div></div>
  <p>Photographs on Unsplash by {credits}. {f(' '.join(Fo['note'].split()))}</p>
  <p>Café figures from the Jaipur Café Index, updated {E(T['cafes.updated'])} · built {E(nice(today))}</p>
</footer>"""

    page = f"""{head}
<body>
{bar}
<main>
{hero}
{intro}
{board}
{cafes}
{proof}
{jewellery}
{nxt}
{updates}
{about}
{contact}
</main>
{footer}
</body>
</html>
"""
    if missing:
        raise BuildError("copy uses tokens the data doesn't have: " + ", ".join(sorted(set(missing))))

    # ---------- write dist/ ----------
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for item in WEB.iterdir():
        if item.name.startswith("."):
            continue
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, DIST / item.name)
    (DIST / "index.html").write_text(page, encoding="utf-8")
    (DIST / "404.html").write_text(not_found(head, bar, footer, brand, cafe), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{base}/</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>\n</urlset>\n",
        encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    if dom:
        (DIST / "CNAME").write_text(dom + "\n", encoding="utf-8")
    # what the page was built from, so check.py (and anyone) can trace every number
    (DIST / "data").mkdir(exist_ok=True)
    (DIST / "data" / "sources.json").write_text(json.dumps(
        {k: {"source": d["_source"], "snapshot": d["meta"].get("snapshot"), "captured_on": d["meta"].get("captured_on")} for k, d in data.items()},
        indent=2), encoding="utf-8")
    return data, today


def not_found(head, bar, footer, brand, cafe):
    h = head.replace('<meta name="robots" content="index, follow, max-image-preview:large">', '<meta name="robots" content="noindex">')
    h = re.sub(r"<title>.*?</title>", f"<title>Page not found · {E(brand)}</title>", h)
    h = re.sub(r'<script type="application/ld\+json">.*?</script>\n', "", h, flags=re.S)
    return f"""{h}
<body>
{bar}
<main>
<section class="page-head"><h1>That page isn't here.</h1><p class="page-lede">It may have moved when the sites changed address.
Start from the <a href="./">front page</a>, or go straight to the <a href="{cafe}/">Jaipur Café Index</a>.</p></section>
</main>
{footer}
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="append", default=[], help="industry=path to read that industry's data from a file instead of its site")
    a = ap.parse_args()
    overrides = dict(x.split("=", 1) for x in a.data)
    try:
        data, _ = build(overrides)
    except BuildError as e:
        print(f"build failed: {e}", file=sys.stderr)
        sys.exit(1)
    for k, d in data.items():
        print(f"{k}: snapshot {d['meta'].get('snapshot')} from {d['_source']}")
    print(f"built {DIST}")


if __name__ == "__main__":
    main()
