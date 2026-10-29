/* EcoIQ Business OS private process workspace — progressive browser UI.
 * No framework/build needed; same-origin Django API remains the authority.
 * Never cache/report raw CSV, source references or sensitive server errors.
 */
(function () {
  'use strict';

  const root = document.getElementById('po-workspace');
  const select = document.getElementById('po-project');
  if (!root || !select) return;

  const fileInput = document.getElementById('po-file');
  const submit = document.getElementById('po-submit');
  const refresh = document.getElementById('po-refresh');
  const previous = document.getElementById('po-prev');
  const next = document.getElementById('po-next-page');
  const pageLabel = document.getElementById('po-page');
  const rows = document.getElementById('po-history-rows');
  const historyStatus = document.getElementById('po-history-status');
  const permission = document.getElementById('po-permission');
  const feedback = document.getElementById('po-upload-feedback');
  const kpiValue = document.getElementById('po-kpi');
  const kpiNote = document.getElementById('po-kpi-note');
  const evidence = document.getElementById('po-evidence');
  const nextStage = document.getElementById('po-next');
  const token = root.querySelector('input[name=csrfmiddlewaretoken]');
  const limit = 512 * 1024;

  let page = 1;
  let controller = null;
  let busy = false;
  let requestSequence = 0;

  const stages = {
    COLLECT_EVIDENCE: 'Collect evidence',
    REPAIR_FLOW_GRAPH: 'Repair flow data',
    RUN_FALSIFICATION: 'Test possible causes',
    HUMAN_REVIEW_REQUIRED: 'Human review required',
    HUMAN_REVIEW_FOR_IMPLEMENTATION: 'Human approval required',
    SIMULATE_ISLAH: 'Simulate improvement',
    DESIGN_ISLAH: 'Design improvement',
    IHSAN_OPTIMISATION: 'Continue improvement',
  };

  const number = (value) => {
    if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
    return new Intl.NumberFormat('en-GB', {
      maximumFractionDigits: 4,
    }).format(value);
  };

  function endpoint(slug) {
    // Encode only the selected, server-rendered project slug.
    return '/api/v2/projects/' + encodeURIComponent(slug) + '/process-analyses/';
  }

  function canUpload() {
    const option = select.options[select.selectedIndex];
    return Boolean(option && option.dataset.upload === '1');
  }

  function setFeedback(message, isError) {
    feedback.textContent = message;
    feedback.classList.toggle('po-feedback--error', Boolean(isError));
    feedback.setAttribute('role', isError ? 'alert' : 'status');
  }

  function setSummary(run) {
    if (!run) {
      kpiValue.textContent = '—';
      kpiNote.textContent = 'No recorded analysis';
      evidence.textContent = '—';
      nextStage.textContent = '—';
      return;
    }
    const result = run.result || {};
    const kpi = result.kpi || {};
    kpiValue.textContent = kpi.value === null || kpi.value === undefined
      ? '— (unknown)'
      : number(kpi.value) + '%';
    kpiNote.textContent = run.process_name + ' · ' + (run.period || 'Unknown period');
    evidence.textContent = 'Not verified';
    nextStage.textContent = stages[result.next_stage] || 'Needs evidence review';
  }

  function emptyRows() {
    rows.replaceChildren();
    previous.disabled = true;
    next.disabled = true;
    pageLabel.textContent = 'Page ' + page;
  }

  function td(text, className) {
    const cell = document.createElement('td');
    cell.textContent = text;
    if (className) cell.className = className;
    return cell;
  }

  function renderHistory(data) {
    emptyRows();
    const records = Array.isArray(data.results) ? data.results : [];
    if (records.length === 0) {
      historyStatus.textContent = data.count
        ? 'There are no records on this page.'
        : 'No analyses recorded for this project.';
      setSummary(null);
      return;
    }
    for (const run of records) {
      const tr = document.createElement('tr');
      const date = run.created_at ? new Date(run.created_at) : null;
      const dateText = date && !Number.isNaN(date.getTime())
        ? date.toLocaleDateString('en-GB') : 'Unknown date';
      tr.appendChild(td(dateText));
      const identity = td(run.case_id || '—', 'po-strong');
      const process = document.createElement('small');
      process.className = 'po-secondary';
      process.textContent = run.process_name || '';
      identity.appendChild(process);
      tr.appendChild(identity);
      const kpi = run.result && run.result.kpi;
      tr.appendChild(td(kpi && kpi.value !== null && kpi.value !== undefined
        ? number(kpi.value) + '% (reported)' : '— (unknown)'));
      tr.appendChild(td(stages[run.result && run.result.next_stage] || 'Evidence review needed'));
      rows.appendChild(tr);
    }
    // Summary on page 1 is the newest saved observation, never a fake average.
    if (page === 1) setSummary(records[0]);
    historyStatus.textContent = data.count + ' saved analysis record(s) · not independently verified';
    previous.disabled = page <= 1;
    next.disabled = !data.has_more || page >= 200;
    pageLabel.textContent = 'Page ' + page;
  }

  async function parse(response) {
    let body = null;
    try { body = await response.json(); } catch (_error) { /* 403 may be HTML */ }
    if (!response.ok) {
      if (response.status === 403 || response.status === 404) {
        throw new Error('Your project access is unavailable or has changed. Reload this page.');
      }
      if (response.status === 429) {
        throw new Error('Upload limit reached. Try again after the rate limit resets.');
      }
      if (response.status === 400 && body && typeof body.detail === 'string') {
        throw new Error(body.detail.slice(0, 200));
      }
      throw new Error('The request could not be completed. Please try again.');
    }
    return body;
  }

  async function loadHistory() {
    if (controller) controller.abort();
    const current = select.value;
    const sequence = ++requestSequence;
    controller = new AbortController();
    const signal = controller.signal;
    emptyRows();
    historyStatus.textContent = 'Loading private history…';
    try {
      const response = await fetch(endpoint(current) + '?page=' + page, {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
        signal,
      });
      const data = await parse(response);
      if (signal.aborted || sequence !== requestSequence || current !== select.value) return;
      renderHistory(data);
    } catch (error) {
      if (signal.aborted || sequence !== requestSequence) return;
      rows.replaceChildren();
      setSummary(null);
      historyStatus.textContent = error.message || 'Unable to load history.';
      previous.disabled = true;
      next.disabled = true;
    }
  }

  function applyPermission() {
    const write = canUpload();
    fileInput.disabled = !write || busy;
    submit.disabled = !write || busy;
    select.disabled = busy;
    refresh.disabled = busy;
    permission.textContent = write
      ? 'You can read history and submit a CSV for analysis.'
      : 'Read-only access: your role does not permit CSV uploads.';
  }

  async function upload() {
    if (busy || !canUpload()) return;
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      setFeedback('Choose one CSV file first.', true);
      return;
    }
    if (!file.name.toLowerCase().endsWith('.csv') || file.size > limit || file.size === 0) {
      setFeedback('Choose a non-empty .csv file no larger than 512 KiB.', true);
      return;
    }
    if (!token || !token.value) {
      setFeedback('Security token missing. Reload and sign in again.', true);
      return;
    }

    busy = true;
    applyPermission();
    setFeedback('Validating reported observations…', false);
    const current = select.value;
    const body = new FormData();
    body.append('file', file, file.name);
    try {
      const response = await fetch(endpoint(current), {
        method: 'POST',
        body,
        credentials: 'same-origin',
        cache: 'no-store',
        headers: {
          Accept: 'application/json',
          'X-CSRFToken': token.value,
        },
      });
      const data = await parse(response);
      if (current !== select.value) return;
      setFeedback(data.created
        ? 'Analysis saved. Observations remain unverified.'
        : 'This file was previously analysed for this project.', false);
      fileInput.value = '';
      page = 1;
      await loadHistory();
    } catch (error) {
      setFeedback(error.message || 'Unable to analyse CSV.', true);
    } finally {
      busy = false;
      applyPermission();
    }
  }

  select.addEventListener('change', () => {
    page = 1;
    if (controller) controller.abort();
    ++requestSequence;
    rows.replaceChildren();
    setSummary(null);
    setFeedback('', false);
    fileInput.value = '';
    applyPermission();
    loadHistory();
  });
  submit.addEventListener('click', upload);
  refresh.addEventListener('click', loadHistory);
  previous.addEventListener('click', () => {
    if (page > 1) { page -= 1; loadHistory(); }
  });
  next.addEventListener('click', () => {
    if (page < 200 && !next.disabled) { page += 1; loadHistory(); }
  });

  applyPermission();
  loadHistory();
}());
