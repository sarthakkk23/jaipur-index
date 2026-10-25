"""Build the main site: config + copy + each live industry's published data + web/ -> dist/ (static, no framework).

Six pages, one board: every page is a 12-column grid of flat tiles fitted edge to edge, the way Jaipur's walled city
is a grid of blocks with a bazaar for each trade. Same fonts and colours as the café index; none of its layouts.

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

# Photographs, all from Unsplash (Unsplash licence). name: (alt, caption, photographer, page, width, height).
# Captions say only what the photographer's own description says; none shows a business measured on these sites.
PHOTOS = {
    "city-above": ("Jaipur's rooftops spreading to the hills, seen from a fort wall with a flag", "Jaipur from above",
                   "Maninder Sidhu", "https://unsplash.com/photos/25zQN22kKrU", 1600, 2097),
    "badi-chaupar": ("A street of shops selling handicrafts near Badi Chaupar, seen from a rooftop", "Near Badi Chaupar",
                     "Harshit Katiyar", "https://unsplash.com/photos/G5ElSIXPNSE", 1600, 1067),
    "lattice": ("A Jaipur street seen through the openings of a carved stone lattice", "Through a stone lattice",
                "Subhashis Das", "https://unsplash.com/photos/SYUrysYdXSo", 1600, 2400),
    "workshop": ("A man resting in an open-fronted workshop on a Jaipur street", "A workshop, Jaipur",
                 "Laura Lezman", "https://unsplash.com/photos/6WTcS_rECpA", 1600, 1067),
    "gem-cutter": ("A craftsman bent over a polishing wheel in a small Jaipur workshop", "At the wheel, Jaipur",
                   "Johan Mouchet", "https://unsplash.com/photos/cFSYBkneAp0", 1600, 2400),
    "textile-stall": ("Printed dresses hanging over a busy street stall at night", "Textiles near Hawa Mahal",
                      "Harshit Katiyar", "https://unsplash.com/photos/BnD28_26kQo", 1600, 2400),
    "kathputli": ("Kathputli string puppets in bright costumes hanging for sale", "Kathputli puppets",
                  "Karan Bipate", "https://unsplash.com/photos/xzkeqp94tm8", 1600, 2400),
    "print-blocks": ("A heap of carved wooden blocks for hand block printing", "Carved printing blocks",
                     "Kushali Bhagat", "https://unsplash.com/photos/y-ZRmGmSyLw", 1600, 1069),
    "emerald": ("A cut emerald on a white table beside tweezers and a jeweller's loupe", "An emerald, loupe and tweezers",
                "Sabrianna", "https://unsplash.com/photos/jYVvmAi4u8c", 1600, 1067),
    "coffee": ("A glass of coffee on a blue saucer on a wooden café table", "Coffee",
               "Parakram Singh", "https://unsplash.com/photos/VIv4QzCd2Xc", 1600, 2133),
    "pink-bazaar": ("Pink and red shopfronts with domed pavilions above a busy bazaar street in Jaipur, lit at dusk", "A bazaar street in the Pink City",
                    "Mohit Mohit", "https://unsplash.com/photos/QkTLv7K_Pe0", 1600, 1607),
    "old-city-bw": ("Jaipur's houses packed rooftop to rooftop, in black and white", "Jaipur, rooftop to rooftop",
                    "Jayanth Muppaneni", "https://unsplash.com/photos/WLmRiVr2E5A", 1600, 1354),
}
WIDTHS = {"city-above": (900, 1600, 2400), "pink-bazaar": (900, 1600, 2400)}
GRADE = {"Strong": 3, "Moderate": 2, "Weak": 1}
PAGES = ["", "cafes/", "jewellery/", "next/", "about/", "updates/"]
CURRENT = ' aria-current="page"'


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


def findings(d):
    I = d["insights"]
    return {f["id"]: f for f in (I.get("findings") or []) + ((I.get("survey") or {}).get("findings") or [])}


def tokens(cfg, data):
    T = {"brand": cfg["brand"]["name"]}
    for key, d in data.items():
        for k, v in (d.get("tokens") or {}).items():
            T[f"{key}.{k}"] = str(v)
        if key == "cafes":
            T["cafes.findings"] = str(len(findings(d)))
            T["cafes.updated"] = nice(d["meta"]["captured_on"])
    return T


def num(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return f"{v:,}" if isinstance(v, int) else str(v)


def entities(s):
    """Email addresses as character references: readable to people, a little harder for scrapers."""
    return "".join(f"&#{ord(c)};" for c in s)


def asset(name):
    """name?v=<content hash>: a new deploy changes the address, so no browser keeps an old copy."""
    return f"{name}?v={hashlib.sha1((WEB / name).read_bytes()).hexdigest()[:10]}"


class Site:
    """Everything one build needs: config, copy, data, and the helpers that turn them into tiles."""

    def __init__(self, overrides):
        self.cfg = yaml.safe_load((ROOT / "site.config.yaml").read_text(encoding="utf-8"))
        self.C = yaml.safe_load((ROOT / "content" / "copy.yaml").read_text(encoding="utf-8"))
        self.dom, self.base = addresses(self.cfg)
        self.data = load_data(self.cfg, overrides)
        if "cafes" not in self.data:
            raise BuildError("the café index is the proof on this site; its data is required")
        self.T = tokens(self.cfg, self.data)
        self.H = yaml.safe_load((ROOT / "content" / "history.yaml").read_text(encoding="utf-8"))
        for k, fact in self.H["facts"].items():
            self.T[f"history.{k}"] = str(fact["value"])
        self.F = findings(self.data["cafes"])
        self.missing, self.used = [], []
        self.brand, self.au = self.cfg["brand"]["name"], self.cfg["author"]
        self.ind = {i["key"]: i for i in self.cfg["industries"]}
        self.cafe = self.ind["cafes"]["url"]
        self.candidates = [i for i in self.cfg["industries"] if i["status"] == "candidate"]
        self.today = datetime.now(timezone.utc).date().isoformat()
        self.mail = f"mailto:{self.au['email']}?subject={quote(self.au.get('email_subject', self.brand))}"
        for group, ids in self.cfg["findings"].items():
            for fid in ids:
                if fid not in self.F:
                    raise BuildError(f"findings.{group}: '{fid}' is not in the café index's published findings")
                if not isinstance(self.F[fid].get("value"), (int, float)):
                    raise BuildError(f"finding '{fid}' has no published value")

    # ----- words -----
    def f(self, text):
        """Escape copy, set a leading **run-in** in bold, swap {{token}} for its value. Unknown tokens are recorded."""
        out = []
        for part in re.split(r"({{\s*[\w.]+\s*}})", " ".join(str(text).split())):
            m = re.fullmatch(r"{{\s*([\w.]+)\s*}}", part)
            if not m:
                out.append(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", E(part)))
            elif self.T.get(m.group(1)) in (None, "", "—"):
                self.missing.append(m.group(1))
                out.append("—")
            else:
                out.append(f'<span class="n">{E(self.T[m.group(1)])}</span>')
        return "".join(out)

    def p(self, text):
        """For attributes and metadata: same tokens, no markup."""
        def sub(m):
            if m.group(1) not in self.T:
                self.missing.append(m.group(1))
                return "—"
            return self.T[m.group(1)]
        return re.sub(r"{{\s*([\w.]+)\s*}}", sub, " ".join(str(text).split())).replace("**", "")

    # ----- pictures -----
    def pic(self, name, sizes, pre, eager=False):
        alt, _, _, _, w, h = PHOTOS[name]
        self.used.append(name)
        ws = WIDTHS.get(name, (900, 1600))
        srcset = lambda ext: ", ".join(f"{pre}img/{name}-{s}.{ext} {s}w" for s in ws)
        load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
        return (f'<picture><source type="image/webp" srcset="{srcset("webp")}" sizes="{sizes}">'
                f'<img src="{pre}img/{name}-1600.jpg" srcset="{srcset("jpg")}" sizes="{sizes}" width="{w}" height="{h}" alt="{E(alt)}" {load}></picture>')

    def photo_tile(self, name, cls, pre, sizes="(max-width: 760px) 100vw, 40vw", caption=True, eager=False):
        cap = f'<figcaption>{E(PHOTOS[name][1])}</figcaption>' if caption else ""
        return f'<figure class="t t-photo rv {cls}">{self.pic(name, sizes, pre, eager)}{cap}</figure>'

    def finding_tile(self, fid, cls, with_limit=True):
        x, P = self.F[fid], self.C["cafes"]
        g = GRADE.get(x.get("grade"), 0)
        limit = f'<p class="fd-limit"><b>{E(P["limit"])}</b> {E(x.get("limit", ""))}</p>' if with_limit else ""
        return (f'<article class="t t-fig rv {cls}"><p class="fig"><span class="n">{E(num(x["value"]))}</span><small>{E(x.get("unit", ""))}</small></p>'
                f'<div class="fig-foot"><p class="fig-cap">{E(x["headline"])}</p>{limit}'
                f'<p class="fd-grade"><span class="ev" data-g="{g}"><i></i><i></i><i></i></span>{E(P["grades"].get(x.get("grade"), ""))} · '
                f'<a href="{self.cafe}/insights/#f-{fid}">{E(P["how"])}</a></p></div></article>')

    # ----- the frame every page sits in -----
    def head(self, path, title, desc, ld, base_tag=False):
        pre = "../" if path else ""
        url = f"{self.base}/{path}"
        base = f'<base href="{self.base}/">\n' if base_tag else ""
        ld_tag = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n' if ld else ""
        robots = "noindex" if base_tag else "index, follow, max-image-preview:large"
        return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
{base}<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="{robots}">
<meta name="author" content="{E(self.au['name'])}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{E(self.brand)}">
<meta property="og:locale" content="en_IN">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{self.base}/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{E(self.brand)}: Jaipur's industries, measured. Jaipur's rooftops from above.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{self.base}/og.jpg">
<link rel="icon" href="{pre}favicon.svg" type="image/svg+xml">
<link rel="icon" href="{pre}favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="{pre}apple-touch-icon.png">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#f5f5f2">
{ld_tag}<script>document.documentElement.classList.add("js");setTimeout(function(){{if(!window.__board)document.documentElement.classList.remove("js")}},3000)</script>
<link rel="preload" href="{pre}fonts/literata.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{pre}{asset('site.css')}">
<script src="{pre}{asset('site.js')}" defer></script>
</head>"""

    def bar(self, path):
        pre = "../" if path else ""
        home = pre or "./"
        links = "".join(f'<a href="{pre}{h}"{CURRENT if h == path else ""}>{E(t)}</a>' for h, t in self.C["nav"])
        ah, at = self.C["nav_action"]
        mark = ('<svg class="mark" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" fill="#e3ad9f"/>'
                '<rect x="14" y="30" width="9" height="20" fill="#161616"/><rect x="27.5" y="20" width="9" height="30" fill="#161616"/>'
                '<rect x="41" y="13" width="9" height="37" fill="#b0533d"/></svg>')
        return (f'<header class="bar"><a class="wordmark" href="{home}">{mark}<span>{E(self.brand)}</span></a>'
                f'<nav class="bar-links" aria-label="Main">{links}</nav>'
                f'<details class="menu"><summary>Menu</summary><nav class="menu-panel" aria-label="Main"><a href="{home}">Home</a>{links}'
                f'<a href="{pre}{ah}">{E(at)}</a></nav></details>'
                f'<a class="btn bar-btn" href="{pre}{ah}"{CURRENT if ah == path else ""}>{E(at)}</a></header>')

    def footer(self, path):
        pre = "../" if path else ""
        Fo = self.C["footer"]
        heights = [100, 74, 90, 62, 84, 70, 96, 66, 88, 78, 60, 92]
        tones = ["pink", "blush", "red", "stone", "clay"]
        blocks, k = [], 0
        for c in self.brand:
            if c == " ":
                blocks.append('<span class="blk blk-gap"></span>')
                continue
            blocks.append(f'<span class="blk tone-{tones[k % len(tones)]}" style="--h:{heights[k % len(heights)]}%"><i>{E(c)}</i></span>')
            k += 1
        live = [i for i in self.cfg["industries"] if i["status"] == "live"]
        jewel = self.ind.get("jewellery")
        inds = "".join(f'<a href="{i["url"]}/">{E(i["name"])}</a>' for i in live)
        if jewel:
            inds += f'<a href="{pre}jewellery/">{E(jewel["name"])} {E(Fo["soon"])}</a>'
        inds += f'<a href="{pre}next/">{E(dict(self.C["nav"])["next/"])}</a>'
        mail = entities(self.mail)
        credits = []
        for n in dict.fromkeys(self.used):
            credits.append(f'<a href="{PHOTOS[n][3]}" rel="noopener" target="_blank">{E(PHOTOS[n][1])}</a> by {E(PHOTOS[n][2])}')
        credit_line = f'<p class="ft-small">{E(Fo["photos"])} {"; ".join(credits)}.</p>' if credits else ""
        return f"""<footer class="foot">
  <a class="blocks" href="{pre or './'}" aria-label="{E(self.brand)}: home">{''.join(blocks)}</a>
  <div class="ft-cols">
    <div><p class="ft-h">{E(Fo['industries'])}</p>{inds}</div>
    <div><p class="ft-h">{E(Fo['project'])}</p><a href="{pre}about/">About</a><a href="{pre}about/#method">How it's made</a><a href="https://github.com/sarthakkk23/jaipur-index" rel="noopener">Source code</a></div>
    <div><p class="ft-h">{E(Fo['stay'])}</p><a href="{pre}updates/">Free updates</a><a href="{mail}">Email</a><a href="{self.au['linkedin']}" rel="noopener">LinkedIn</a></div>
    <div class="ft-note"><p>{self.f(Fo['note'])}</p></div>
  </div>
  {credit_line}
  <p class="ft-small">Café figures from the Jaipur Café Index, updated {E(self.T['cafes.updated'])} · built {E(nice(self.today))}</p>
</footer>"""

    def page(self, path, title, desc, body, ld_extra=None, main_cls="", not_found=False):
        crumbs = [{"@type": "ListItem", "position": 1, "name": self.brand, "item": f"{self.base}/"}]
        if path:
            crumbs.append({"@type": "ListItem", "position": 2, "name": title.split(" · ")[0], "item": f"{self.base}/{path}"})
        graph = [
            {"@type": "WebSite", "@id": f"{self.base}/#site", "name": self.brand, "url": f"{self.base}/", "inLanguage": "en-IN",
             "publisher": {"@id": f"{self.base}/#author"}},
            {"@type": "Person", "@id": f"{self.base}/#author", "name": self.au["name"], "url": f"{self.base}/about/",
             "sameAs": [self.au["linkedin"]], "jobTitle": "Data analyst", "image": f"{self.base}/img/sarthak-street-800.jpg",
             "homeLocation": {"@type": "City", "name": "Jaipur"}, "knowsAbout": ["Market research", "Data analysis", "Jaipur"]},
            {"@type": "WebPage", "@id": f"{self.base}/{path}#page", "url": f"{self.base}/{path}", "name": title, "description": desc,
             "isPartOf": {"@id": f"{self.base}/#site"}, "about": {"@type": "City", "name": "Jaipur"},
             "primaryImageOfPage": f"{self.base}/og.jpg", "dateModified": self.today, "inLanguage": "en-IN"},
            {"@type": "BreadcrumbList", "itemListElement": crumbs},
        ] + (ld_extra or [])
        ld = None if not_found else {"@context": "https://schema.org", "@graph": graph}
        return f"""{self.head(path, title, desc, ld, base_tag=not_found)}
<body>
<a class="skip" href="#main">Skip to the content</a>
{self.bar(path)}
<main id="main" class="{main_cls}">
{body}
</main>
{self.footer(path)}
</body>
</html>
"""

    def close_row(self, pre, headline, text, href, action, photo, pick=""):
        """The close: one row of the board, an accent tile flanked by a photograph and a colour, cropped at both edges."""
        data = f' data-pick="{pick}"' if pick else ""
        return f"""<section class="board row-close" aria-labelledby="close-h">
  {self.photo_tile(photo, "c-side c-left", pre, "20vw", caption=False)}
  <div class="t t-accent c-main rv"><h2 id="close-h">{E(headline)}</h2><p>{self.f(text)}</p><p><a class="btn btn-paper" href="{href}"{data}>{E(action)}</a></p></div>
  <div class="t tone-blush c-side c-right rv" aria-hidden="true"></div>
</section>"""

    # ================================================================ pages
    def home(self):
        pre, H = "", self.C["home"]
        src = self.H["source"]

        # ----- the first screen: an honest way out, then the city's story -----
        Y = H["hurry"]
        hrefs = {"cafe": f"{self.cafe}/"}
        links = "".join(f'<a href="{hrefs.get(h, h)}">{E(t)}</a>' for h, t in Y["links"])
        hurry = f"""<div class="hurry"><p class="hurry-text">{self.f(Y['text'])}</p><nav class="hurry-links" aria-label="Skip to">{links}</nav>
    <p class="hurry-after">{self.f(Y['after'])}</p></div>"""
        V = H["hero"]
        hero = f"""<section class="board story-head" aria-labelledby="hero-h">
  <div class="t tone-clay s7 story rv"><h1 id="hero-h">{E(V['headline'])}</h1>
    {hurry}
    <p class="statement">{self.f(V['text'])}</p>
    <p class="small src"><a href="{src['url']}" rel="noopener">{E(src['name'])}</a></p></div>
  {self.photo_tile("pink-bazaar", "s5 story-pic", pre, "(max-width: 900px) 100vw, 42vw", eager=True)}
</section>"""

        # ----- a short history: four dated tiles, read left to right -----
        S = H["history"]
        shapes = ["s5 tone-blush", "s7 tone-stone", "s7 tone-pink", "s5 tone-ink"]
        items = "".join(f"""<article class="t when rv {shapes[n % 4]}"><p class="when-mark">{self.f(mark)}</p>
    <div class="when-text"><h3>{E(title)}</h3><p>{self.f(text)}</p></div></article>"""
                        for n, (mark, title, text) in enumerate(S["items"]))
        history = f"""<section class="board history" aria-labelledby="hist-h">
  <div class="t t-plain s12 sec-head rv"><h2 id="hist-h">{E(S['headline'])}</h2><p class="small"><a href="{src['url']}" rel="noopener">{E(S['source'])}</a></p></div>
  {items}
</section>"""

        # ----- the bridge: from the city's trades to this project -----
        I = H["bridge"]
        bridge = f"""<section class="board intro" aria-labelledby="bridge-h">
  <div class="t t-plain s12 rv"><h2 id="bridge-h">{E(I['headline'])}</h2><p class="lead">{self.f(I['lead'])}</p>
  <div class="cols">{''.join(f'<p>{self.f(c)}</p>' for c in I['cols'])}</div></div>
</section>"""

        # ----- find your trade: the one live thing; one photograph, the one that belongs to the answer -----
        K = H["picker"]
        jewel = self.ind["jewellery"]
        trades = [("cafes", self.ind["cafes"]["short"], f"{self.cafe}/", K["live"], "tone-pink"),
                  ("jewellery", jewel["short"], "jewellery/", K["soon"], "tone-blush")]
        trades += [(c["key"], c["short"], "next/", "", "tone-stone") for c in self.candidates]
        trades.append(("other", K["other"], "updates/", "", "tone-stone2"))
        buttons = "".join(
            f'<a class="trade rv {tone}" href="{href}" data-trade="{key}" aria-controls="answer"><span class="trade-name">{E(name)}</span>'
            + (f'<span class="trade-tag">{E(tag)}</span>' if tag else "") + "</a>" for key, name, href, tag, tone in trades)
        ex = "".join(f'<li><b><span class="n">{E(num(self.F[i]["value"]))}</span>{E(self.F[i].get("unit", ""))}</b> {E(self.F[i]["headline"])}</li>'
                     for i in self.cfg["findings"]["picker"])
        photos = {"cafes": "coffee", "jewellery": "gem-cutter", "textiles": "print-blocks", "handicrafts": "kathputli"}

        def ans(key, head, body, href, go, hidden=True):
            ph = photos.get(key)
            pic = (f'<figure class="ans-pic">{self.pic(ph, "(max-width: 900px) 100vw, 40vw", pre)}<figcaption>{E(PHOTOS[ph][1])}</figcaption></figure>'
                   if ph else "")
            return (f'<div class="ans{" ans-has-pic" if ph else ""}" data-for="{key}"{" hidden" if hidden else ""}><div class="ans-text"><h3>{E(head)}</h3>{body}'
                    f'<p><a class="btn btn-paper" href="{href}">{E(go)}</a></p></div>{pic}</div>')

        answers = [ans("cafes", K["cafes_head"], f'<p>{self.f(K["cafes_text"])}</p><ul class="ans-figs">{ex}</ul>', f"{self.cafe}/", K["cafes_go"], hidden=False),
                   ans("jewellery", K["jewellery_head"], f'<p>{self.f(K["jewellery_text"])}</p>', "updates/?pick=jewellery", K["jewellery_go"])]
        for c in self.candidates:
            answers.append(ans(c["key"], f"{c['short']}: {K['candidate_head'].lower()}", f'<p>{self.f(K["candidate_text"])}</p>',
                               f"updates/?pick=next&amp;trade={quote(c['short'])}", K["candidate_go"]))
        answers.append(ans("other", K["other_head"], f'<p>{self.f(K["other_text"])}</p>', "updates/?pick=next", K["other_go"]))
        picker = f"""<section class="board picker" id="trades" aria-labelledby="trades-h">
  <div class="t t-plain s4 pk-head rv"><h2 id="trades-h">{E(K['headline'])}</h2><p>{self.f(K['lede'])}</p></div>
  <div class="trades s8">{buttons}</div>
  <div class="t tone-ink answer s12" id="answer" aria-live="polite">{''.join(answers)}</div>
</section>"""

        # ----- the close: who's behind it, and the one action -----
        C = H["close"]
        portrait = ('<figure class="t t-photo s3 who-pic rv"><picture><source type="image/webp" srcset="img/sarthak-street-400.webp 400w, img/sarthak-street-800.webp 800w" sizes="(max-width: 900px) 50vw, 25vw">'
                    f'<img src="img/sarthak-street-800.jpg" srcset="img/sarthak-street-400.jpg 400w, img/sarthak-street-800.jpg 800w" sizes="(max-width: 900px) 50vw, 25vw" width="800" height="1542" alt="{E(self.au["name"])}" loading="lazy" decoding="async"></picture></figure>')
        close = f"""<section class="board close-who" aria-labelledby="close-h">
  {portrait}
  <div class="t tone-blush s4 who-text rv"><p class="statement">{self.f(C['who'])}</p>{''.join(f'<p>{self.f(x)}</p>' for x in C['who_more'])}
    <p class="who-links"><a class="link" href="about/">{E(C['more'])}</a><a class="link" href="{self.au['linkedin']}" rel="noopener">{E(C['linkedin'])}</a></p></div>
  <div class="t t-accent s5 who-act rv"><h2 id="close-h">{E(C['headline'])}</h2><p>{self.f(C['text'])}</p><p><a class="btn btn-paper" href="updates/">{E(C['action'])}</a></p></div>
</section>"""

        live = [i for i in self.cfg["industries"] if i["status"] == "live"]
        ld = [{"@type": "ItemList", "name": f"{self.brand}: industry sites", "itemListElement": [
            {"@type": "ListItem", "position": n + 1, "item": {"@type": "WebSite", "name": i["name"], "url": f"{i['url']}/"}}
            for n, i in enumerate(live)]}]
        return self.page("", self.p(H["title"]), self.p(H["description"]), "\n".join([hero, history, bridge, picker, close]), ld, "home")

    def cafes(self):
        pre, P = "../", self.C["cafes"]
        cafe = self.cafe
        head = f"""<section class="board p-head" aria-labelledby="h">
  <div class="t tone-pink s8 name rv"><h1 id="h">{E(P['headline'])}</h1></div>
  {self.photo_tile("coffee", "s4 r2", pre, "(max-width: 760px) 100vw, 33vw", eager=True)}
  <div class="t t-plain s5 rv"><p class="statement">{self.f(P['statement'])}</p><p class="small">{self.f(P['updated'])}</p></div>
  <div class="t t-accent s3 act rv"><a class="btn btn-paper" href="{cafe}/">{E(P['action'])}</a></div>
</section>"""
        bars = "".join(f"""<details class="bar-row"{" open" if n == 0 else ""}><summary>{E(t)}</summary>
      <div class="bar-body"><p>{self.f(d)}</p><p><a class="link" href="{cafe}/{h}">{E(P['open'])} {E(t)}</a></p></div></details>"""
                       for n, (h, t, d) in enumerate(P["inside"]))
        inside = f"""<section class="board inside" aria-labelledby="inside-h">
  <div class="t t-plain s7 words rv"><h2 id="inside-h" class="giant">{E(P['inside_word'])}</h2>{bars}</div>
  {self.photo_tile("badi-chaupar", "s5 sticky", pre)}
</section>"""
        spans = ["s6 tone-blush", "s3 tone-stone", "s3 tone-pink", "s3 tone-stone", "s3 tone-blush", "s6 tone-clay"]
        figs = "".join(self.finding_tile(fid, spans[n % 6]) for n, fid in enumerate(self.cfg["findings"]["proof"]))
        proof = f"""<section class="board proof" aria-labelledby="proof-h">
  <div class="t t-plain s12 sec-head rv"><h2 id="proof-h">{E(P['findings_headline'])}</h2><p>{self.f(P['findings_lede'])}</p></div>
  {figs}
  <div class="t t-plain s12 rv"><a class="btn" href="{cafe}/insights/"><span>{self.f(P['all'])}</span></a></div>
</section>"""
        close = self.close_row(pre, P["close_headline"], P["close_text"], "../updates/?pick=cafes", P["close_action"], "workshop")
        return self.page("cafes/", self.p(P["title"]), self.p(P["description"]), "\n".join([head, inside, proof, close]),
                         [{"@type": "WebSite", "name": self.ind["cafes"]["name"], "url": f"{cafe}/"}])

    def jewellery(self):
        pre, J = "../", self.C["jewellery"]
        head = f"""<section class="board p-head" aria-labelledby="h">
  <div class="t tone-clay s7 name rv"><h1 id="h">{E(J['headline'])}</h1></div>
  {self.photo_tile("gem-cutter", "s5 r2", pre, "(max-width: 760px) 100vw, 42vw", eager=True)}
  <div class="t t-plain s4 rv"><p class="statement">{self.f(J['statement'])}</p></div>
  <div class="t t-accent s3 act rv"><a class="btn btn-paper" href="../updates/?pick=jewellery" data-pick="jewellery">{E(J['action'])}</a><p class="small">{self.f(J['note'])}</p></div>
</section>"""
        tones = ["s7 tone-blush", "s5 tone-stone", "s5 tone-ink", "s7 tone-pink"]
        qs = "".join(f'<div class="t q rv {tones[n % 4]}"><p class="q-text">{self.f(q)}</p><p class="small">{self.f(who)}</p></div>'
                     for n, (q, who) in enumerate(J["questions"]))
        questions = f"""<section class="board questions" aria-labelledby="q-h">
  <div class="t t-plain s12 sec-head rv"><h2 id="q-h">{E(J['questions_headline'])}</h2></div>
  {qs}
</section>"""
        pair = f"""<section class="board pair" aria-label="The trade">
  {self.photo_tile("emerald", "s8", pre, "(max-width: 760px) 100vw, 66vw")}
  {self.photo_tile("badi-chaupar", "s4", pre, "(max-width: 760px) 100vw, 33vw")}
</section>"""
        close = self.close_row(pre, J["close_headline"], J["close_text"], "../updates/?pick=jewellery", J["action"], "textile-stall", pick="jewellery")
        return self.page("jewellery/", self.p(J["title"]), self.p(J["description"]), "\n".join([head, questions, pair, close]))

    def nxt(self):
        pre, N = "../", self.C["next"]
        head = f"""<section class="board p-head" aria-labelledby="h">
  <div class="t tone-blush s8 name rv"><h1 id="h">{E(N['headline'])}</h1></div>
  <div class="t t-plain s4 rv"><p class="statement">{self.f(N['statement'])}</p></div>
</section>"""
        tests = f"""<section class="board tests" aria-labelledby="tests-h">
  <div class="t t-plain s4 rv"><h2 id="tests-h">{E(N['tests_headline'])}</h2></div>
  <div class="t tone-ink s4 rv"><p class="statement">{self.f(N['tests'][0])}</p></div>
  <div class="t tone-pink s4 rv"><p class="statement">{self.f(N['tests'][1])}</p></div>
</section>"""
        photos = {"textiles": "print-blocks", "handicrafts": "kathputli", "hotels": "lattice"}
        shapes = {"textiles": "s6 wide", "handicrafts": "s3 tall", "hotels": "s3 tall"}
        cands = []
        for c in self.candidates:
            ph = photos.get(c["key"])
            pic = (f'<figure class="cand-pic">{self.pic(ph, "(max-width: 760px) 100vw, 40vw", pre)}<figcaption>{E(PHOTOS[ph][1])}</figcaption></figure>'
                   if ph else "")
            cands.append(f"""<article class="t tone-stone cand rv {shapes.get(c['key'], 's4')}">{pic}<div class="cand-text">
      <h3>{E(c['short'])}</h3><p>{self.f(N['candidates'].get(c['key'], ''))}</p>
      <p><a class="btn" href="../updates/?pick=next&amp;trade={quote(c['short'])}">{E(N['vote'])}</a></p></div></article>""")
        cands.append(f"""<article class="t tone-red cand cand-other rv s12"><h3>{E(N['other_headline'])}</h3><p>{self.f(N['other_text'])}</p>
      <p><a class="btn btn-paper" href="../updates/?pick=next">{E(N['other_go'])}</a></p></article>""")
        list_ = f'<section class="board cands" aria-label="Candidates">{"".join(cands)}</section>'
        return self.page("next/", self.p(N["title"]), self.p(N["description"]), "\n".join([head, tests, list_]))

    def about(self):
        pre, A = "../", self.C["about"]
        portrait = (f'<figure class="t t-photo s4 r2 portrait rv"><picture><source type="image/webp" srcset="../img/sarthak-street-400.webp 400w, ../img/sarthak-street-800.webp 800w" sizes="(max-width: 760px) 100vw, 33vw">'
                    f'<img src="../img/sarthak-street-800.jpg" srcset="../img/sarthak-street-400.jpg 400w, ../img/sarthak-street-800.jpg 800w" sizes="(max-width: 760px) 100vw, 33vw" width="800" height="1542" alt="{E(self.au["name"])}" loading="lazy" decoding="async"></picture></figure>')
        head = f"""<section class="board p-head" aria-labelledby="h">
  <div class="t tone-pink s8 name rv"><h1 id="h">{E(A['headline'])}</h1></div>
  {portrait}
  <div class="t t-plain s8 bio rv"><p class="statement">{self.f(A['paras'][0])}</p>{''.join(f'<p>{self.f(x)}</p>' for x in A['paras'][1:])}</div>
</section>"""
        method = f"""<section class="board method" id="method" aria-labelledby="m-h">
  <div class="t tone-stone s12 rv"><h2 id="m-h">{E(A['method_headline'])}</h2>
  <div class="cols">{''.join(f'<p>{self.f(x)}</p>' for x in A['method'])}</div></div>
</section>"""
        rows = "".join(f'<li><a href="{u}" rel="noopener" target="_blank"><span>{E(cap)}</span><span class="soft">{E(who)}</span></a></li>'
                       for alt, cap, who, u, *_ in PHOTOS.values())
        credits = f"""<section class="board credits" aria-labelledby="c-h">
  {self.photo_tile("old-city-bw", "s5", pre)}
  <div class="t t-plain s7 rv"><h2 id="c-h">{E(A['credits_headline'])}</h2><p>{self.f(A['credits_lede'])}</p><ul class="credit-list">{rows}</ul></div>
</section>"""
        U = self.C["home"]["close"]
        close = self.close_row(pre, U["headline"], U["text"], "../updates/", U["action"], "city-above")
        return self.page("about/", self.p(A["title"]), self.p(A["description"]), "\n".join([head, method, credits, close]),
                         [{"@type": "ProfilePage", "url": f"{self.base}/about/", "mainEntity": {"@id": f"{self.base}/#author"}}])

    def updates(self):
        pre, U = "../", self.C["updates"]
        sub = self.cfg.get("subscribe") or {}
        fields = sub.get("fields") or {}
        live_form = sub.get("provider") == "google_form" and sub.get("action") and all(fields.get(k) for k in ("name", "contact", "industries"))
        fn = lambda k, fallback: E(fields.get(k) or fallback)
        no_js = (f'action="{E(sub["action"])}" method="post" target="_blank"' if live_form      # how the form posts without site.js
                 else f'action="{entities("mailto:" + self.au["email"])}" method="post" enctype="text/plain"')
        picks = "".join(f'<label class="pick"><input type="checkbox" name="{fn("industries", "industries")}" value="{E(v)}" data-key="{k}"{" checked" if k == "cafes" else ""}><span>{E(v)}</span></label>'
                        for k, v in U["picks"].items())
        mail = entities(self.mail)
        body = f"""<section class="board p-head updates" aria-labelledby="h">
  <div class="t tone-pink s5 name rv"><h1 id="h">{E(U['headline'])}</h1><p>{self.f(U['lede'])}</p></div>
  <form class="t tone-ink s7 sign rv" {no_js} data-provider="{'google_form' if live_form else 'email'}" data-action="{E(sub.get('action', '') if live_form else '')}"
    data-to="{entities(self.au['email'])}" data-subject="{E(self.brand)}: updates" data-thanks="{E(U['thanks'])}" data-thanks-email="{E(U['thanks_email'])}" novalidate>
    <label class="field"><span>{E(U['name'])}</span><input type="text" name="{fn('name', 'name')}" autocomplete="name" required maxlength="80"></label>
    <label class="field"><span>{E(U['contact'])}</span><input type="tel" name="{fn('contact', 'contact')}" autocomplete="tel" inputmode="tel" required maxlength="16" placeholder="{E(U['contact_hint'])}"></label>
    <fieldset class="picks"><legend>{E(U['pick'])}</legend>{picks}</fieldset>
    <label class="field field-q"><span>{E(U['question'])}</span><textarea name="{fn('question', 'question')}" rows="3" maxlength="1000" placeholder="{E(U['question_hint'])}"></textarea></label>
    <button class="btn btn-accent" type="submit">{E(U['send'])}</button>
    <p class="small note">{self.f(U['note'])}</p>
    <p class="status" role="status" aria-live="polite"></p>
  </form>
  {self.photo_tile("workshop", "s7", pre, "(max-width: 760px) 100vw, 58vw")}
  <div class="t tone-blush s5 ask rv" id="ask"><h2>{E(U['ask_headline'])}</h2><p>{self.f(U['ask_text'])}</p>
    <p class="email"><a href="{mail}">{entities(self.au['email'])}</a></p>
    <p class="acts"><a class="btn" href="{mail}">{E(U['email'])}</a><button type="button" class="btn btn-quiet copy" data-copy="{entities(self.au['email'])}">{E(U['copy'])}</button>
    <a class="btn btn-quiet" href="{self.au['linkedin']}" rel="noopener" target="_blank">{E(U['linkedin'])}</a></p>
    <p class="small copied" role="status" aria-live="polite"></p></div>
</section>"""
        return self.page("updates/", self.p(U["title"]), self.p(U["description"]), body)

    def not_found(self):
        """Served from any depth, so its links resolve against the site's own address (<base>)."""
        Nf = self.C["not_found"]
        body = f"""<section class="board p-head" aria-labelledby="h">
  <div class="t tone-blush s8 name"><h1 id="h">{E(Nf['headline'])}</h1></div>
  <div class="t t-plain s4"><p class="statement">{E(Nf['text'])}</p><p><a class="btn" href="./">{E(Nf['home'])}</a></p></div>
</section>"""
        return self.page("", f"Page not found · {self.brand}", self.p(self.C["home"]["description"]), body, not_found=True)


def build(overrides):
    s = Site(overrides)
    pages = {}
    for path, fn in zip(PAGES, [s.home, s.cafes, s.jewellery, s.nxt, s.about, s.updates]):
        s.used = []
        pages[path] = fn()
    s.used = []
    nf = s.not_found()
    if s.missing:
        raise BuildError("copy uses tokens the data doesn't have: " + ", ".join(sorted(set(s.missing))))

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for item in WEB.iterdir():
        if item.name.startswith("."):
            continue
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, DIST / item.name)
    for path, h in pages.items():
        (DIST / path).mkdir(parents=True, exist_ok=True)
        (DIST / path / "index.html").write_text(h, encoding="utf-8")
    (DIST / "404.html").write_text(nf, encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {s.base}/sitemap.xml\n", encoding="utf-8")
    urls = "".join(f"  <url><loc>{s.base}/{p}</loc><lastmod>{s.today}</lastmod><changefreq>weekly</changefreq><priority>{'1.0' if not p else '0.8'}</priority></url>\n"
                   for p in PAGES)
    (DIST / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      f"{urls}</urlset>\n", encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    if s.dom:
        (DIST / "CNAME").write_text(s.dom + "\n", encoding="utf-8")
    (DIST / "data").mkdir(exist_ok=True)
    (DIST / "data" / "sources.json").write_text(json.dumps(
        {k: {"source": d["_source"], "snapshot": d["meta"].get("snapshot"), "captured_on": d["meta"].get("captured_on")} for k, d in s.data.items()},
        indent=2), encoding="utf-8")
    return s.data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="append", default=[], help="industry=path to read that industry's data from a file instead of its site")
    a = ap.parse_args()
    try:
        data = build(dict(x.split("=", 1) for x in a.data))
    except BuildError as e:
        print(f"build failed: {e}", file=sys.stderr)
        sys.exit(1)
    for k, d in data.items():
        print(f"{k}: snapshot {d['meta'].get('snapshot')} from {d['_source']}")
    print(f"built {DIST}: {len(PAGES)} pages + 404")


if __name__ == "__main__":
    main()
