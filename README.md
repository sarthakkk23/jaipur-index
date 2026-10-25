# Jaipur Index (working name)

The main website for Sarthak Oberoi's Jaipur industry research: the front door that links to every industry site.
In the wider project folder, read `../GAMEPLAN.md` first.

**Live industry:** [Jaipur Café Index](https://sarthakkk23.github.io/jaipur-cafe-pulse/) · **Next:** jewellery ·
**Preview:** https://sarthakkk23.github.io/jaipur-index/

## Its job

- **It makes owners want to come here.** It's a free, open project, positioned as the one-stop place for anyone
  running, or planning to start, a business in Jaipur, of any size. It uses sales principles to win attention, trust and
  return visits, not to sell: the problem and a promise first, proof from real findings, anticipation for what's next,
  and one clear call to action.
- **Nothing is for sale.** It has no consulting offer, prices or "hire me". The gate fails the build on wording that
  reads like an offer.
- **It doesn't publish research itself.** The industry sites do, and this site sends people to them.
- **It looks like the café site.** The fonts, colours, layout and motion layer are copied from `cafes/web/v2/`.

## How it fits together

```
site.config.yaml        brand, domain, industry addresses, sign-up form, which café findings to show. ONE FILE.
content/copy.yaml       every word on the page; numbers only as {{tokens}}
pipeline/build.py       config + copy + each live industry's published data + web/ -> dist/ (static, no framework)
pipeline/check.py       the gate, written separately: every number on the built page must trace to published data
pipeline/make_images.swift   draws og.jpg (share card) and the icons; run on a Mac when the look changes
web/v2.css, web/v2.js   shared with the café index (keep in step); master.css / master.js add the front door's parts
.github/workflows/site.yml   PRs: build + gate. main and site/** branches: + deploy. Twice a week: rebuild
```

**Where the numbers come from.** None are typed in. At build time `build.py` reads the café index's own published
file (`<café site>/data/insights.json`) and fills the `{{tokens}}` in the copy from it. The hero's rotating finding and
the proof cards are the café index's published findings, picked by id in `site.config.yaml`. The site rebuilds twice
a week, so the front door follows each café refresh without anyone editing it. `check.py` then reads the finished page
and fails if any visible number isn't in that data.

## Build locally

```bash
./build.sh                                            # café figures from the live café site
./build.sh ../cafes/data/public/insights_latest.json  # or from a local copy
python3 -m http.server 8420 --directory dist
```

## Switching to your own domain (one line)

1. Buy the domain, and point it and the `cafes` and `jewellery` subdomains at GitHub Pages (DNS: `A`/`AAAA` records for
   the apex, a `CNAME` to `sarthakkk23.github.io` for each subdomain).
2. Move the café site to `cafes.<domain>`: set its custom domain in its repo's Pages settings and its `base_url` in
   `cafes/config.yaml`. GitHub redirects the old github.io address to the new one.
3. Here, set `brand.domain` in `site.config.yaml`. Every link, canonical tag, the sitemap and the share card's address
   follow, and the build writes the `CNAME` file. Then set the same domain under this repo's Settings → Pages.

Do step 3 on the same day as step 2, so the front door never links to a café address that isn't live yet. Renaming
the brand is the line above it, `brand.name`.

## Setting up the sign-up form (about 5 minutes)

Until this is done, the form still works: "Send" opens the visitor's email app with their details addressed to you.

1. In Google Forms, create a form called "Jaipur Index: updates" with four questions, in this order:
   - **Your name**: short answer, required
   - **WhatsApp number**: short answer, required
   - **Send me**: checkboxes, required, with exactly these options: `Cafés`, `Jewellery, when it launches`,
     `The next industry`
   - **What do you wish you knew about your industry?**: paragraph, optional
2. Under Responses, link it to a new Google Sheet.
3. Click ⋮ → *Get pre-filled link*, fill each answer with something, then *Get link*. The link contains one
   `entry.123456789=` per question; those numbers are the field IDs.
4. In `site.config.yaml`, under `subscribe`, set `provider: google_form`, set `action` to the form's address with
   `/viewform` replaced by `/formResponse`, and paste the four `entry.…` IDs into `fields`.

## House rules

- Every number comes from an industry site's published data, and the gate enforces it. A blank beats a guess.
- Name no business. Criticise no business, area or community.
- Nothing for sale.
- These are defaults: Sarthak can change any of them.

## Licence

Code: MIT (see LICENSE). Photographs are from Unsplash, credited in the footer.
