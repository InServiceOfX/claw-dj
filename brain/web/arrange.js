import * as client from './plan_client.js';
import {mountPlanPicker} from './plan_picker.js';
import {createTransitionEditor} from './transition_editor.js';

const root = document.getElementById('arrange-root');
const pickerRoot = document.getElementById('plan-picker');

if (root && pickerRoot) initialize();

function initialize() {
  const state = {
    slug: null,
    snapshot: null,
    loading: false,
    selected: new Set(),
    draggedKey: null,
    keyboardKey: null,
    keyboardTarget: null,
  };
  const editor = createTransitionEditor(document.getElementById('transition-editor'));
  const picker = mountPlanPicker(pickerRoot);
  const conflictBanner = document.getElementById('plan-conflict-banner');
  const conflictText = document.getElementById('plan-conflict-text');

  function announce(message) {
    document.getElementById('arrange-live').textContent = message;
  }

  function discardLocalBuffer() {
    state.selected.clear();
    state.draggedKey = null;
    state.keyboardKey = null;
    state.keyboardTarget = null;
    editor.close();
  }

  document.addEventListener('clawdj:plan-conflict', event => {
    discardLocalBuffer();
    const changed = event.detail?.payload?.changed_files || [];
    conflictText.textContent = `This plan changed on disk${changed.length ? ` (${changed.join(', ')})` : ''}. Refresh to review the changed-on-disk plan before trying that edit again.`;
    conflictBanner.hidden = false;
  });

  document.getElementById('plan-conflict-refresh').addEventListener('click', () => refresh());

  document.addEventListener('clawdj:plan-switched', async event => {
    const plan = event.detail?.plan;
    discardLocalBuffer();
    state.slug = plan?.slug || null;
    state.snapshot = null;
    try {
      if (window.clawDjLegacy?.refreshForPlan) await window.clawDjLegacy.refreshForPlan();
    } catch (error) {
      announce(`Plan switched, but an existing view did not refresh: ${error.message}`);
    }
    if (state.slug) await refresh();
    else render();
  });

  document.addEventListener('clawdj:transition-changed', event => {
    if (event.detail?.slug === state.slug) refresh();
  });

  async function refresh() {
    if (!state.slug || state.loading) return;
    state.loading = true;
    conflictBanner.hidden = true;
    editor.close();
    renderLoading();
    try {
      // This is deliberately the only request in Refresh: one Arrange
      // snapshot replaces the complete painted plan state.
      const snapshot = await client.refreshPlan(state.slug, {});
      state.snapshot = snapshot;
      discardLocalBuffer();
      picker.setSnapshotState(state.slug, snapshot.stale);
      render();
      announce(`Refreshed ${snapshot.tracks.length} tracks from disk.`);
    } catch (error) {
      if (error.name !== 'AbortError') renderError(error.message);
    } finally {
      state.loading = false;
      const button = document.getElementById('arrange-refresh');
      if (button) button.disabled = false;
    }
  }

  function renderLoading() {
    root.innerHTML = `<div class="arrange-toolbar"><button id="arrange-refresh" type="button" disabled aria-busy="true">Refreshing…</button></div>
      <div class="arrange-pending" role="status">Reading one complete Arrange snapshot from disk…</div>`;
  }

  function renderError(message) {
    root.innerHTML = `<div class="arrange-toolbar"><button id="arrange-refresh" type="button">Refresh</button></div>
      <div class="banner">${escapeHtml(message)}</div>`;
    document.getElementById('arrange-refresh').addEventListener('click', refresh);
  }

  function render() {
    if (!state.snapshot) {
      root.innerHTML = `<div class="empty">${state.slug ? 'Press Refresh to read this plan.' : 'Create or switch to a plan above.'}</div>`;
      return;
    }
    const snapshot = state.snapshot;
    const units = buildUnits(snapshot);
    const artifact = snapshot.artifact;
    const changed = snapshot.staleness?.changed_inputs || [];
    root.innerHTML = `
      <div class="arrange-toolbar">
        <button id="arrange-refresh" type="button">Refresh</button>
        <form id="arrange-add-form" class="arrange-add-form">
          <label for="arrange-add-id">Track ID</label>
          <input id="arrange-add-id" name="track_id" required placeholder="Paste a library track ID">
          <button type="submit">Add track</button>
        </form>
        <button id="arrange-add-curate" type="button">Add from Curate selection</button>
        <button id="arrange-bunch" type="button" ${state.selected.size < 2 ? 'disabled' : ''}>Bunch these (${state.selected.size})</button>
        ${renderAddToBunch(snapshot)}
      </div>
      <div class="arrange-state ${snapshot.stale ? 'is-stale' : ''}">
        <span><strong>${snapshot.stale ? 'Stale' : 'Current'}</strong>${changed.length ? ` · changed: ${escapeHtml(changed.join(', '))}` : ''}</span>
        <span>Artifact: ${artifact ? `v${escapeHtml(artifact.version)}${artifact.profile ? ` · ${escapeHtml(artifact.profile)}` : ''}` : 'not built'}</span>
        <span title="${escapeHtml(snapshot.rev)}">Revision ${escapeHtml(snapshot.rev.slice(0, 12))}</span>
        <span>${Object.keys(snapshot.revs || {}).length} source revisions</span>
      </div>
      <div class="arrange-list" role="list" aria-label="Ordered tracks and transitions">
        ${renderUnits(units, snapshot)}
      </div>
      ${renderOrphaned(snapshot)}
      <details id="arrange-journal"><summary>What changed</summary><div class="journal-log" role="log" aria-live="polite">Open to load recent changes.</div></details>`;
    wireRendered(units);
  }

  function wireRendered(units) {
    document.getElementById('arrange-refresh').addEventListener('click', refresh);
    document.getElementById('arrange-add-form').addEventListener('submit', async event => {
      event.preventDefault();
      const input = event.currentTarget.elements.track_id;
      const trackId = input.value.trim();
      if (!trackId) return;
      await mutate(() => client.addTracks(state.slug, {add: [trackId]}), `Added ${trackId}.`);
    });
    document.getElementById('arrange-add-curate').addEventListener('click', async () => {
      const disk = new Set(state.snapshot.tracks.map(track => track.track_id));
      const trackIds = [...document.querySelectorAll('#selected input[data-id]:checked')]
        .map(input => input.dataset.id).filter(trackId => !disk.has(trackId));
      if (!trackIds.length) {
        announce('The current Curate selection is already represented. Press Refresh if another agent changed it.');
        return;
      }
      await mutate(() => client.addTracks(state.slug, {add: trackIds}), `Added ${trackIds.length} Curate track(s).`);
    });
    document.getElementById('arrange-bunch').addEventListener('click', createBunch);
    document.getElementById('arrange-bunch-add')?.addEventListener('click', addSelectedToBunch);
    root.querySelectorAll('[data-unbunch-track]').forEach(button => button.addEventListener('click', () =>
      removeTrackFromBunch(button.dataset.unbunchFrom, button.dataset.unbunchTrack)));
    root.querySelectorAll('input[data-select-track]').forEach(box => box.addEventListener('change', () => {
      if (box.checked) state.selected.add(box.dataset.selectTrack);
      else state.selected.delete(box.dataset.selectTrack);
      const button = document.getElementById('arrange-bunch');
      button.disabled = state.selected.size < 2;
      button.textContent = `Bunch these (${state.selected.size})`;
      const add = document.getElementById('arrange-bunch-add');
      if (add) {
        add.disabled = state.selected.size < 1;
        add.textContent = `Add to bunch (${state.selected.size})`;
      }
    }));
    root.querySelectorAll('[data-remove-track]').forEach(button => button.addEventListener('click', () =>
      mutate(() => client.addTracks(state.slug, {remove: [button.dataset.removeTrack]}), `Removed ${button.dataset.removeTrack}.`)));
    root.querySelectorAll('[data-unbunch]').forEach(button => button.addEventListener('click', () =>
      mutate(() => client.deactivateBunch(state.slug, button.dataset.unbunch), 'Bunch deactivated; the reusable library bunch remains saved.')));
    root.querySelectorAll('[data-archive-bunch]').forEach(button => button.addEventListener('click', () => archiveBunch(button.dataset.archiveBunch)));
    root.querySelectorAll('[data-move]').forEach(button => button.addEventListener('click', () => {
      const index = units.findIndex(unit => unit.key === button.dataset.unitKey);
      const target = button.dataset.move === 'up' ? index - 1 : index + 1;
      moveUnit(units, index, target);
    }));
    root.querySelectorAll('[data-transition-index]').forEach(button => button.addEventListener('click', () => openEditor(Number(button.dataset.transitionIndex))));
    root.querySelectorAll('[data-orphan-index]').forEach(button => button.addEventListener('click', () => {
      const orphaned = (state.snapshot.segments || []).filter(segment => segment.state === 'orphaned');
      const segment = orphaned[Number(button.dataset.orphanIndex)];
      if (segment) editor.open({segment, slug: state.slug});
    }));
    wireDragAndKeyboard(units);
    const details = document.getElementById('arrange-journal');
    details.addEventListener('toggle', () => { if (details.open) loadJournal(details); }, {once: true});
  }

  async function mutate(operation, success) {
    try {
      await operation();
      announce(success);
      await refresh();
    } catch (error) {
      if (!(error instanceof client.PlanConflictError)) announce(error.message);
    }
  }

  function bunchById(bunchId) {
    return (state.snapshot?.bunches || []).find(item => item.bunch_id === bunchId) || null;
  }

  async function writeBunchTracks(bunchId, trackIds, message) {
    try {
      await client.setBunchTracks(bunchId, trackIds);
    } catch (error) {
      announce(error.message || 'The bunch could not be updated.');
      return;
    }
    announce(message);
    await refresh();
  }

  async function addSelectedToBunch() {
    const bunchId = document.getElementById('arrange-bunch-target')?.value;
    const bunch = bunchById(bunchId);
    if (!bunch || !state.selected.size) return;
    const members = new Set(bunch.track_ids || []);
    // Append in the plan's own running order so the bunch's exact order
    // stays something the arrangement can actually satisfy.
    const added = state.snapshot.tracks
      .map(track => track.track_id)
      .filter(id => state.selected.has(id) && !members.has(id));
    if (!added.length) {
      announce(`Every selected song is already in “${bunch.label}”.`);
      return;
    }
    await writeBunchTracks(
      bunchId,
      [...(bunch.track_ids || []), ...added],
      `Added ${added.length} song(s) to “${bunch.label}”.`,
    );
  }

  async function removeTrackFromBunch(bunchId, trackId) {
    const bunch = bunchById(bunchId);
    if (!bunch) return;
    const remaining = (bunch.track_ids || []).filter(id => id !== trackId);
    if (remaining.length === (bunch.track_ids || []).length) return;
    // A bunch of one has no ordering left to enforce; say so rather than
    // leaving a meaningless single-song "exact order" unit on the page.
    if (remaining.length < 2) {
      announce(`“${bunch.label}” would have fewer than two songs left — un-bunch it instead.`);
      return;
    }
    await writeBunchTracks(bunchId, remaining, `Removed 1 song from “${bunch.label}”.`);
  }

  async function createBunch() {
    const ordered = state.snapshot.tracks.map(track => track.track_id).filter(id => state.selected.has(id));
    if (ordered.length < 2) return;
    const label = window.prompt('Name this reusable bunch:', ordered.join(' + '));
    if (!label?.trim()) return;
    const result = await client.createAndActivateBunch(state.slug, {label: label.trim(), track_ids: ordered, ordered: true});
    if (result.stage === 'activated') {
      announce(`Saved and activated “${result.created.label}”.`);
      await refresh();
    } else if (result.stage === 'activation-conflicted') {
      const conflict = result.conflict;
      const known = state.snapshot.bunches.find(item => item.bunch_id === conflict.conflicting_bunch_id);
      const conflictingName = known ? `“${known.label}” (${conflict.conflicting_bunch_id})` : conflict.conflicting_bunch_id;
      announce(`Library bunch “${result.created.label}” was still saved. Activation conflicts with ${conflictingName}; shared songs: ${(conflict.shared_track_ids || []).join(', ')}.`);
    } else {
      announce(result.error?.message || 'The bunch could not be created and activated.');
    }
  }

  async function archiveBunch(bunchId) {
    if (!window.confirm('Archive this reusable library bunch? Active plans will retain a warning.')) return;
    try {
      const result = await client.archiveBunch(bunchId);
      announce(`Archived bunch. Affected plans: ${(result.affected_slugs || []).join(', ') || 'none'}.`);
      await refresh();
    } catch (error) {
      announce(error.message);
    }
  }

  async function moveUnit(units, from, to) {
    if (from < 0 || to < 0 || to >= units.length || from === to) return;
    const desired = [...units];
    const [unit] = desired.splice(from, 1);
    desired.splice(to, 0, unit);
    state.keyboardKey = null;
    state.keyboardTarget = null;
    if (unit.bunch) {
      const toIndex = desired.slice(0, to).reduce((total, item) => total + item.tracks.length, 0);
      await mutate(() => client.moveBunch(state.slug, unit.bunch.bunch_id, toIndex), `Moved ${unit.label} to position ${to + 1}.`);
    } else {
      const order = desired.flatMap(item => item.tracks.map(track => track.track_id));
      await mutate(() => client.setOrder(state.slug, order), `Moved ${unit.label} to position ${to + 1}.`);
    }
  }

  function wireDragAndKeyboard(units) {
    root.querySelectorAll('[data-unit-key]').forEach(element => {
      element.addEventListener('dragstart', () => { state.draggedKey = element.dataset.unitKey; });
      element.addEventListener('dragend', () => { state.draggedKey = null; });
      element.addEventListener('dragover', event => event.preventDefault());
      element.addEventListener('drop', event => {
        event.preventDefault();
        const from = units.findIndex(unit => unit.key === state.draggedKey);
        const to = units.findIndex(unit => unit.key === element.dataset.unitKey);
        moveUnit(units, from, to);
      });
      element.addEventListener('keydown', event => {
        const index = units.findIndex(unit => unit.key === element.dataset.unitKey);
        if (event.key === ' ' || event.key === 'Enter') {
          event.preventDefault();
          if (state.keyboardKey === element.dataset.unitKey) {
            const target = state.keyboardTarget;
            state.keyboardKey = null;
            state.keyboardTarget = null;
            moveUnit(units, index, target);
          } else {
            state.keyboardKey = element.dataset.unitKey;
            state.keyboardTarget = index;
            announce(`Picked up ${units[index].label}. Use arrow keys to choose a position, then Space to drop.`);
          }
        } else if (state.keyboardKey === element.dataset.unitKey && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
          event.preventDefault();
          const delta = event.key === 'ArrowUp' ? -1 : 1;
          state.keyboardTarget = Math.max(0, Math.min(units.length - 1, state.keyboardTarget + delta));
          announce(`${units[index].label} will move to position ${state.keyboardTarget + 1}. Press Space to drop.`);
        } else if (event.key === 'Escape' && state.keyboardKey) {
          state.keyboardKey = null;
          state.keyboardTarget = null;
          announce('Reorder cancelled.');
        }
      });
    });
  }

  function openEditor(index) {
    const tracks = state.snapshot.tracks;
    const from = tracks[index]?.track_id;
    const to = tracks[index + 1]?.track_id;
    const segment = findSegment(state.snapshot.segments, from, to) || {
      from_track_id: from, to_track_id: to, state: 'derived', overridden: false,
      override_fields: [], author: null,
    };
    editor.open({segment, slug: state.slug});
    document.getElementById('transition-editor').scrollIntoView({behavior: 'smooth', block: 'nearest'});
  }

  async function loadJournal(details) {
    const log = details.querySelector('.journal-log');
    log.textContent = 'Loading recent changes…';
    try {
      const entries = await client.fetchJournal(state.slug, 50);
      log.innerHTML = entries.length ? entries.map(entry => `
        <div class="journal-entry"><strong>${escapeHtml(entry.action)}</strong>
        <span>${escapeHtml(entry.actor)} · author: ${escapeHtml(entry.author || 'none')}</span>
        <time>${escapeHtml(new Date(Number(entry.at) * 1000).toLocaleString())}</time></div>`).join('') : '<div class="empty">No recorded changes.</div>';
    } catch (error) {
      log.textContent = error.message;
    }
  }

  picker.refresh().then(active => {
    state.slug = active?.slug || null;
    if (state.slug) refresh();
    else render();
  }).catch(error => renderError(error.message));
}

function buildUnits(snapshot) {
  const starts = new Map();
  for (const bunch of snapshot.bunches || []) {
    if (bunch.enabled === false || bunch.span == null) continue;
    starts.set(Number(bunch.span.start), bunch);
  }
  const units = [];
  for (let index = 0; index < snapshot.tracks.length;) {
    const bunch = starts.get(index);
    if (bunch) {
      const members = new Set(bunch.track_ids || []);
      const span = snapshot.tracks.slice(index, Number(bunch.span.end) + 1);
      const tracks = span.filter(track => members.has(track.track_id));
      units.push({key: `bunch:${bunch.bunch_id}`, label: bunch.label, bunch, tracks});
      // A bunch is meant to be contiguous, but nothing guarantees the current
      // order agrees -- an unbunched track can sit between the bunch's first
      // and last member. Those used to be filtered out of the unit AND
      // skipped by the cursor below, so they vanished from Arrange entirely
      // and every drag then computed an order missing them, which the server
      // correctly rejected as not_a_permutation (reported 2026-08-03:
      // "when I bunch songs it makes the songs I didn't bunch go away", and
      // drags silently doing nothing). Surface them as their own units
      // immediately after the bunch so they stay visible and draggable.
      for (const track of span) {
        if (members.has(track.track_id)) continue;
        units.push({
          key: `track:${track.track_id}`,
          label: track.title || track.track_id,
          bunch: null,
          tracks: [track],
        });
      }
      index = Number(bunch.span.end) + 1;
    } else {
      const track = snapshot.tracks[index];
      units.push({key: `track:${track.track_id}`, label: track.title || track.track_id, bunch: null, tracks: [track]});
      index += 1;
    }
  }
  return units;
}

function renderUnits(units, snapshot) {
  let trackIndex = 0;
  const notes = new Map((snapshot.notes || []).map(note => [note.track_id, note]));
  return units.map((unit, unitIndex) => {
    const startIndex = trackIndex;
    const cards = unit.tracks.map(track => renderTrack(track, trackIndex++, notes.get(track.track_id), unit.bunch)).join('');
    const transition = trackIndex < snapshot.tracks.length ? renderTransition(snapshot, trackIndex - 1) : '';
    return `<div class="arrange-unit ${unit.bunch ? 'is-bunch' : ''}" role="listitem" tabindex="0" draggable="true" data-unit-key="${escapeHtml(unit.key)}" aria-label="${escapeHtml(unit.label)}, position ${unitIndex + 1} of ${units.length}">
      <div class="unit-head">
        <span>${unit.bunch ? `Bunch · ${escapeHtml(unit.bunch.label)} · songs ${Number(unit.bunch.span.start) + 1}–${Number(unit.bunch.span.end) + 1} · exact order` : `Track ${startIndex + 1}`}</span>
        <span class="unit-actions">
          <button type="button" data-move="up" data-unit-key="${escapeHtml(unit.key)}" ${unitIndex === 0 ? 'disabled' : ''}>Move up</button>
          <button type="button" data-move="down" data-unit-key="${escapeHtml(unit.key)}" ${unitIndex === units.length - 1 ? 'disabled' : ''}>Move down</button>
          ${unit.bunch ? `<button type="button" data-unbunch="${escapeHtml(unit.bunch.bunch_id)}">Un-bunch</button><button type="button" data-archive-bunch="${escapeHtml(unit.bunch.bunch_id)}">Archive bunch…</button>` : ''}
        </span>
      </div>${cards}</div>${transition}`;
  }).join('');
}

function renderAddToBunch(snapshot) {
  // Adding and removing deliberately use DIFFERENT gestures. Driving both
  // from one checkbox set would require every existing member to render
  // pre-selected, so "deselect to remove" and "select to add" would fight
  // over the same state (Ernest raised exactly this, 2026-08-03). Instead:
  // selection always means "tracks I am acting on" and never comes
  // pre-checked, adding is selection + this picker, and removing is the
  // per-row "Leave bunch" button inside the bunch itself.
  const bunches = (snapshot.bunches || []).filter(bunch => bunch.enabled !== false);
  if (!bunches.length) return '';
  const options = bunches
    .map(bunch => `<option value="${escapeHtml(bunch.bunch_id)}">${escapeHtml(bunch.label)}</option>`)
    .join('');
  return `<span class="arrange-add-bunch">
    <select id="arrange-bunch-target" aria-label="Bunch to add the selected tracks to">${options}</select>
    <button id="arrange-bunch-add" type="button" ${state.selected.size < 1 ? 'disabled' : ''}>Add to bunch (${state.selected.size})</button>
  </span>`;
}

function renderTrack(track, index, note, bunch) {
  const available = note?.available ?? track.available ?? true;
  return `<article class="arrange-track ${available ? '' : 'is-unavailable'}">
    <label class="arrange-select"><input type="checkbox" data-select-track="${escapeHtml(track.track_id)}"> Select track ${index + 1}</label>
    <div class="arrange-position">${index + 1}</div>
    <div><div class="title">${escapeHtml(track.title || track.track_id)}</div><div class="artist">${escapeHtml(track.artist || '')}</div></div>
    <div class="track-facts"><span>${track.bpm ? `${Number(track.bpm).toFixed(1)} BPM` : 'BPM —'}</span><span>${escapeHtml(track.key || 'Key —')}</span><span>${available ? 'Available' : 'Unavailable'}</span></div>
    <div class="effective-note"><strong>${escapeHtml(note?.layer || 'global')} note${note?.diverged ? ' · diverged' : ''}</strong><span>${escapeHtml(note?.note || 'No DJ note')}</span></div>
    <button type="button" data-remove-track="${escapeHtml(track.track_id)}" aria-label="Remove ${escapeHtml(track.title || track.track_id)} from plan">Remove</button>
    ${bunch ? `<button type="button" class="unbunch-one" data-unbunch-track="${escapeHtml(track.track_id)}" data-unbunch-from="${escapeHtml(bunch.bunch_id)}" aria-label="Remove ${escapeHtml(track.title || track.track_id)} from bunch ${escapeHtml(bunch.label)}">Leave bunch</button>` : ''}
  </article>`;
}

function renderTransition(snapshot, index) {
  const from = snapshot.tracks[index]?.track_id;
  const to = snapshot.tracks[index + 1]?.track_id;
  const segment = findSegment(snapshot.segments, from, to);
  const beats = segment?.transition_beats ?? segment?.beats;
  return `<button type="button" class="transition-card ${segment?.overridden ? 'is-overridden' : ''}" data-transition-index="${index}">
    <span class="transition-arrow">↓</span>
    <span><strong>${escapeHtml(segment?.technique || 'Transition not built')}</strong>
    <small>${beats != null ? `${escapeHtml(beats)} beats · ` : ''}author: ${escapeHtml(segment?.author || 'derived')}</small></span>
    <span>${escapeHtml(segment?.showcase_move || '')}</span>
    <span>${escapeHtml(segment?.note || 'Edit transition')}</span>
  </button>`;
}

function renderOrphaned(snapshot) {
  const orphaned = (snapshot.segments || []).filter(segment => segment.state === 'orphaned');
  if (!orphaned.length) return '';
  return `<section class="orphaned-transitions"><h2>Orphaned transition overrides</h2>${orphaned.map((segment, index) => `
    <button type="button" class="transition-card is-orphaned" data-orphan-index="${index}">
      ${escapeHtml(segment.from_track_id || segment.from)} → ${escapeHtml(segment.to_track_id || segment.to)} · ${escapeHtml(segment.note || segment.technique || 'stored override')}
    </button>`).join('')}</section>`;
}

function findSegment(segments, from, to) {
  return (segments || []).find(segment =>
    (segment.from_track_id || segment.from) === from && (segment.to_track_id || segment.to) === to);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
}
