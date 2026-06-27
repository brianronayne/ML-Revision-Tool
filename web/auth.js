/* Optional cloud login & progress sync via Supabase.
   Degrades gracefully: with no config or no SDK loaded, the app stays
   fully functional in local-only mode and the auth UI stays hidden. */
window.Auth = (() => {
  const cfg = window.MLREV_CONFIG || {};
  const ready = !!(cfg.SUPABASE_URL && cfg.SUPABASE_ANON_KEY && window.supabase);

  let client = null;
  let user = null;
  let pushTimer = null;
  let handledUserId = null;
  const els = {};

  function cacheEls() {
    const ids = ["authArea", "signInBtn", "signOutBtn", "userEmail", "authModal",
      "authEmail", "sendLinkBtn", "googleBtn", "closeAuthModal", "authMsg"];
    ids.forEach((id) => (els[id] = document.getElementById(id)));
  }

  function renderUser() {
    if (!els.authArea) return;
    els.authArea.classList.remove("hidden");
    const signedIn = !!user;
    els.signInBtn.classList.toggle("hidden", signedIn);
    els.signOutBtn.classList.toggle("hidden", !signedIn);
    els.userEmail.classList.toggle("hidden", !signedIn);
    els.userEmail.textContent = signedIn ? (user.email || "signed in") : "";
  }

  function openModal(open) {
    els.authModal.classList.toggle("hidden", !open);
    if (open) { els.authMsg.textContent = ""; els.authEmail.focus(); }
  }

  async function fetchCloud() {
    const { data, error } = await client
      .from("user_progress").select("progress").eq("user_id", user.id).maybeSingle();
    if (error) { console.warn("[auth] fetch:", error.message); return {}; }
    return (data && data.progress) || {};
  }

  function pushProgress(progress) {
    if (!user || !client) return;
    clearTimeout(pushTimer);
    pushTimer = setTimeout(async () => {
      const { error } = await client.from("user_progress").upsert({
        user_id: user.id, progress, updated_at: new Date().toISOString(),
      });
      if (error) console.warn("[auth] push:", error.message);
    }, 1200);
  }

  async function onSignedIn() {
    if (user.id === handledUserId) return; // already merged this session
    handledUserId = user.id;
    renderUser();
    const cloud = await fetchCloud();
    const local = (window.App && window.App.getProgress()) || {};
    const merged = window.SRS.mergeProgress(local, cloud);
    if (window.App) window.App.applyRemoteProgress(merged);
    pushProgress(merged); // sync any local-only cards back up
  }

  function wireUI() {
    cacheEls();
    if (!els.authArea) return;
    els.signInBtn.addEventListener("click", () => openModal(true));
    els.closeAuthModal.addEventListener("click", () => openModal(false));
    els.authModal.addEventListener("click", (e) => { if (e.target === els.authModal) openModal(false); });
    els.signOutBtn.addEventListener("click", () => client.auth.signOut());
    els.sendLinkBtn.addEventListener("click", async () => {
      const email = els.authEmail.value.trim();
      if (!email) { els.authMsg.textContent = "Enter your email."; return; }
      els.authMsg.textContent = "Sending…";
      const { error } = await client.auth.signInWithOtp({
        email, options: { emailRedirectTo: window.location.href },
      });
      els.authMsg.textContent = error ? error.message : "Check your email for a sign-in link.";
    });
    els.googleBtn.addEventListener("click", async () => {
      const { error } = await client.auth.signInWithOAuth({
        provider: "google", options: { redirectTo: window.location.href },
      });
      if (error) els.authMsg.textContent = error.message;
    });
  }

  async function init() {
    if (!ready) return; // local-only mode
    try {
      client = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
      wireUI();
      client.auth.onAuthStateChange((_event, session) => {
        const next = session ? session.user : null;
        const wasSignedIn = !!user;
        user = next;
        if (user) { openModal(false); onSignedIn(); }
        else { if (wasSignedIn) handledUserId = null; renderUser(); }
      });
    } catch (e) {
      console.warn("[auth] init failed:", e);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return { pushProgress, currentUser: () => user, isReady: () => ready };
})();
