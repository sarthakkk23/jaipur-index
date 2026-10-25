// Jaipur Index. Progressive enhancement only: every page is complete without this file.
(() => {
  window.__board = true;
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- entrances: tiles rise in, a board at a time, staggered by position; never a gate ----------
  const tiles = [...document.querySelectorAll(".rv")];
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
        t.classList.add("in");
        io.unobserve(t);
      });
    }, { rootMargin: "0px 0px -6% 0px" });
    tiles.forEach((t) => io.observe(t));
  } else showAll();

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
