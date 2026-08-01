import {clearTransition, setTransition} from './plan_client.js';

const FIELDS = [
  {name: 'technique', label: 'Technique', kind: 'text'},
  {name: 'beats', label: 'Transition beats', kind: 'number'},
  {name: 'showcase_move', label: 'Showcase move', kind: 'text'},
  {name: 'effects', label: 'Effects (JSON array)', kind: 'textarea'},
  {name: 'note', label: 'Transition note', kind: 'textarea'},
];

function pair(segment) {
  return {
    from_track_id: segment.from_track_id || segment.from,
    to_track_id: segment.to_track_id || segment.to,
  };
}

function valueFor(segment, name) {
  if (name === 'beats') return segment.beats ?? segment.transition_beats ?? '';
  if (name === 'effects') return segment.effects == null ? '' : JSON.stringify(segment.effects, null, 2);
  return segment[name] ?? '';
}

export function createTransitionEditor(root) {
  if (!root) throw new Error('Transition editor root is required.');
  let current = null;
  let clickHandler = null;

  async function defaultSave(slug, patch) {
    return setTransition(slug, patch);
  }

  async function defaultRevert(slug, segment, field) {
    const ids = pair(segment);
    if (!field) return clearTransition(slug, ids.from_track_id, ids.to_track_id);
    const remaining = {};
    for (const name of segment.override_fields || []) {
      if (name === field) continue;
      const value = valueFor(segment, name);
      if (name === 'effects') remaining[name] = value ? JSON.parse(value) : [];
      else if (name === 'beats') remaining[name] = value === '' ? null : Number(value);
      else remaining[name] = value;
    }
    await clearTransition(slug, ids.from_track_id, ids.to_track_id);
    if (!Object.keys(remaining).length) return null;
    return setTransition(slug, {...ids, ...remaining, author: 'human'});
  }

  function close() {
    if (clickHandler) root.removeEventListener('click', clickHandler);
    clickHandler = null;
    current = null;
    root.hidden = true;
    root.innerHTML = '';
  }

  function open({segment, slug, onSave = defaultSave, onRevert = defaultRevert, onClose = close}) {
    close();
    current = {segment, slug, onSave, onRevert, onClose};
    const ids = pair(segment);
    const overridden = new Set(segment.override_fields || []);
    root.hidden = false;
    root.classList.toggle('is-orphaned', segment.state === 'orphaned');
    root.innerHTML = `
      <div class="transition-editor-head">
        <div>
          <h2>Edit transition</h2>
          <div class="transition-pair">${escapeHtml(ids.from_track_id)} → ${escapeHtml(ids.to_track_id)}</div>
        </div>
        <button type="button" data-editor-action="close" aria-label="Close transition editor">Close</button>
      </div>
      ${segment.state === 'orphaned' ? '<div class="orphaned-message">Orphaned override — this stored pair is not adjacent in the current order.</div>' : ''}
      <div class="transition-author">Current author: ${escapeHtml(segment.author || 'derived')}</div>
      <form id="transition-editor-form">
        ${FIELDS.map(field => fieldMarkup(field, valueFor(segment, field.name), overridden.has(field.name))).join('')}
        <div class="transition-editor-actions">
          <button type="submit" class="primary">Save changed fields</button>
          <button type="button" data-editor-action="clear" ${segment.overridden ? '' : 'disabled'}>Clear entire override</button>
        </div>
      </form>
      <div class="transition-editor-status" role="status" aria-live="polite"></div>`;

    const form = root.querySelector('#transition-editor-form');
    const status = root.querySelector('.transition-editor-status');
    const initial = Object.fromEntries(FIELDS.map(field => [field.name, String(valueFor(segment, field.name))]));

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const patch = {...ids};
      try {
        for (const field of FIELDS) {
          const control = form.elements.namedItem(field.name);
          if (control.value === initial[field.name]) continue;
          if (field.name === 'effects') patch.effects = control.value.trim() ? JSON.parse(control.value) : [];
          else if (field.name === 'beats') patch.beats = control.value === '' ? null : Number(control.value);
          else patch[field.name] = control.value;
        }
        if (Object.keys(patch).length === 2) {
          status.textContent = 'No fields changed.';
          return;
        }
        patch.author = 'human';
        setDisabled(root, true);
        await onSave(slug, patch);
        status.textContent = 'Transition override saved.';
        document.dispatchEvent(new CustomEvent('clawdj:transition-changed', {detail: {slug, pair: ids}}));
      } catch (error) {
        status.textContent = error instanceof SyntaxError ? 'Effects must be a valid JSON array.' : error.message;
      } finally {
        setDisabled(root, false);
      }
    });

    clickHandler = async function handleClick(event) {
      const button = event.target.closest('button[data-editor-action]');
      if (!button || !current) return;
      if (button.dataset.editorAction === 'close') {
        onClose();
        return;
      }
      const field = button.dataset.field;
      if (button.dataset.editorAction === 'clear' && !window.confirm('Clear this entire transition override and return to derived values?')) return;
      try {
        setDisabled(root, true);
        await onRevert(slug, segment, field);
        status.textContent = field ? `${field.replace('_', ' ')} reverted to derived.` : 'Transition override cleared.';
        document.dispatchEvent(new CustomEvent('clawdj:transition-changed', {detail: {slug, pair: ids}}));
      } catch (error) {
        status.textContent = error.message;
      } finally {
        setDisabled(root, false);
      }
    };
    root.addEventListener('click', clickHandler);
  }

  return {open, close};
}

function fieldMarkup(field, value, overridden) {
  const control = field.kind === 'textarea'
    ? `<textarea name="${field.name}" rows="${field.name === 'effects' ? 4 : 3}">${escapeHtml(value)}</textarea>`
    : `<input name="${field.name}" type="${field.kind}" ${field.kind === 'number' ? 'min="0" step="1"' : ''} value="${escapeHtml(value)}">`;
  return `<div class="transition-field ${overridden ? 'is-overridden' : ''}">
    <label>${escapeHtml(field.label)}${overridden ? ' <span class="override-mark">overridden</span>' : ''}${control}</label>
    ${overridden ? `<button type="button" data-editor-action="revert" data-field="${field.name}">Revert to derived</button>` : ''}
  </div>`;
}

function setDisabled(root, disabled) {
  root.querySelectorAll('button, input, textarea').forEach(control => { control.disabled = disabled; });
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
}
