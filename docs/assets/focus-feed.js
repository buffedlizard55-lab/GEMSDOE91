/* Optional public GitHub head checks. No credentials, rasters or score scraping. */
(() => {
  const button = document.getElementById('refresh-focus');
  const status = document.getElementById('focus-status');
  const rows = [...document.querySelectorAll('[data-focus-site]')];
  if (!button || !status || !rows.length) return;
  const getHead = async number => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(`https://api.github.com/repos/buffedlizard55-lab/GEMSDOE${number}/commits/main`, {
        headers: { Accept: 'application/vnd.github+json' },
        credentials: 'omit', cache: 'no-store', signal: controller.signal
      });
      if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
      const data = await response.json();
      if (typeof data.sha !== 'string' || !/^[0-9a-f]{40}$/.test(data.sha)) throw new Error('Invalid commit identity');
      return data.sha;
    } finally {
      clearTimeout(timeout);
    }
  };
  button.addEventListener('click', async () => {
    button.disabled = true;
    status.textContent = 'Checking public GitHub main commit heads…';
    try {
      const results = await Promise.allSettled(rows.map(row => {
        const number = row.dataset.focusSite;
        if (!/^\d{1,3}$/.test(number)) throw new Error('Invalid repository');
        return getHead(number);
      }));
      let success = 0;
      results.forEach((result, index) => {
        const row = rows[index];
        const detail = row.querySelector('[data-focus-detail]');
        if (result.status === 'fulfilled') {
          const old = row.querySelector('[data-focus-link]');
          const link = document.createElement('a');
          link.dataset.focusLink = '';
          link.href = `https://github.com/buffedlizard55-lab/GEMSDOE${row.dataset.focusSite}/commit/${result.value}`;
          link.textContent = result.value.slice(0, 12);
          old.replaceWith(link);
          detail.textContent = 'live main head · page and raster not re-audited';
          success += 1;
        } else {
          detail.textContent = 'refresh unavailable · previous link retained';
        }
      });
      status.textContent = `${success} of ${rows.length} public heads checked at ${new Date().toISOString()} (browser clock). ${rows.length - success} unavailable; no scores verified.`;
    } catch (error) {
      status.textContent = 'Refresh unavailable; saved snapshots remain visible. No scores verified.';
    } finally {
      button.disabled = false;
    }
  });
})();
