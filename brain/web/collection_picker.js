const root = document.getElementById('collection-picker');

if (root) mountCollectionPicker(root);

export function mountCollectionPicker(container) {
  const state = {
    data: null,
    showingNew: false,
    working: false,
    statusOverride: null,
    form: {
      mount: '',
      roots: '',
      name: '',
      scan: true,
    },
  };

  async function request(options = {}) {
    const response = await fetch('/api/collections', options);
    let payload = null;
    const text = await response.text();
    try {
      payload = text ? JSON.parse(text) : {};
    } catch {
      throw new Error(
        response.ok
          ? 'Server returned non-JSON for /api/collections'
          : `Collections API failed (${response.status}). Restart scripts/start.sh if this build is older than the collection picker.`
      );
    }
    if (!response.ok) throw new Error(payload.message || payload.error || response.statusText);
    return payload;
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[character]);
  }

  function status(message) {
    state.statusOverride = message;
    const target = document.getElementById('collection-picker-status');
    if (target) target.textContent = message;
  }

  function defaultStatusText() {
    const active = activeCollection();
    return active
      ? `${active.display_name} · ${active.mount_base}`
      : 'Legacy local library (no collection registry yet)';
  }

  function readFormIntoState() {
    const mount = document.getElementById('collection-mount');
    const roots = document.getElementById('collection-roots');
    const name = document.getElementById('collection-name');
    const scan = document.getElementById('collection-scan');
    if (mount) state.form.mount = mount.value;
    if (roots) state.form.roots = roots.value;
    if (name) state.form.name = name.value;
    if (scan) state.form.scan = scan.checked;
  }

  function rootLines() {
    return state.form.roots.split('\n').map(value => value.trim()).filter(Boolean);
  }

  function setRoots(lines) {
    state.form.roots = lines.join('\n');
    const area = document.getElementById('collection-roots');
    if (area) area.value = state.form.roots;
  }

  function appendRoot(path) {
    const lines = rootLines();
    if (!lines.includes(path)) lines.push(path);
    setRoots(lines);
  }

  async function refreshLegacyViews() {
    if (window.clawDjLegacy?.refreshForPlan) await window.clawDjLegacy.refreshForPlan();
  }

  function emitCollectionChange(collection) {
    document.dispatchEvent(new CustomEvent('collectionchange', {detail: {collection}}));
  }

  function activeCollection() {
    return (state.data?.collections || []).find(collection => collection.active) || null;
  }

  function render() {
    const collections = state.data?.collections || [];
    const active = activeCollection();
    const busy = Boolean(state.data?.busy || state.working);
    const statusText = state.statusOverride || (
      active
        ? `${escapeHtml(active.display_name)} · ${escapeHtml(active.mount_base)}`
        : 'Legacy local library (no collection registry yet)'
    );
    container.innerHTML = `
      <h2>Music collection</h2>
      <div id="collection-picker-status" class="ingest-detail" aria-live="polite">${statusText}</div>
      <div class="collection-picker-row">
        <label for="collection-select"><strong>Known collections</strong></label>
        <select id="collection-select" ${busy ? 'disabled' : ''}>
          ${collections.length ? collections.map(collection => `
            <option value="${escapeHtml(collection.collection_id)}" ${collection.active ? 'selected' : ''}>
              ${escapeHtml(collection.display_name)}${collection.mounted ? '' : ' · unavailable'}
            </option>`).join('') : '<option value="">None registered</option>'}
        </select>
        <button id="collection-activate" type="button" ${busy || !collections.length ? 'disabled' : ''}>Use selected</button>
        <button id="collection-new-toggle" type="button" ${busy && !state.showingNew ? 'disabled' : ''}>${state.showingNew ? 'Cancel' : 'Start new collection…'}</button>
      </div>
      ${state.showingNew ? `
        <form id="collection-new-form" class="collection-new-form">
          <div class="collection-field-row">
            <label for="collection-mount"><strong>Mounted volume or folder</strong></label>
            <div class="collection-input-row">
              <input id="collection-mount" required placeholder="/Volumes/Elements" aria-label="Mounted volume or folder" value="${escapeHtml(state.form.mount)}" ${state.working ? 'readonly' : ''}>
              <button id="collection-browse-mount" type="button" ${state.working ? 'disabled' : ''}>Browse…</button>
            </div>
          </div>
          <div class="collection-field-row">
            <label for="collection-roots"><strong>Scan root folders</strong> <span class="ingest-detail">(one per line; can add several)</span></label>
            <textarea id="collection-roots" required placeholder="/Volumes/Elements/Music/HipHop&#10;/Volumes/Elements/Music/RnB" aria-label="Scan root folders" ${state.working ? 'readonly' : ''}>${escapeHtml(state.form.roots)}</textarea>
            <div class="collection-input-row">
              <button id="collection-browse-root" type="button" ${state.working ? 'disabled' : ''}>Add root…</button>
              <button id="collection-clear-roots" type="button" ${state.working ? 'disabled' : ''}>Clear roots</button>
            </div>
          </div>
          <div class="collection-field-row">
            <label for="collection-name"><strong>Collection name</strong> <span class="ingest-detail">(optional)</span></label>
            <input id="collection-name" placeholder="Elements" aria-label="Collection name" value="${escapeHtml(state.form.name)}" ${state.working ? 'readonly' : ''}>
          </div>
          <div class="collection-actions-row">
            <label class="collection-scan-option"><input id="collection-scan" type="checkbox" ${state.form.scan ? 'checked' : ''} ${state.working ? 'disabled' : ''}> Scan after creating (local tags only — not lyrics, network APIs, or Mixxx analysis)</label>
            <button id="collection-estimate" class="primary" type="submit" ${state.working ? 'disabled' : ''}>${state.working ? 'Working…' : 'Estimate &amp; continue'}</button>
          </div>
          <p class="ingest-detail">Estimate walks the chosen folders and can take a few minutes on a large drive. Your fields stay filled. A macOS folder dialog is used for Browse (the browser cannot expose real /Volumes paths).</p>
        </form>` : ''}`;
    bind();
  }

  function bind() {
    document.getElementById('collection-new-toggle')?.addEventListener('click', () => {
      if (state.working) return;
      readFormIntoState();
      state.showingNew = !state.showingNew;
      state.statusOverride = null;
      render();
    });
    document.getElementById('collection-activate')?.addEventListener('click', activateSelected);
    document.getElementById('collection-new-form')?.addEventListener('submit', createNew);
    document.getElementById('collection-mount')?.addEventListener('input', readFormIntoState);
    document.getElementById('collection-roots')?.addEventListener('input', readFormIntoState);
    document.getElementById('collection-name')?.addEventListener('input', readFormIntoState);
    document.getElementById('collection-scan')?.addEventListener('change', readFormIntoState);
    document.getElementById('collection-browse-mount')?.addEventListener('click', () => browseMount());
    document.getElementById('collection-browse-root')?.addEventListener('click', () => browseRoot());
    document.getElementById('collection-clear-roots')?.addEventListener('click', () => {
      state.form.roots = '';
      setRoots([]);
      status('Cleared scan roots.');
    });
  }

  async function browseMount() {
    if (state.working) return;
    readFormIntoState();
    status('Opening folder dialog for the collection mount…');
    try {
      const result = await request({
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          action: 'browse',
          prompt: 'Choose the mounted volume or collection folder',
          initial: state.form.mount || '/Volumes',
        }),
      });
      if (result.cancelled || !result.path) {
        status('Mount browse cancelled.');
        return;
      }
      state.form.mount = result.path;
      if (!state.form.name) {
        const parts = result.path.replace(/\/+$/, '').split('/');
        state.form.name = parts[parts.length - 1] || '';
      }
      render();
      status(`Mount set to ${result.path}`);
    } catch (error) {
      status(error.message);
    }
  }

  async function browseRoot() {
    if (state.working) return;
    readFormIntoState();
    status('Opening folder dialog to add a scan root…');
    try {
      const result = await request({
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          action: 'browse',
          prompt: 'Choose a music folder to scan (add multiple roots one at a time)',
          initial: state.form.mount || rootLines().slice(-1)[0] || '/Volumes',
        }),
      });
      if (result.cancelled || !result.path) {
        status('Root browse cancelled.');
        return;
      }
      appendRoot(result.path);
      if (!state.form.mount) {
        // Convenience: if mount is empty, set it to the volume parent of first root when under /Volumes/X/...
        const match = result.path.match(/^(\/Volumes\/[^/]+)/);
        if (match) state.form.mount = match[1];
      }
      render();
      status(`Added root ${result.path}`);
    } catch (error) {
      status(error.message);
    }
  }

  async function load() {
    state.data = await request();
    // Keep draft + override when reloading mid-work.
    render();
    return state.data;
  }

  async function activateSelected() {
    const collectionId = document.getElementById('collection-select').value;
    if (!collectionId) return;
    state.working = true;
    render();
    status('Switching collection…');
    try {
      const collection = await request({
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'activate', collection_id: collectionId}),
      });
      await refreshLegacyViews();
      emitCollectionChange(collection);
      state.working = false;
      state.statusOverride = null;
      await load();
      status(`Using ${collection.display_name} · ${collection.mount_base}`);
    } catch (error) {
      state.working = false;
      render();
      status(error.message);
    }
  }

  async function createNew(event) {
    event.preventDefault();
    readFormIntoState();
    const mountBase = state.form.mount.trim();
    const roots = rootLines();
    const displayName = state.form.name.trim();
    const scanRequested = Boolean(state.form.scan);
    if (!mountBase || !roots.length) {
      status('Choose a mounted folder and at least one scan root.');
      return;
    }
    state.working = true;
    render();
    status('Counting audio files under the chosen roots (no tags opened yet). Large volumes can take several minutes — leave this tab open…');
    try {
      const estimate = await request({
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'estimate', mount_base: mountBase, roots}),
      });
      const seconds = Number(estimate.estimated_seconds || 0);
      const decision = scanRequested
        ? `Create this collection and scan ${estimate.audio_file_count.toLocaleString()} audio files now?\n\nEstimated local metadata time: about ${seconds.toLocaleString()} seconds (${Math.max(1, Math.round(seconds / 60))} min at a conservative rate).\n\nMount: ${mountBase}\nRoots:\n- ${roots.join('\n- ')}`
        : `Create this collection without scanning?\n\nThe estimate found ${estimate.audio_file_count.toLocaleString()} audio files; you can use Check for new music later.\n\nMount: ${mountBase}\nRoots:\n- ${roots.join('\n- ')}`;
      if (!window.confirm(decision)) {
        state.working = false;
        render();
        status('No collection was created. Your paths are still filled in.');
        return;
      }
      status('Creating collection and preparing the per-volume database…');
      const registration = {
        action: 'register',
        mount_base: mountBase,
        roots,
        display_name: displayName || undefined,
        scan: scanRequested,
      };
      const collection = await request({
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(registration),
      });
      state.showingNew = false;
      state.form = {mount: '', roots: '', name: '', scan: true};
      await refreshLegacyViews();
      emitCollectionChange(collection);
      state.working = false;
      await load();
      status(collection.scan_started
        ? `Using ${collection.display_name}; the confirmed scan is running.`
        : `Using ${collection.display_name}; no scan was started.`);
      if (collection.scan_started) pollUntilIdle();
    } catch (error) {
      state.working = false;
      render();
      status(error.message);
    }
  }

  async function pollUntilIdle() {
    const timer = window.setInterval(async () => {
      try {
        const data = await load();
        if (!data.busy) {
          window.clearInterval(timer);
          await refreshLegacyViews();
          status(`Using ${activeCollection()?.display_name || 'the active collection'}; scan finished.`);
        }
      } catch (error) {
        window.clearInterval(timer);
        status(error.message);
      }
    }, 1000);
  }

  load().catch(error => status(error.message));
  return {reload: load};
}
