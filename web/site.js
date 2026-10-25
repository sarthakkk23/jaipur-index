// Jaipur Index. Progressive enhancement only: every page is complete without this file.
(() => {
  window.__board = true;
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  // ---------- entrances: tiles rise in, a board at a time, staggered by position; never a gate ----------
  const tiles = [...document.querySelectorAll(".rv, .sh, .cell, .mosaic")];
  const showAll = () => tiles.forEach((t) => t.classList.add("in"));
  if (!reduce && "IntersectionObserver" in window) {
    let alive = false;
    setTimeout(() => { if (!alive) showAll(); }, 2000);
    const io = new IntersectionObserver((es) => {
      alive = true;
      es.forEach((e) => {
        if (!e.isIntersecting) return;
        const t = e.target, sib = [...(t.parentElement?.children || [])];
        t.style.transitionDelay = `${Math.min(6, Math.max(0, sib.indexOf(t))) * 75}ms`;
        if (t.classList.contains("mosaic")) [...t.children].forEach((c, i) => { c.style.transitionDelay = `${(i % 6) * 60 + Math.floor(i / 6) * 90}ms`; });
        t.classList.add("in");
        io.unobserve(t);
      });
    }, { rootMargin: "0px 0px -6% 0px" });
    tiles.forEach((t) => io.observe(t));
  } else showAll();

  // ---------- the hero sheet: columns drift at their own speeds as the page scrolls ----------
  const cols = [...document.querySelectorAll(".sheet-col[data-speed]")];
  if (cols.length && !reduce) {
    const wide = matchMedia("(min-width: 761px)");
    let ticking = false;
    const frame = () => {
      ticking = false;
      const y = clamp(scrollY, 0, innerHeight * 1.2);
      cols.forEach((c) => { c.style.transform = wide.matches ? `translateY(${(-y * +c.dataset.speed).toFixed(1)}px)` : ""; });
    };
    addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }, { passive: true });
    wide.addEventListener?.("change", frame);
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
