"""The gate. Separate from the build on purpose: it reads the finished page and the industry data afresh, and fails
if anything a visitor can read breaks the house rules.

  1. No figure typed into content/copy.yaml: every number there must come in as a {{token}}.
  2. Every number visible on every built page (text, title, description, share text) is found in an industry site's
     published data: a token value, a finding's value, or the wording of a published finding. Dates of the
     snapshot and of the build are allowed.
  3. Nothing for sale: no prices, fees, packages or "hire me".
  4. Jaipur's own dates (content/history.yaml) each carry a source and a quote, and the date is in the quote.

Usage: python pipeline/check.py   (run after build.py; it reads the data the build saved in .cache/)
"""
import argparse, html, json, re, sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from build import CACHE, addresses, load_data, findings  # noqa: E402  (the same loader, so both read the same file)

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
SELLING = re.compile(r"\b(hire me|consulting (?:offer|packages?|rates?)|book a call|pricing|per hour|our fees|retainer)\b", re.I)


class Visible(HTMLParser):
    """Collects what a person (or a search engine's snippet) can read: text outside scripts and styles, plus the
    title, meta descriptions, alt text and form placeholders."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "meta" and (a.get("name") in ("description", "twitter:title", "twitter:description")
                              or a.get("property") in ("og:title", "og:description", "og:image:alt")):
            self.out.append(a.get("content") or "")
        for k in ("alt", "placeholder", "aria-label"):
            if a.get(k):
                self.out.append(a[k])

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def norm(n):
    return n.replace(",", "")


def allowed_numbers(data):
    ok = set()
    def add_text(s):
        ok.update(norm(n) for n in NUM.findall(str(s)))
    for d in data.values():
        for v in (d.get("tokens") or {}).values():
            add_text(v)
        F = findings(d)
        ok.add(str(len(F)))                                    # {{cafes.findings}}: counted from the same list
        for f in F.values():
            v = f.get("value")
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            add_text(v)
            add_text(f.get("headline", ""))
            add_text(f.get("limit", ""))
        cap = d["meta"].get("captured_on")
        if cap:
            dd = date.fromisoformat(cap)
            ok.update({str(dd.day), str(dd.year)})
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="append", default=[])
    a = ap.parse_args()
    errors = []

    # 1. no literal figures in the copy
    copy = (ROOT / "content" / "copy.yaml").read_text(encoding="utf-8")
    for i, line in enumerate(copy.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        bare = re.sub(r"{{\s*[\w.]+\s*}}", "", line)
        if NUM.search(bare):
            errors.append(f"copy.yaml line {i}: a figure typed in by hand ({line.strip()[:80]})")

    # 2. every number on the page traces to published data
    cfg = yaml.safe_load((ROOT / "site.config.yaml").read_text(encoding="utf-8"))
    addresses(cfg)
    overrides = {f.stem: str(f) for f in CACHE.glob("*.json")}    # the data the build just used
    overrides.update(dict(x.split("=", 1) for x in a.data))
    data = load_data(cfg, overrides)
    ok = allowed_numbers(data)
    hist = yaml.safe_load((ROOT / "content" / "history.yaml").read_text(encoding="utf-8"))
    if not (hist.get("source") or {}).get("url"):
        errors.append("history.yaml: no source address")
    for k, fact in (hist.get("facts") or {}).items():
        v = str(fact.get("value", ""))
        if not v or v not in str(fact.get("quote", "")):
            errors.append(f"history.yaml: '{k}' ({v}) isn't in its own quote")
        else:
            ok.update(norm(n) for n in NUM.findall(v))
    pages = 0
    for page in sorted((ROOT / "dist").rglob("*.html")):
        rel = page.relative_to(ROOT / "dist")
        built = page.read_text(encoding="utf-8")
        allowed = set(ok)
        m = re.search(r"built (\d{1,2}) \w+ (\d{4})", built)
        if m:
            allowed.update(m.groups())
        p = Visible()
        p.feed(built)
        text = html.unescape(" ".join(p.out))
        for n in sorted({norm(x) for x in NUM.findall(text)}):
            if n not in allowed:
                ctx = re.search(rf".{{0,50}}\b{re.escape(n)}\b.{{0,30}}", text.replace(",", ""))
                errors.append(f"{rel} shows {n}, which isn't in the published data: …{ctx.group(0).strip() if ctx else ''}…")
        for hit in SELLING.findall(text):
            errors.append(f"{rel} reads like an offer: '{hit}'")
        pages += 1

    if errors:
        print("check failed:", *errors, sep="\n  ", file=sys.stderr)
        sys.exit(1)
    print(f"check passed: every number on {pages} pages traces to published data ({len(ok)} allowed values)")


if __name__ == "__main__":
    main()
