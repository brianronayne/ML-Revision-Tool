/* App controller: views, session loop, keyboard shortcuts. */
(() => {
  const cards = window.CARDS || [];
  let progress = SRS.loadProgress();

  // ---- session state ----
  let queue = [];
  let againQueue = [];
  let current = null;
  let revealed = false;
  let totalThisSession = 0;
  let counts = { seen: 0, again: 0, hard: 0, good: 0 };
  let activeTag = null;

  // ---- element refs ----
  const $ = (id) => document.getElementById(id);
  const views = { home: $("home"), review: $("review"), summary: $("summary") };

  function showView(name) {
    for (const [k, el] of Object.entries(views)) el.classList.toggle("hidden", k !== name);
  }

  // ---------- HOME ----------
  function renderHome() {
    progress = SRS.loadProgress();
    const tag = activeTag;
    const stats = SRS.getStats(cards, progress, tag);
    const seenToday = SRS.newCardsSeenToday(progress);

    $("statsGrid").innerHTML = [
      statCard(stats.new, "New", "accent"),
      statCard(stats.due, "Due now", "due"),
      statCard(stats.bucket_1 + stats.bucket_0, "Learning", "learn"),
      statCard(stats.bucket_2, "Known", "known"),
    ].join("");

    const limit = clampLimit($("newLimit").value);
    const due = SRS.getDueCards(cards, progress, tag, limit);
    const scope = tag ? `“${tag}”` : "all topics";
    $("dueHint").textContent = due.length
      ? `${due.length} card${due.length === 1 ? "" : "s"} ready in ${scope}.`
      : `Nothing due in ${scope} right now — come back later.`;

    $("deckMeta").textContent =
      `${cards.length} cards · ${Object.keys(SRS.allTags(cards)).length} topics · ${seenToday} new seen today`;
  }

  function statCard(value, label, kind) {
    return `<div class="stat-card ${kind}">
      <div class="stat-value">${value}</div>
      <div class="stat-label">${label}</div>
    </div>`;
  }

  function buildTagSelect() {
    const tagCounts = SRS.allTags(cards);
    const opts = [`<option value="">All topics (${cards.length})</option>`];
    for (const [tag, n] of Object.entries(tagCounts)) {
      opts.push(`<option value="${tag}">${tag} (${n})</option>`);
    }
    $("tagSelect").innerHTML = opts.join("");
  }

  const clampLimit = (v) => {
    let n = parseInt(v, 10);
    if (isNaN(n) || n < 0) n = 0;
    if (n > 200) n = 200;
    return n;
  };

  // ---------- SESSION ----------
  function startSession() {
    progress = SRS.loadProgress();
    activeTag = $("tagSelect").value || null;
    const limit = clampLimit($("newLimit").value);

    let due = SRS.getDueCards(cards, progress, activeTag, limit);
    if (!due.length) {
      renderHome();
      flashDueHint();
      return;
    }
    due = shuffle(due.slice());
    queue = due;
    againQueue = [];
    totalThisSession = due.length;
    counts = { seen: 0, again: 0, hard: 0, good: 0 };

    $("scopePill").textContent = activeTag ? activeTag : "all topics";
    showView("review");
    nextCard();
  }

  function nextCard() {
    if (!queue.length && againQueue.length) {
      queue = againQueue;
      againQueue = [];
    }
    if (!queue.length) return endSession();

    current = queue.shift();
    revealed = false;

    $("flashcard").classList.remove("flipped");
    $("ratingRow").classList.add("hidden");
    $("revealBtn").classList.remove("hidden");

    $("questionText").textContent = current.question;
    $("answerText").textContent = current.answer;
    $("frontSource").textContent = sourceShort(current.source);
    $("frontTags").innerHTML = (current.tags || [])
      .map((t) => `<span class="chip">${t}</span>`).join("");

    const remaining = queue.length + againQueue.length + 1;
    const done = counts.seen;
    $("progressLabel").textContent = `${done + 1} / ${done + remaining}`;
    const pct = totalThisSession ? (done / totalThisSession) * 100 : 0;
    $("progressFill").style.width = `${pct}%`;
  }

  function reveal() {
    if (revealed) return;
    revealed = true;
    $("flashcard").classList.add("flipped");
    $("revealBtn").classList.add("hidden");
    $("ratingRow").classList.remove("hidden");
  }

  function rate(rating) {
    if (!revealed || !current) return;
    SRS.updateProgress(progress, current.id, rating);
    SRS.saveProgress(progress);
    if (window.Auth && Auth.currentUser()) Auth.pushProgress(progress);

    counts.seen++;
    if (rating === 1) { counts.again++; againQueue.push(current); }
    else if (rating === 2) counts.hard++;
    else counts.good++;

    nextCard();
  }

  function endSession() {
    $("progressFill").style.width = "100%";
    $("summaryStats").innerHTML = [
      sumRow("Reviewed", counts.seen, "neutral"),
      sumRow("Good", counts.good, "good"),
      sumRow("Hard", counts.hard, "hard"),
      sumRow("Again", counts.again, "again"),
    ].join("");
    showView("summary");
  }

  function sumRow(label, value, kind) {
    return `<div class="sum-row ${kind}"><span>${label}</span><span class="sum-val">${value}</span></div>`;
  }

  // ---------- helpers ----------
  function shuffle(a) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function sourceShort(src = "") {
    return src.replace(/\.pdf$/i, "");
  }

  function flashDueHint() {
    const el = $("dueHint");
    el.classList.remove("pulse");
    void el.offsetWidth; // reflow to restart animation
    el.classList.add("pulse");
  }

  // ---------- events ----------
  $("startBtn").addEventListener("click", startSession);
  $("revealBtn").addEventListener("click", reveal);
  $("exitBtn").addEventListener("click", () => { renderHome(); showView("home"); });
  $("homeBtn").addEventListener("click", () => { renderHome(); showView("home"); });
  $("tagSelect").addEventListener("change", (e) => { activeTag = e.target.value || null; renderHome(); });
  $("newLimit").addEventListener("input", renderHome);

  $("ratingRow").addEventListener("click", (e) => {
    const btn = e.target.closest(".rate-btn");
    if (btn) rate(parseInt(btn.dataset.rating, 10));
  });

  $("resetBtn").addEventListener("click", () => {
    if (confirm("Reset all study progress? This cannot be undone.")) {
      SRS.resetProgress();
      progress = SRS.loadProgress();
      renderHome();
      showView("home");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (views.review.classList.contains("hidden")) return;
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      if (!revealed) reveal();
    } else if (revealed && ["1", "2", "3"].includes(e.key)) {
      e.preventDefault();
      rate(parseInt(e.key, 10));
    } else if (e.key === "Escape") {
      renderHome(); showView("home");
    }
  });

  // ---------- bridge for auth.js (optional) ----------
  window.App = {
    getProgress: () => progress,
    applyRemoteProgress(remote) {
      progress = remote;
      SRS.saveProgress(progress);
      renderHome();
    },
  };

  // ---------- init ----------
  buildTagSelect();
  renderHome();
  showView("home");
})();
