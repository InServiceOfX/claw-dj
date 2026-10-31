// Stems page: every vocals-only and instrumental-only track in the library.
// Scroll or search each list, preview any row in the browser (not Mixxx),
// pick one vocal and one instrumental, then plan or play the layer live in
// Mixxx. Nothing is rendered: the server runs hands.stem_layer.

const el = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = { data: null, vocal: null, bed: null, beds: null, polling: null, loaded: false };

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.error || response.statusText);
  return data;
}

function length(seconds) {
  if (!seconds) return '—';
  const s = Math.round(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function row(track, kind) {
  const picked = (kind === 'vocals_only' ? state.vocal : state.bed)?.track_id === track.track_id;
  const label = `${track.artist} — ${track.title}`;
  const flags = [
    track.kind_source === 'override' ? '<span class="stem-flag">hand</span>' : '',
    track.clean ? '<span class="stem-flag">clean</span>' : '',
    track.score !== undefined ? `<span class="stem-flag" title="${esc(track.reason)}">fit ${track.score.toFixed(1)}</span>` : '',
  ].join('');
  return `<div class="stem-row${picked ? ' is-picked' : ''}" data-stem-id="${esc(track.track_id)}" data-stem-kind="${kind}">
    <button type="button" class="preview-btn" data-preview-id="${esc(track.track_id)}" data-preview-label="${esc(label)}" title="Preview in this tab (not Mixxx)" aria-label="Preview ${esc(label)}">▶</button>
    <label class="stem-pick"><input type="radio" name="stem-${kind}" value="${esc(track.track_id)}" ${picked ? 'checked' : ''} aria-label="Use ${esc(label)}">
      <span><span class="title" title="${esc(track.title)}">${esc(track.title)}</span>${flags ? `<span class="stem-flags">${flags}</span>` : ''}<span class="artist">${esc(track.artist)}${track.album ? ' · ' + esc(track.album) : ''}</span></span></label>
    <span class="bpm ${track.bpm ? '' : 'missing'}" title="${track.bpm_source ? 'from ' + track.bpm_source : 'Mixxx analyzes on load'}">${track.bpm ? track.bpm.toFixed(1) : '—'}</span>
    <span class="key ${track.key ? '' : 'missing'}">${esc(track.key || '—')}</span>
    <span class="len">${length(track.duration_seconds)}</span>
    <select class="stem-kind" data-kind-for="${esc(track.track_id)}" aria-label="Track type for ${esc(label)}" title="Detected from the ${esc(track.kind_source)}${track.kind_evidence ? ': ' + esc(track.kind_evidence) : ''}">
      <option value="" selected>type…</option>
      <option value="vocals_only">vocals only</option>
      <option value="instrumental_only">instrumental</option>
      <option value="full_mix">full mix</option>
      <option value="auto">auto (from name)</option>
    </select>
  </div>`;
}

function render() {
  if (!state.data) return;
  const vocals = state.data.vocals_only;
  const beds = state.beds || state.data.instrumental_only;
  el('stem-vocal-count').textContent = vocals.length.toLocaleString();
  el('stem-bed-count').textContent = state.beds ? `${beds.length} best fits` : beds.length.toLocaleString();
  el('stem-vocals').innerHTML = vocals.length ? vocals.map(t => row(t, 'vocals_only')).join('') : '<div class="empty">No vocals-only tracks match.</div>';
  el('stem-beds').innerHTML = beds.length ? beds.map(t => row(t, 'instrumental_only')).join('') : '<div class="empty">No instrumentals match.</div>';
  el('stem-beds-all').hidden = !state.beds;
  renderPick();
}

function renderPick() {
  const v = state.vocal, b = state.bed;
  el('stem-picked-vocal').textContent = v ? `${v.artist} — ${v.title}` : 'choose a vocal';
  el('stem-picked-bed').textContent = b ? `${b.artist} — ${b.title}` : 'choose an instrumental';
  const ready = Boolean(v && b);
  el('stem-plan').disabled = !ready;
  el('stem-play').disabled = !ready;
  el('stem-suggest').disabled = !v;
}

async function load(refresh = false) {
  const q = el('stem-search').value.trim();
  el('stem-status').textContent = 'Reading the library…';
  try {
    state.data = await api(`/api/stems?q=${encodeURIComponent(q)}${refresh ? '&refresh=1' : ''}`);
    state.beds = null;
    el('stem-status').textContent = `${state.data.counts.vocals_only.toLocaleString()} vocals only · ${state.data.counts.instrumental_only.toLocaleString()} instrumentals`;
    render();
  } catch (error) {
    el('stem-status').textContent = `Could not read the library: ${error.message}`;
  }
}

function find(id) {
  const all = [...(state.data?.vocals_only || []), ...(state.data?.instrumental_only || []), ...(state.beds || [])];
  return all.find(t => t.track_id === id) || null;
}

function options(dryRun) {
  const from = el('stem-vocal-from').value.trim();
  return {
    vocal_id: state.vocal.track_id,
    bed_id: state.bed.track_id,
    vocal_from_seconds: from === '' ? null : Number(from),
    count_shift_beats: Number(el('stem-count-shift').value),
    lead_bars: Number(el('stem-lead-bars').value),
    dry_run: dryRun,
  };
}

function showLayer(status) {
  const lines = status.log || [];
  el('stem-console').textContent = lines.join('\n');
  el('stem-console').hidden = !lines.length;
  el('stem-console').scrollTop = el('stem-console').scrollHeight;
  const phase = status.phase || 'idle';
  const what = status.dry_run ? 'Plan' : 'Mixxx';
  el('stem-layer-status').textContent = status.error ? `${what}: ${phase} — ${status.error}` : `${what}: ${phase}`;
  el('stem-stop').hidden = !status.playing || status.dry_run;
  if (!status.playing && state.polling) { clearInterval(state.polling); state.polling = null; }
}

async function startLayer(dryRun) {
  if (!state.vocal || !state.bed) return;
  if (!dryRun) {
    const ok = el('stem-confirm');
    if (!ok.checked) { el('stem-layer-status').textContent = 'Tick "Play in Mixxx now" first — this starts decks 1 and 2.'; return; }
  }
  try {
    showLayer(await api('/api/stems/layer', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(options(dryRun))}));
    if (!state.polling) state.polling = setInterval(async () => showLayer(await api('/api/stems/layer')), 1000);
  } catch (error) {
    el('stem-layer-status').textContent = error.message;
  }
}

function wire() {
  let timer;
  el('stem-search').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => load(), 200); });
  el('stem-refresh').addEventListener('click', () => load(true));
  el('page-stems').addEventListener('change', async event => {
    const radio = event.target.closest('input[type=radio]');
    if (radio) {
      const track = find(radio.value);
      if (radio.name === 'stem-vocals_only') { state.vocal = track; el('stem-vocal-from').value = ''; }
      else state.bed = track;
      document.querySelectorAll(`.stem-row[data-stem-kind="${radio.name.slice(5)}"]`).forEach(r => r.classList.toggle('is-picked', r.dataset.stemId === radio.value));
      renderPick();
      return;
    }
    const select = event.target.closest('select.stem-kind');
    if (select && select.value) {
      try {
        const result = await api('/api/stems/kind', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({track_id: select.dataset.kindFor, kind: select.value})});
        el('stem-status').textContent = `Marked as ${result.kind.replace('_', ' ')} (${result.source}).`;
        await load(true);
      } catch (error) {
        el('stem-status').textContent = error.message;
      }
    }
  });
  el('stem-suggest').addEventListener('click', async () => {
    try {
      const result = await api(`/api/stems/beds?vocal_id=${encodeURIComponent(state.vocal.track_id)}`);
      state.beds = result.beds;
      render();
    } catch (error) { el('stem-status').textContent = error.message; }
  });
  el('stem-beds-all').addEventListener('click', () => { state.beds = null; render(); });
  el('stem-use-position').addEventListener('click', () => {
    const audio = el('preview-audio');
    if (!state.vocal || audio.dataset.trackId !== state.vocal.track_id) {
      el('stem-layer-status').textContent = 'Preview the chosen vocal, pause where the verse starts, then use its position.';
      return;
    }
    el('stem-vocal-from').value = audio.currentTime.toFixed(1);
  });
  el('stem-plan').addEventListener('click', () => startLayer(true));
  el('stem-play').addEventListener('click', () => startLayer(false));
  el('stem-stop').addEventListener('click', async () => showLayer(await api('/api/stems/layer/stop', {method: 'POST'})));
}

export function showStems() {
  if (!state.loaded) { state.loaded = true; wire(); load(); }
  api('/api/stems/layer').then(showLayer).catch(() => {});
}

window.clawdjShowStems = showStems;
