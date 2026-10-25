// Jaipur Index: the sign-up form and its "notify me" links. Progressive enhancement: without this file the form
// still posts (to the Google Form, or as an email), just without the checks and the thank-you.
(() => {
  const form = document.querySelector(".sign");
  if (!form) return;
  const status = form.querySelector(".up-status");
  const nameEl = form.querySelector('input[type="text"]'), telEl = form.querySelector('input[type="tel"]');
  const qEl = form.querySelector("textarea"), boxes = [...form.querySelectorAll('input[type="checkbox"]')];
  const isPhone = (v) => /^(\+?91|0)?[6-9]\d{9}$/.test(v.replace(/[\s()-]/g, ""));
  const say = (t) => { status.textContent = t; };

  // "Tell me when it's live" and "Vote" arrive with their box already ticked
  document.querySelectorAll("[data-pick]").forEach((a) => a.addEventListener("click", () => {
    const box = boxes.find((b) => b.dataset.key === a.dataset.pick);
    if (box) box.checked = true;
    setTimeout(() => (a.dataset.pick === "next" ? qEl : nameEl)?.focus({ preventScroll: true }), 600);
  }));

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
