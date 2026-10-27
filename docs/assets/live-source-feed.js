/* Public GitHub commit activity only: never a score, receipt or upload decision. */
(() => {
  const container = document.getElementById('live-source-feed');
  if (!container) return;
  const status = document.getElementById('live-source-status');
  const items = [...container.querySelectorAll('[data-repository]')];
  const cacheKey = 'gems91-source-commits-v1';
  const maxAge = 10 * 60 * 1000;

  function valid(item) {
    return item && /^[a-f0-9]{40}$/.test(item.sha) &&
      typeof item.date === 'string' && !Number.isNaN(Date.parse(item.date));
  }
  function display(element, record) {
    const value = element.querySelector('.commit-status');
    if (!valid(record)) {
      value.textContent = 'Unavailable — open repository';
      return false;
    }
    const repo = element.dataset.repository;
    const link = document.createElement('a');
    link.href = `https://github.com/buffedlizard55-lab/${repo}/commit/${record.sha}`;
    link.textContent = `${record.sha.slice(0, 10)} · ${record.date.replace('T', ' ').replace('Z', ' UTC')}`;
    value.replaceChildren(link);
    return true;
  }
  async function refresh() {
    let cached = {};
    try {
      const parsed = JSON.parse(sessionStorage.getItem(cacheKey) || '{}');
      if (parsed.rows && typeof parsed.rows === 'object') cached = parsed.rows;
    } catch (_) { /* Cache is optional and can be unavailable in private mode. */ }
    const fresh = {};
    const results = await Promise.all(items.map(async (element) => {
      const repo = element.dataset.repository;
      let record = cached[repo];
      const age = record && Date.now() - record.fetchedAt;
      if (!valid(record) || !Number.isFinite(age) || age < 0 || age >= maxAge) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        try {
          const response = await fetch(`https://api.github.com/repos/buffedlizard55-lab/${repo}/commits/main`, {
            headers: { Accept: 'application/vnd.github+json' }, cache: 'no-store', signal: controller.signal
          });
          if (!response.ok) throw new Error('GitHub feed unavailable');
          const json = await response.json();
          record = { sha: json.sha, date: json.commit && json.commit.committer && json.commit.committer.date, fetchedAt: Date.now() };
        } catch (_) { record = null; }
        finally { clearTimeout(timeout); }
      }
      if (valid(record)) fresh[repo] = record;
      return display(element, record);
    }));
    try { sessionStorage.setItem(cacheKey, JSON.stringify({ rows: fresh })); }
    catch (_) { /* The page remains useful without storage. */ }
    const count = results.filter(Boolean).length;
    status.textContent = count === items.length
      ? 'Public repository activity refreshed. This feed does not verify scores or submission readiness.'
      : `Public activity available for ${count} of ${items.length} sites; other links open the repositories. No score or readiness is inferred.`;
  }
  function refreshSafely() {
    refresh().catch(() => { status.textContent = 'Public activity unavailable; use the repository links. No score or readiness is inferred.'; });
  }
  refreshSafely();
  setInterval(refreshSafely, maxAge);
})();
