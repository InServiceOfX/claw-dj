// Behavioral UI-handler checks without a browser, network, or Mixxx.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('brain/web/arrange.js', 'utf8').replace(/^import .*;\n/gm, '');
const calls = [];
let rejectSave = null;
let resolveSave = null;
let confirm = true;
const client = {
  setNote: async (...args) => { calls.push(['save', ...args]); if (rejectSave) throw rejectSave;
    if (resolveSave) await new Promise(resolve => { resolveSave = resolve; }); },
  clearNote: async (...args) => { calls.push(['clear', ...args]); },
};
const sandbox = {client, document: {getElementById: () => null}, window: {confirm: () => confirm}};
vm.createContext(sandbox);
vm.runInContext(source + '\nthis.ui = {renderTrack, wireSongNotes, renderAddToBunch};', sandbox);
const ui = sandbox.ui;
const html = ui.renderTrack({track_id: '/one', title: '<Who Shot Ya>', artist: 'Biggie'}, 0,
  {note: 'Keep intro\nAvoid </textarea><script>evil</script>', layer: 'plan', available: true}, null, 'first-plan');
assert.match(html, /Edit playback note/);
assert.match(html, /<textarea/);
assert.ok(html.includes('&lt;/textarea&gt;&lt;script&gt;evil&lt;/script&gt;'));
assert.match(html, /Save for this plan/);
assert.match(html, /Use library default/);
assert.match(html, /does not change the running mix/);
assert.match(html, /data-song-note-plan="first-plan"/);
const inherited = ui.renderTrack({track_id: '/two'}, 1, {note: 'Inherited', layer: 'global'});
assert.ok(!inherited.includes('data-note-clear'));
const bunchedPlan = {bunches: [{bunch_id: 'who-shot-ya', label: 'Who Shot Ya versions'}]};
assert.match(ui.renderAddToBunch(bunchedPlan, 2), /Add to bunch \(2\)/);
assert.ok(!ui.renderAddToBunch(bunchedPlan, 2).includes('disabled'));
assert.ok(ui.renderAddToBunch(bunchedPlan, 0).includes('disabled'));

function fixture({drafts = new Map(), trackId = '/one', plan = 'first-plan', original = 'Original'} = {}) {
  const listeners = {};
  const field = {value: 'Keep intro\nSkip spoken scene', defaultValue: original};
  const status = {textContent: ''};
  const details = {open: true};
  const buttons = {};
  for (const key of ['cancel', 'clear']) buttons[key] = {
    disabled: false, addEventListener: (kind, fn) => { listeners[key] = fn; },
  };
  const controls = [field, ...Object.values(buttons)];
  const form = {
    dataset: {songNote: trackId, songNotePlan: plan}, elements: {note: field},
    addEventListener: (kind, fn) => { listeners[kind] = fn; },
    querySelector: selector => selector.includes('cancel') ? buttons.cancel : selector.includes('clear') ? buttons.clear : status,
    querySelectorAll: () => controls,
    closest: () => details,
    reset: () => { field.value = field.defaultValue; },
  };
  let slug = plan;
  const saved = [];
  ui.wireSongNotes({querySelectorAll: () => [form]}, {
    drafts, getSlug: () => slug, onSaved: async (...args) => { saved.push(args); },
  });
  return {listeners, field, status, details, controls, saved, switchPlan: () => { slug = 'second-plan'; }};
}
(async () => {
  let f = fixture();
  await f.listeners.submit({preventDefault() {}});
  assert.deepEqual(calls.pop(), ['save', 'first-plan', '/one', 'Keep intro\nSkip spoken scene', 'human']);
  assert.equal(f.saved.length, 1);
  assert.ok(f.controls.every(c => !c.disabled));
  f = fixture();
  f.listeners.cancel();
  assert.equal(f.field.value, 'Original');
  assert.equal(f.details.open, false);
  assert.equal(calls.length, 0);
  confirm = false;
  await f.listeners.clear();
  assert.equal(calls.length, 0);
  confirm = true;
  await f.listeners.clear();
  assert.deepEqual(calls.pop(), ['clear', 'first-plan', '/one']);
  rejectSave = new Error('Plan changed; refresh before retrying');
  f = fixture();
  await f.listeners.submit({preventDefault() {}});
  assert.match(f.status.textContent, /Plan changed/);
  assert.equal(f.field.value, 'Keep intro\nSkip spoken scene');
  assert.ok(f.controls.every(c => !c.disabled));
  assert.equal(f.saved.length, 0);
  assert.equal(calls.length, 1); // No automatic retry.
  calls.length = 0;
  rejectSave = null;
  f = fixture();
  f.switchPlan();
  await f.listeners.submit({preventDefault() {}});
  await f.listeners.clear();
  assert.equal(calls.length, 0); // Old visible forms never write into a new plan.
  assert.match(f.status.textContent, /plan switched/);
  const drafts = new Map();
  const songA = fixture({drafts});
  const songB = fixture({drafts, trackId: '/two'});
  songB.field.value = 'Keep my unfinished skit note';
  songB.listeners.input();
  await songA.listeners.submit({preventDefault() {}});
  calls.length = 0;
  const refreshedB = fixture({drafts, trackId: '/two'});
  assert.equal(refreshedB.field.value, 'Keep my unfinished skit note');
  assert.match(refreshedB.status.textContent, /Unsaved draft restored/);
  assert.equal(refreshedB.details.open, true);
  const otherPlanB = fixture({drafts, trackId: '/two', plan: 'second-plan'});
  assert.notEqual(otherPlanB.field.value, refreshedB.field.value);
  const changedB = fixture({drafts, trackId: '/two', original: 'Someone else edited this note'});
  assert.match(changedB.status.textContent, /saved note changed/);
  assert.equal(changedB.field.value, refreshedB.field.value);
  changedB.listeners.cancel();
  assert.equal(changedB.field.value, 'Someone else edited this note');
  assert.equal(drafts.size, 0);
  for (const kind of ['keydown', 'dragstart', 'drop']) {
    let stopped = false;
    f.listeners[kind]({stopPropagation() { stopped = true; }});
    assert.equal(stopped, true);
  }
  resolveSave = true;
  f = fixture();
  const pending = f.listeners.submit({preventDefault() {}});
  assert.ok(f.controls.every(c => c.disabled));
  f.switchPlan();
  resolveSave();
  await pending;
  assert.equal(calls[0][1], 'first-plan');
  assert.equal(f.saved.length, 0); // Do not refresh another plan after switching.
  console.log('Song note rendering, save/cancel/clear, conflicts, stale forms, drafts and plan-switch checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
