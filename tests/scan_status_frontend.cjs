// Exercise the actual page initialization against a resumed or idle scan.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('brain/web/playlist.html', 'utf8');
const start = html.lastIndexOf('(async()=>{\n');
const end = html.indexOf('window.clawDjLegacy', start);
assert.ok(start >= 0 && end > start);
const initialization = html.slice(start, end);
async function check(running) {
  const polls = [];
  const quiet = async () => ({});
  const context = {
    loadMeta: quiet, loadProviders: quiet, loadLibrary: quiet, loadSelected: quiet,
    loadIngest: async () => ({running}),
    pollIngest: message => polls.push(message),
    pollBrain: async () => ({running: false}), pollMix: quiet,
    pollMixUntilIdle() {}, showPage() {}, location: {hash: '#curate'},
    el: () => { throw new Error('Initialization unexpectedly failed'); },
  };
  await vm.runInNewContext(initialization, context);
  assert.equal(polls.length, running ? 1 : 0);
}
(async () => {
  await check(true);
  await check(false);
  console.log('Reloaded active scans resume polling; idle scans do not start a poll.');
})().catch(error => { console.error(error); process.exitCode = 1; });
