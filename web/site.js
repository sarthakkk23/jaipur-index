// Pink City Papers. Progressive enhancement only: every page is complete without this file.
(() => {
  window.__board = true;
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- watch: run once when an element comes into view. If the observer never reports, show everything; never a gate ----------
  const watch = (els, onIn, margin = "0px 0px -6% 0px") => {
    if (!els.length) return;
    if (reduce || !("IntersectionObserver" in window)) { els.forEach(onIn); return; }
    let alive = false;
    setTimeout(() => { if (!alive) els.forEach(onIn); }, 2000);
    const io = new IntersectionObserver((es) => {
      alive = true;
      es.forEach((e) => { if (e.isIntersecting) { onIn(e.target); io.unobserve(e.target); } });
    }, { rootMargin: margin });
    els.forEach((t) => io.observe(t));
  };

  // ---------- entrances: tiles rise in, a board at a time, staggered by position ----------
  watch([...document.querySelectorAll(".rv")], (t) => {
    const sib = [...(t.parentElement?.children || [])];
    t.style.transitionDelay = `${Math.min(6, Math.max(0, sib.indexOf(t))) * 75}ms`;
    t.classList.add("in");
  });

  // ---------- headings rise word by word: each word in a clipped span, the text itself unchanged ----------
  if (!reduce) {
    const heads = [...document.querySelectorAll("main h2")].filter((h) => !h.closest(".hx"));
    heads.forEach((h) => {
      let k = 0;
      const walk = (node) => [...node.childNodes].forEach((n) => {
        if (n.nodeType === 1) return walk(n);
        if (n.nodeType !== 3 || !n.textContent.trim()) return;
        const frag = document.createDocumentFragment();
        n.textContent.split(/(\s+)/).forEach((part) => {
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.append(part); return; }
          const w = document.createElement("span"), i = document.createElement("span");
          w.className = "w"; i.textContent = part; i.style.setProperty("--k", k++); w.append(i); frag.append(w);
        });
        n.replaceWith(frag);
      });
      walk(h);
      h.classList.add("split");
    });
    watch(heads, (h) => h.classList.add("in"), "0px 0px -10% 0px");
  }

  // ---------- big figures count up from zero when they arrive; the page's own number is always what's left ----------
  const ease = (t) => 1 - Math.pow(2, -10 * t);
  const count = (el, delay) => {
    const txt = el.textContent.trim(), m = txt.match(/^(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?$/);
    if (!m) return;
    const commas = m[1].includes(","), dec = m[2] ? m[2].length - 1 : 0, end = parseFloat(txt.replace(/,/g, ""));
    const fmt = new Intl.NumberFormat("en-US", { useGrouping: commas, minimumFractionDigits: dec, maximumFractionDigits: dec });
    el.style.display = "inline-block"; el.style.minWidth = `${el.getBoundingClientRect().width}px`;
    el.textContent = fmt.format(0);
    setTimeout(() => {
      const t0 = performance.now(), dur = end < 20 ? 900 : 1400;
      const tick = (now) => {
        const p = Math.min(1, (now - t0) / dur);
        el.textContent = p < 1 ? fmt.format(end * ease(p)) : txt;
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      setTimeout(() => { el.textContent = txt; }, dur + 400);   // if frames stall (a background tab), the real figure still lands
    }, delay);
  };
  if (!reduce) {
    const first = !root.classList.contains("seen");
    watch([...document.querySelectorAll(".hx-n .n, .fig .n, .ans-figs .n")].filter((n) => !n.closest(".gq")),
      (n) => count(n, n.closest(".hx") ? (first ? 1850 : 700) : 150), "0px 0px -8% 0px");
  }

  // ---------- the footer's name builds itself, block by block ----------
  const blocks = document.querySelector(".blocks");
  if (blocks) {
    [...blocks.children].forEach((b, j) => b.style.setProperty("--j", j));
    watch([blocks], (b) => b.classList.add("in"), "0px 0px -15% 0px");
  }

  // ---------- the bar steps aside while you read down, and comes back when you scroll up ----------
  const bar = document.querySelector(".bar"), menu = document.querySelector(".menu");
  if (bar) {
    let lastY = scrollY, ticking = false;
    addEventListener("scroll", () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = scrollY, d = y - lastY;
        if (Math.abs(d) > 6) { bar.classList.toggle("tuck", d > 0 && y > 240 && !menu?.open); lastY = y; }
        ticking = false;
      });
    }, { passive: true });
  }

  // ---------- the main buttons lean toward the pointer, a little ----------
  if (!reduce && matchMedia("(hover: hover) and (pointer: fine)").matches) {
    document.querySelectorAll(".hx-acts .btn, .bar-btn, .act-go .btn").forEach((b) => {
      b.addEventListener("pointermove", (e) => {
        const r = b.getBoundingClientRect();
        const dx = (e.clientX - r.left - r.width / 2) / (r.width / 2), dy = (e.clientY - r.top - r.height / 2) / (r.height / 2);
        b.style.translate = `${(dx * 6).toFixed(1)}px ${(dy * 4).toFixed(1)}px`;
      });
      b.addEventListener("pointerleave", () => { b.style.translate = ""; });
    });
  }

  // ---------- the story: one moment at a time; the reader turns the page ----------
  const box = document.querySelector(".story-box");
  if (box) {
    const steps = [...box.querySelectorAll(".step")], dots = [...box.querySelectorAll(".dot-btn")];
    const next = box.querySelector(".story-next"), back = box.querySelector(".story-back"), nav = box.querySelector(".story-nav");
    const today = box.querySelector(".today img");
    let at = 0;
    const show = (i, dir) => {
      at = (i + steps.length) % steps.length;
      steps.forEach((s, n) => {
        const on = n === at;
        s.hidden = !on;
        if (on && dir && !reduce) { s.classList.add(dir > 0 ? "from-right" : "from-left"); void s.offsetWidth; s.classList.remove("from-right", "from-left"); }
      });
      dots.forEach((d, n) => { d.classList.toggle("seen", n < at); n === at ? d.setAttribute("aria-current", "step") : d.removeAttribute("aria-current"); });
      box.dataset.stage = String(at);              // the city builds to this moment
      if (at >= 1) today?.setAttribute("loading", "eager");   // fetch today's photograph before the last page
      back.disabled = at === 0;
      next.textContent = at === steps.length - 1 ? next.dataset.again : next.dataset.next;
    };
    box.classList.add("story-on");
    nav.hidden = false;
    next.addEventListener("click", () => show(at === steps.length - 1 ? 0 : at + 1, 1));
    back.addEventListener("click", () => show(at - 1, -1));
    dots.forEach((d, n) => d.addEventListener("click", () => show(n, n > at ? 1 : -1)));
    box.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") { e.preventDefault(); show(Math.min(at + 1, steps.length - 1), 1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); show(Math.max(at - 1, 0), -1); }
    });
    // a swipe on a phone turns the page too
    let x0 = null;
    const swipe = box.querySelector(".story-body");
    swipe.addEventListener("pointerdown", (e) => { x0 = e.clientX; });
    swipe.addEventListener("pointerup", (e) => {
      if (x0 === null) return;
      const dx = e.clientX - x0; x0 = null;
      if (Math.abs(dx) > 50) dx < 0 ? show(Math.min(at + 1, steps.length - 1), 1) : show(Math.max(at - 1, 0), -1);
    });
    show(0, 0);
  }

  // ---------- jewellery: one finding at a time, then an offer to read the rest ----------
  const jf = document.querySelector("[data-jf]");
  if (jf) {
    const cards = [...jf.querySelectorAll(".jf-card")], marks = [...jf.querySelectorAll(".jf-marks i")];
    const nav = jf.querySelector(".jf-nav"), end = jf.querySelector(".jf-end"), again = jf.querySelector(".jf-again");
    let at = 0;
    const show = (n, scroll) => {
      at = n;
      const done = n >= cards.length;
      cards.forEach((c, i) => { c.hidden = i !== n; c.classList.toggle("in", i === n); });
      marks.forEach((m, i) => { m.classList.toggle("now", i === n); m.classList.toggle("done", i < n); });
      end.hidden = !done; end.classList.toggle("in", done);
      nav.hidden = done; again.hidden = !done;
      if (scroll) jf.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "nearest" });
    };
    jf.querySelector(".jf-next").addEventListener("click", () => show(at + 1, true));
    again.addEventListener("click", () => show(0, true));
    jf.querySelector(".jf-marks").hidden = false;
    jf.classList.add("jf-on");
    show(0, false);
  }

  // ---------- guess first: the reader guesses, then sees the real figure ----------
  const game = document.querySelector(".guess");
  if (game) {
    const S = JSON.parse(game.dataset.s), total = +game.dataset.total;
    const cards = [...game.querySelectorAll(".gq")], marks = [...game.querySelectorAll(".gq-marks i")];
    const nav = game.querySelector(".gq-nav"), nextBtn = game.querySelector(".gq-next"), end = game.querySelector(".gq-end");
    let at = 0, hits = 0;
    const fill = (t, o) => t.replace(/\{(\w+)\}/g, (_, k) => o[k]);
    cards.forEach((c) => {
      const range = c.querySelector("input"), out = c.querySelector("output"), unit = c.dataset.unit;
      const say = () => { out.textContent = `${range.value}${unit}`; range.setAttribute("aria-valuetext", `${range.value}${unit}`); };
      range.addEventListener("input", say);
      say();
      c.querySelector(".gq-lock").addEventListener("click", () => {
        const guess = +range.value, real = parseFloat(c.dataset.value), d = guess - real, off = Math.abs(d);
        const word = off <= 2 ? S.spot : off <= 10 ? S.near : S.far;   // "close" means within ten points, the same line the score uses
        c.querySelector(".gq-verdict").textContent = off <= 2 ? word : `${word} ${fill(S.gap, { d: Math.round(off), dir: d < 0 ? S.under : S.over })}`;
        if (off <= 10) hits++;
        c.classList.add("shown");
        range.disabled = true; c.querySelector(".gq-lock").disabled = true;
        requestAnimationFrame(() => {
          c.querySelector(".gq-you").style.setProperty("--w", `${guess}%`);
          c.querySelector(".gq-real").style.setProperty("--w", `${Math.min(100, real)}%`);
        });
        nextBtn.textContent = at === total - 1 ? S.finish : S.next;
        nav.hidden = false;
        nextBtn.focus({ preventScroll: true });
        if (matchMedia("(max-width: 900px)").matches)   // on a phone the answer is below the slider: bring it into view
          c.querySelector(".gq-reveal").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
      });
    });
    const show = (i) => {
      at = i;
      cards.forEach((c, n) => { c.hidden = n !== i; });
      marks.forEach((m, n) => { m.classList.toggle("done", n < i); m.classList.toggle("now", n === i); });
      nav.hidden = true;
    };
    const reset = () => {
      hits = 0;
      cards.forEach((c) => {
        c.classList.remove("shown");
        const r = c.querySelector("input"); r.disabled = false; r.value = 50; r.dispatchEvent(new Event("input"));
        c.querySelector(".gq-lock").disabled = false;
        c.querySelectorAll(".gq-bars i").forEach((b) => b.style.removeProperty("--w"));
      });
      end.hidden = true; game.querySelector(".gq-list").hidden = false; game.querySelector(".gq-marks").hidden = false;
      show(0);
    };
    nextBtn.addEventListener("click", () => {
      if (at < total - 1) { show(at + 1); cards[at].querySelector("input").focus({ preventScroll: true }); return; }
      game.querySelector(".gq-score").textContent = fill(S.done, { n: hits, total });
      game.querySelector(".gq-more").textContent = fill(S.done_more, { all: game.dataset.all });
      game.querySelector(".gq-list").hidden = true; game.querySelector(".gq-marks").hidden = true; nav.hidden = true;
      end.hidden = false;
    });
    game.querySelector(".gq-again").addEventListener("click", reset);
    game.classList.add("gq-on");
    game.querySelector(".gq-marks").hidden = false;
    show(0);
  }

  // ---------- find your trade: pick one, the board answers in place ----------
  const answer = document.getElementById("answer");
  const trades = [...document.querySelectorAll(".trade[data-trade]")];
  if (answer && trades.length) {
    const panels = [...answer.querySelectorAll(".ans")];
    const pick = (key, focus) => {
      trades.forEach((t) => t.setAttribute("aria-pressed", String(t.dataset.trade === key)));
      panels.forEach((p) => {
        const on = p.dataset.for === key;
        p.hidden = !on;
        if (on) { p.classList.remove("swap"); void p.offsetWidth; p.classList.add("swap"); }
      });
      if (focus && matchMedia("(max-width: 900px)").matches) answer.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    };
    trades.forEach((t) => {
      t.setAttribute("role", "button");
      t.addEventListener("click", (e) => { e.preventDefault(); pick(t.dataset.trade, true); });
      t.addEventListener("keydown", (e) => { if (e.key === " ") { e.preventDefault(); pick(t.dataset.trade, true); } });
    });
    pick("cafes", false);
  }

  // ---------- copy the email address in one tap ----------
  document.querySelectorAll(".copy[data-copy]").forEach((b) => b.addEventListener("click", async () => {
    const say = b.closest(".t")?.querySelector(".copied");
    try { await navigator.clipboard.writeText(b.dataset.copy); if (say) say.textContent = "Copied. Paste it into any email."; }
    catch { if (say) say.textContent = b.dataset.copy; }
  }));

  // ---------- the sign-up form ----------
  const form = document.querySelector(".sign");
  if (!form) return;
  const status = form.querySelector(".status");
  const nameEl = form.querySelector('input[type="text"]'), telEl = form.querySelector('input[type="tel"]');
  const qEl = form.querySelector("textarea"), boxes = [...form.querySelectorAll('input[type="checkbox"]')];
  const say = (t) => { status.textContent = t; };
  const isPhone = (v) => /^(\+?91|0)?[6-9]\d{9}$/.test(v.replace(/[\s()-]/g, ""));

  // arriving from "Tell me when it's live" or "Vote for this": the right box is ticked, the trade is written in
  const q = new URLSearchParams(location.search);
  const want = q.get("pick");
  if (want) boxes.forEach((b) => { b.checked = b.dataset.key === want || (b.dataset.key === "cafes" && want === "cafes"); });
  if (q.get("trade") && !qEl.value) qEl.value = `I'd like the next index to be: ${q.get("trade").slice(0, 60)}.`;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!nameEl.value.trim()) { say("Please add your name."); nameEl.focus(); return; }
    if (!isPhone(telEl.value.trim())) { say("Please add a 10-digit Indian mobile number."); telEl.focus(); return; }
    const picked = boxes.filter((b) => b.checked).map((b) => b.value);
    if (!picked.length) { say("Pick at least one thing to hear about."); boxes[0].focus(); return; }

    if (form.dataset.provider !== "google_form") {
      // no form connected yet: hand the details to the person's own email app, addressed to Sarthak
      const body = [`Name: ${nameEl.value.trim()}`, `WhatsApp: ${telEl.value.trim()}`, `Send me: ${picked.join(", ")}`,
        qEl.value.trim() ? `\nWhat I wish I knew:\n${qEl.value.trim()}` : ""].join("\n");
      location.href = `mailto:${form.dataset.to}?subject=${encodeURIComponent(form.dataset.subject)}&body=${encodeURIComponent(body)}`;
      say(form.dataset.thanksEmail);
      return;
    }
    form.classList.add("sending"); say("Sending…");
    try {
      await fetch(form.dataset.action, { method: "POST", mode: "no-cors", body: new FormData(form) });   // Google Forms gives no readable reply
      form.classList.add("done"); say(form.dataset.thanks);
      form.reset();
    } catch { say("That didn't go through. Please try again in a moment."); }
    form.classList.remove("sending");
  });
})();
