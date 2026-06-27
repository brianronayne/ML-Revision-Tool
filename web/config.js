// Supabase configuration for cross-device login & sync.
//
// Leave both strings empty to run in LOCAL-ONLY mode: progress stays in this
// browser (exactly the default behaviour, no accounts). Fill them in to enable
// sign-in and cloud sync:
//
//   1. Create a free project at https://supabase.com
//   2. Run supabase/schema.sql in the project's SQL editor
//   3. Project Settings > API: copy the "Project URL" and the "anon public" key
//   4. Paste them below, commit, and redeploy.
//
// The anon key is SAFE to expose publicly — Row-Level Security restricts every
// user to their own data.
window.MLREV_CONFIG = {
  SUPABASE_URL: "",
  SUPABASE_ANON_KEY: "",
};
