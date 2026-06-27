/* Spaced-repetition scheduler — a faithful port of src/srs.py.
   Progress is stored in localStorage instead of progress.json. */

const SRS = (() => {
  const BUCKET_INTERVALS = { 0: 0, 1: 1.0, 2: 4.0 }; // days; 0 = same session
  const DEFAULT_NEW_PER_DAY = 20;
  const STORAGE_KEY = "mlrev_progress_v1";

  function loadProgress() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch {
      return {};
    }
  }

  function saveProgress(progress) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  }

  function resetProgress() {
    localStorage.removeItem(STORAGE_KEY);
  }

  const dayKey = (d) => {
    // local calendar date as YYYY-MM-DD
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  };

  function filterByTag(cards, tag) {
    if (!tag) return cards;
    return cards.filter((c) => (c.tags || []).includes(tag));
  }

  function newCardsSeenToday(progress, now = new Date()) {
    const today = dayKey(now);
    let count = 0;
    for (const state of Object.values(progress)) {
      if (state.first_seen && dayKey(new Date(state.first_seen)) === today) count++;
    }
    return count;
  }

  function getDueCards(cards, progress, tag = null, newLimit = DEFAULT_NEW_PER_DAY) {
    const now = new Date();
    const remainingNew = Math.max(0, newLimit - newCardsSeenToday(progress, now));

    const scoped = filterByTag(cards, tag);
    const scheduled = [];
    const fresh = [];
    for (const card of scoped) {
      const state = progress[card.id];
      if (!state) {
        fresh.push(card);
      } else if (new Date(state.next_due) <= now) {
        scheduled.push(card);
      }
    }
    return scheduled.concat(fresh.slice(0, remainingNew));
  }

  /* rating: 1=Again, 2=Hard, 3=Good */
  function updateProgress(progress, cardId, rating) {
    const now = new Date();
    const state = progress[cardId] || { bucket: 0, interval_days: 0.0, total_reviews: 0 };

    if (!state.first_seen) state.first_seen = now.toISOString();

    const addDays = (days) => new Date(now.getTime() + days * 86400000).toISOString();

    if (rating === 1) {
      // Again — reset, re-queue within session
      state.bucket = 0;
      state.interval_days = 0.0;
      state.next_due = new Date(now.getTime() - 1000).toISOString();
    } else if (rating === 2) {
      // Hard
      state.bucket = 1;
      state.interval_days = BUCKET_INTERVALS[1];
      state.next_due = addDays(BUCKET_INTERVALS[1]);
    } else {
      // Good — promote, interval doubles once in bucket 2
      const prevBucket = state.bucket || 0;
      const newBucket = Math.min(prevBucket + 1, 2);
      const prevInterval = state.interval_days || 0.0;
      let newInterval;
      if (newBucket === 2) {
        newInterval = Math.max(prevInterval * 2.0, BUCKET_INTERVALS[2]);
      } else {
        newInterval = BUCKET_INTERVALS[newBucket];
      }
      state.bucket = newBucket;
      state.interval_days = newInterval;
      state.next_due = addDays(newInterval);
    }

    state.total_reviews = (state.total_reviews || 0) + 1;
    progress[cardId] = state;
  }

  function getStats(cards, progress, tag = null) {
    const counts = { new: 0, due: 0, bucket_0: 0, bucket_1: 0, bucket_2: 0 };
    const now = new Date();
    for (const card of filterByTag(cards, tag)) {
      const state = progress[card.id];
      if (!state) {
        counts.new++;
      } else {
        counts[`bucket_${state.bucket}`]++;
        if (new Date(state.next_due) <= now) counts.due++;
      }
    }
    return counts;
  }

  function allTags(cards) {
    const counts = {};
    for (const card of cards) {
      for (const tag of card.tags || []) counts[tag] = (counts[tag] || 0) + 1;
    }
    return Object.fromEntries(
      Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    );
  }

  return {
    DEFAULT_NEW_PER_DAY,
    loadProgress, saveProgress, resetProgress,
    filterByTag, newCardsSeenToday, getDueCards,
    updateProgress, getStats, allTags,
  };
})();
