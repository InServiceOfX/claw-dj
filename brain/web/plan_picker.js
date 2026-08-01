import {
  PlanApiError,
  createPlan,
  deletePlan,
  duplicatePlan,
  getActivePlan,
  listPlans,
  renamePlan,
  setActivePlan,
  setStatus,
} from './plan_client.js';

const STATUS_LABELS = {wip: 'Work in progress', ready: 'Ready', archived: 'Archived'};

function uniquePlans(groups) {
  const plans = new Map();
  for (const group of groups) for (const plan of group) plans.set(plan.slug, plan);
  return [...plans.values()].sort((a, b) =>
    Number(b.last_opened_at || b.updated_at || 0) - Number(a.last_opened_at || a.updated_at || 0));
}

export function mountPlanPicker(root, {onSwitch = () => {}, onStatusChange = () => {}} = {}) {
  if (!root) throw new Error('Plan picker root is required.');
  const state = {activeSlug: null, plans: [], busy: false};

  root.innerHTML = `
    <div class="plan-picker-row">
      <label for="plan-picker-select">Mix plan</label>
      <select id="plan-picker-select" aria-label="Active mix plan"></select>
      <span id="plan-picker-stale" class="stale-dot" aria-label="Plan freshness"></span>
      <select id="plan-picker-status" aria-label="Plan status"></select>
      <button type="button" data-plan-action="new">New</button>
      <button type="button" data-plan-action="rename">Rename</button>
      <button type="button" data-plan-action="duplicate">Duplicate</button>
      <button type="button" data-plan-action="delete">Delete</button>
    </div>
    <div id="plan-picker-message" class="plan-picker-message" role="status" aria-live="polite"></div>`;

  const select = root.querySelector('#plan-picker-select');
  const status = root.querySelector('#plan-picker-status');
  const stale = root.querySelector('#plan-picker-stale');
  const message = root.querySelector('#plan-picker-message');

  function activePlan() {
    return state.plans.find(plan => plan.slug === state.activeSlug) || null;
  }

  function setBusy(value) {
    state.busy = value;
    root.querySelectorAll('button, select').forEach(control => { control.disabled = value; });
  }

  function render() {
    const plan = activePlan();
    select.innerHTML = state.plans.length
      ? state.plans.map(item => `<option value="${escapeAttribute(item.slug)}">${escapeHtml(item.display_name)}</option>`).join('')
      : '<option value="">No plans yet</option>';
    select.value = state.activeSlug || '';
    status.innerHTML = Object.entries(STATUS_LABELS)
      .map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
    status.value = plan?.status || 'wip';
    stale.textContent = plan?.stale ? '● stale' : '● current';
    stale.classList.toggle('is-stale', Boolean(plan?.stale));
    stale.hidden = !plan;
    status.hidden = !plan;
    root.querySelectorAll('[data-plan-action="rename"], [data-plan-action="duplicate"], [data-plan-action="delete"]')
      .forEach(button => { button.disabled = state.busy || !plan; });
  }

  async function load() {
    let active = null;
    try {
      active = await getActivePlan();
    } catch (error) {
      if (!(error instanceof PlanApiError) || error.status !== 404) throw error;
    }
    state.plans = uniquePlans(await Promise.all([
      listPlans({status: 'wip'}),
      listPlans({status: 'ready'}),
      listPlans({status: 'archived'}),
    ]));
    state.activeSlug = active?.slug || null;
    if (active && !state.plans.some(plan => plan.slug === active.slug)) state.plans.unshift(active);
    render();
    return active;
  }

  async function activate(slug, announcement) {
    setBusy(true);
    try {
      const plan = await setActivePlan(slug);
      state.activeSlug = plan.slug;
      await load();
      message.textContent = announcement || `Switched to ${plan.display_name}.`;
      onSwitch(plan.slug);
      document.dispatchEvent(new CustomEvent('clawdj:plan-switched', {detail: {plan}}));
    } finally {
      setBusy(false);
      render();
    }
  }

  select.addEventListener('change', async () => {
    if (!select.value || select.value === state.activeSlug) return;
    try {
      await activate(select.value);
    } catch (error) {
      message.textContent = error.message;
      select.value = state.activeSlug || '';
    }
  });

  status.addEventListener('change', async () => {
    const plan = activePlan();
    if (!plan || status.value === plan.status) return;
    setBusy(true);
    try {
      const changed = await setStatus(plan.slug, status.value);
      Object.assign(plan, changed);
      message.textContent = `${changed.display_name} is now ${STATUS_LABELS[changed.status].toLowerCase()}.`;
      onStatusChange(changed.slug, changed.status);
      document.dispatchEvent(new CustomEvent('clawdj:plan-status-changed', {detail: {plan: changed}}));
    } catch (error) {
      message.textContent = error.message;
    } finally {
      setBusy(false);
      render();
    }
  });

  root.addEventListener('click', async event => {
    const button = event.target.closest('button[data-plan-action]');
    if (!button) return;
    const plan = activePlan();
    try {
      if (button.dataset.planAction === 'new') {
        const displayName = window.prompt('Name the new mix plan:');
        if (!displayName?.trim()) return;
        setBusy(true);
        const created = await createPlan(displayName.trim());
        await activate(created.slug, `Created and switched to ${created.display_name}.`);
      } else if (button.dataset.planAction === 'rename' && plan) {
        const displayName = window.prompt('Rename this mix plan:', plan.display_name);
        if (!displayName?.trim() || displayName.trim() === plan.display_name) return;
        setBusy(true);
        const changed = await renamePlan(plan.slug, displayName.trim());
        Object.assign(plan, changed);
        message.textContent = `Renamed plan to ${changed.display_name}.`;
      } else if (button.dataset.planAction === 'duplicate' && plan) {
        const displayName = window.prompt('Name the duplicate:', `${plan.display_name} copy`);
        if (!displayName?.trim()) return;
        setBusy(true);
        const created = await duplicatePlan(plan.slug, displayName.trim());
        await activate(created.slug, `Duplicated and switched to ${created.display_name}.`);
      } else if (button.dataset.planAction === 'delete' && plan) {
        if (!window.confirm(`Move “${plan.display_name}” to the plan trash?`)) return;
        setBusy(true);
        await deletePlan(plan.slug);
        await load();
        if (state.plans.length) await activate(state.plans[0].slug, `Deleted ${plan.display_name} and switched plans.`);
        else {
          message.textContent = `Deleted ${plan.display_name}. Create a plan to continue.`;
          onSwitch(null);
          document.dispatchEvent(new CustomEvent('clawdj:plan-switched', {detail: {plan: null}}));
        }
      }
    } catch (error) {
      message.textContent = error.message;
    } finally {
      setBusy(false);
      render();
    }
  });

  return {
    async refresh() { return load(); },
    setSnapshotState(slug, isStale) {
      const plan = state.plans.find(item => item.slug === slug);
      if (plan) plan.stale = Boolean(isStale);
      render();
    },
    get activeSlug() { return state.activeSlug; },
  };
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
