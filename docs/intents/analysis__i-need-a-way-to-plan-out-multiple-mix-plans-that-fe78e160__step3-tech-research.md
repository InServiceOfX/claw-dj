# Step 3: Tech Stack Research

**Intent:** `i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`
**Status:** Research Complete
**Date:** 2026-07-31

> **Output location note.** The workflow prescribes
> `gh issue comment 3953181291 --repo / --body "..."`. That is not executable here and was not
> attempted. Re-verified for this step: `gh auth status` → "You are not logged into any GitHub
> hosts", `GH_TOKEN` unset, `--repo /` is not a repo spec, and the intent record's
> `Source kind: inline` means no GitHub issue exists. The real remote is
> `git@github.com:InServiceOfX/claw-dj.git`, where `3953181291` is a local-intent id, not an
> issue number. Written to a file, matching steps 1, 2, and 2b.

---

## Corrections to earlier steps (verified this session)

Four claims carried forward from step 2b are wrong. They matter because they change what code is
legal to write.

| Claim | Reality | Consequence |
|---|---|---|
| "Python 3.13 stdlib only" | `.venv/bin/python --version` → **3.14.3** (uv-managed CPython, `~/.local/share/uv/python/cpython-3.14.3-macos-aarch64-none`). `pyproject.toml` declares `requires-python = ">=3.13"`. | The floor and the actual interpreter disagree. Anything 3.14-only (`Path.copy()`) is available on this machine but violates the declared contract. **Decide before step 4:** bump the floor to `>=3.14`, or stay 3.13-compatible. |
| "no dev dependencies declared at all" | True for *dev* deps, but the project *does* declare runtime deps: `hai-agents[desktop]`, `librosa>=0.11.0`, `mido`, `mutagen>=1.48.1`, `python-dotenv`, `python-rtmidi`, locked in `uv.lock` (`revision = 3`). | "Stdlib only" describes the *server and GUI*, not the project. Correct framing: the web/persistence layer is deliberately stdlib; the audio layer is not. |
| "Tests are stdlib `unittest` classes discovered by pytest" | **pytest is not installed** (`No module named pytest`). The documented and working command is `PROGRESS.md:78` → `uv run python -m unittest discover -s tests`. Verified: **168 tests, OK, 9.0s**. | New modules must be `unittest`-discoverable. `-s tests` without `-t .` — `tests/` has no `__init__.py`, so `-t .` fails with `ImportError: Start directory is not importable`. |
| `sqlite3` general availability | `sqlite3.version`/`version_info` were **removed in 3.14** (deprecated 3.12). `sqlite3.sqlite_version` → `3.50.4`. `sqlite3.threadsafety` → **3** (serialized). | Any code reading `sqlite3.version` crashes on this interpreter. `threadsafety == 3` does *not* remove the `check_same_thread` guard — see Data Access below. |

One addition to step 2's stack table: the server is **`ThreadingHTTPServer`**
(`brain/playlist_editor.py:12,1423`), not plain `HTTPServer`. That is load-bearing for
`plan_revision` and is treated as a first-class constraint below.

---

## Documentation References

Candidates for `context_urls` in `architecture.json`, tagged with the module they serve.

| Technology | Official Docs | Key Pages | Serves |
|---|---|---|---|
| Python 3.14 (release) | [whatsnew/3.14](https://docs.python.org/3/whatsnew/3.14.html) | deferred annotations (PEP 649/749), `sqlite3` removals, `http.server` HTTPS, free-threading (PEP 779) | all |
| `http.server` | [library/http.server](https://docs.python.org/3/library/http.server.html) | `ThreadingHTTPServer`, `BaseHTTPRequestHandler.path`/`headers`/`rfile`/`wfile`, `send_response`/`send_header`/`end_headers`/`send_error`, `protocol_version`, security warning | `plan_api` |
| `sqlite3` | [library/sqlite3](https://docs.python.org/3/library/sqlite3.html) | `check_same_thread`, `threadsafety`, `autocommit` (3.12+), connection-as-context-manager, `executescript` | `plan_notes`, `plan_migration` |
| `pathlib` | [library/pathlib](https://docs.python.org/3/library/pathlib.html) | `Path.copy()`/`copy_into()`/`move()`/`move_into()` (**3.14**), `Path.replace()`, `Path.stat().st_mtime_ns`/`st_size` | `plan_store`, `plan_revision` |
| `hashlib` | [library/hashlib](https://docs.python.org/3/library/hashlib.html) | `file_digest(fileobj, digest)` (3.11+; raises `BlockingIOError` on non-blocking files as of 3.14) | `plan_revision` |
| `unicodedata` | [library/unicodedata](https://docs.python.org/3/library/unicodedata.html) | `normalize('NFKD', s)` for stdlib slugging | `plan_store` |
| HTTP conditional requests | [RFC 9110 §13.2](https://www.rfc-editor.org/rfc/rfc9110#section-13.2) · [MDN If-Match](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/If-Match) · [MDN 412](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/412) | strong vs. weak validators, mid-air-collision workflow, precondition evaluation happens *before* payload processing | `plan_revision`, `plan_api` |
| HTML Drag & Drop | [MDN Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API) | `draggable`, `dragstart`/`dragover`/`drop`/`dragend`, mandatory `preventDefault()` on `dragover`, `dataTransfer` read-only in `drop` | `plan_ui` |
| Accessible reordering | [Smashing: Accessible List Reordering](https://www.smashingmagazine.com/2018/01/dragon-drop-accessible-list-reordering/) · [React Aria: Taming the dragon](https://react-aria.adobe.com/blog/drag-and-drop) | keyboard pick-up/move/drop, move-up/down buttons, `aria-live` position announcements | `plan_ui` |
| `Element.moveBefore()` | [MDN Element.moveBefore](https://developer.mozilla.org/en-US/docs/Web/API/Element/moveBefore) · [Chrome blog](https://developer.chrome.com/blog/movebefore-api) | state-preserving atomic DOM move — **not Baseline** (~67% support) | `plan_ui` (avoid) |
| SQLite schema versioning | [PRAGMA user_version](https://sqlite.org/pragma.html#pragma_user_version) · [levlaz: migrations with user_version](https://levlaz.org/sqlite-db-migrations-with-pragma-user_version/) | numbered migrations, version flip as last statement inside the transaction | `plan_migration` (only if plan state lands in the DB) |
| Clustered TSP | [Clustered TSP via TSP methods (arXiv 2007.05254)](https://arxiv.org/abs/2007.05254) · [Ordered Clustered TSP (PMC3950363)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3950363/) | Chisman's reduction; contiguity as a formal constraint | `order_constraints` |

---

## Project Structure Conventions

There is no framework convention to import — the layout is the repo's own and every new module
must land inside it. Verified against the working tree:

```
claw-dj/
├── pyproject.toml            # requires-python, runtime deps, packages = [brain, hands, shared]
├── uv.lock                   # uv is the env/dep manager (revision 3)
├── PROGRESS.md               # canonical run commands (test cmd at :78)
├── brain/
│   ├── playlist_editor.py    # 1437 lines — HTTP app + PlaylistApp state  ← at prompt ceiling
│   ├── build_mix_plan.py     # 1895 lines                                  ← past prompt ceiling
│   ├── mix_graph.py          # greedy_mix_order (nearest-neighbour tour) :317
│   ├── mix_order_brief.py    # force_adjacent :199, apply_constraints :245
│   ├── library_index.py      # SCHEMA + PRAGMA table_info migrations :120-140
│   ├── archive_mix_plan.py   # proto plan store (sha256 + git provenance)
│   ├── web/playlist.html     # 863 lines, single asset                     ← at prompt ceiling
│   └── data/                 # gitignored — plans/<slug>/ goes here
├── tests/                    # unittest; NO __init__.py (discovery is -s tests, not -t .)
└── docs/intents/             # this workflow's output
```

**Placement decisions for the ten step-2 modules.** Foundational ones (`plan_store`,
`plan_revision`, `plan_bunches`, `transition_overrides`, `plan_paths`, `plan_notes`,
`order_constraints`, `plan_migration`) are new files under `brain/`, one module per file, each with
a matching `tests/test_<module>.py`. `plan_api` is a retrofit of `brain/playlist_editor.py`;
`plan_ui` is `brain/web/playlist.html`. Both retrofit targets are at the single-prompt ceiling
step 2 flagged, so:

- **Extract `brain/web/playlist.js`** (and serve it as a second static route) before adding
  arrange-tab JS. The page is already ~370 lines of inline vanilla JS inside 863 lines of HTML;
  the arrange tab plus drag-reorder plus a transition editor roughly doubles that.
- **Extract the route table out of `make_handler`** (see Routing below). That shrinks
  `playlist_editor.py` while making plan-scoped URLs expressible.

---

## Framework Patterns

### Routing — the blocker step 2b identified, and the fix

`BaseHTTPRequestHandler` has **no** path-parameter routing. Confirmed from the docs: it exposes
`self.path` (which *includes* the query string), `self.command`, `self.headers`, `self.rfile`,
`self.wfile`, and dispatches only by method name (`do_GET`, `do_POST`). Everything else is yours to
write. The current code is a literal `if parsed.path == "/api/meta": …` ladder
(`brain/playlist_editor.py:1262+`), so `/api/plans/<slug>/tracks` is genuinely unreachable today.

**Recommendation: a module-level route table, not a framework.** Keep the no-framework rule; make
dispatch data instead of control flow:

```python
ROUTES = [
    ("GET",  re.compile(r"^/api/plans$"),                    lambda app, m, body: app.list_plans()),
    ("GET",  re.compile(r"^/api/plans/(?P<slug>[a-z0-9-]+)$"), lambda app, m, body: app.get_plan(m["slug"])),
    ("POST", re.compile(r"^/api/plans/(?P<slug>[a-z0-9-]+)/bunches$"), ...),
]
```

Match against `urlparse(self.path).path` (never raw `self.path` — it carries the query). Constrain
the slug group to `[a-z0-9-]+` in the pattern itself: that is the path-traversal defence for
`brain/data/plans/<slug>/`, applied before any filesystem call. The 27 existing exact-match routes
become table entries with anchored literal patterns, so the retrofit is mechanical and the
`if`-ladder disappears.

The docs also note `protocol_version` defaults to `'HTTP/1.0'`; the current handler already sends an
accurate `Content-Length` (`_json`, `:1250-1257`), so raising it to `'HTTP/1.1'` for keep-alive is
safe if desired — but it is not required by this feature and is out of scope.

### Data Access

Two stores, two rules.

**SQLite (`brain/data/library.sqlite3`).** `sqlite3.threadsafety` is **3** (serialized) on this
build, but that describes the *C library*, not Python's guard: `check_same_thread` still defaults to
`True` and raises `ProgrammingError` if a connection crosses threads. Under `ThreadingHTTPServer`
every request is its own thread, so **a module-level long-lived connection is a latent crash**. The
established safe pattern is already in the repo — `brain/mix_directives.py:115`:

```python
with closing(sqlite3.connect(db_path)) as db:
    ...
```

New modules touching the DB follow that, per call. Note `brain/library_index.py:120` uses
`sqlite3.connect(path, timeout=30)` — keep the timeout for writer contention. Do **not** switch to
`autocommit=` (3.12+): the whole repo is on the default `LEGACY_TRANSACTION_CONTROL`, and mixing
models across modules is how you get surprise commits.

**Plan JSON (`brain/data/plans/<slug>/`).** Every write is an atomic replace:

1. write to a temp file **in the same directory** (same filesystem — `os.replace` is only atomic
   there),
2. `flush()` then `os.fsync()` the temp file,
3. `os.replace(tmp, target)` (`Path.replace()` maps to this),
4. optionally `fsync` the directory fd so the rename itself is durable.

On macOS, `fsync` does not force the drive cache; `fcntl(F_FULLFSYNC)` does. For a local DJ tool
that is over-engineering — flush + `os.replace` is the right stopping point, and the note exists so
nobody claims crash-durability the code doesn't provide.

`Path.copy()` (3.14) makes `plan_store.duplicate()` one line and recurses into directories — but it
does not exist on 3.13, which is the declared floor. Either bump `requires-python` or use
`shutil.copytree`. This is the concrete cost of the version mismatch above.

### "Middleware" — there is none, and one is needed

The stdlib gives no middleware hook. The one cross-cutting concern this feature introduces —
**every plan-mutating request must carry and check a revision token** — therefore has to live
somewhere explicit. Put it in the dispatcher: mark routes as mutating, and have the dispatcher do
read-rev → compare → call → write-rev, so `plan_revision` is enforced structurally rather than by
remembering to call it in 12 handlers.

**Protocol shape.** RFC 9110 §13.2 and MDN describe the canonical mid-air-collision workflow:
`GET` returns `ETag: "v1"`; the writer sends `If-Match: "v1"`; a mismatch is **412 Precondition
Failed**, evaluated *before* the request payload is processed. Two documented facts make the literal
header form a poor fit here:

- `If-Match` uses **strong comparison** — a `W/`-prefixed weak validator *never* matches.
- `If-Match` is defined for `PUT`/`PATCH`/`DELETE`; MDN explicitly notes it is not a standard use
  with `POST` — and all 19 existing mutations in this repo are `POST` with JSON bodies.

**Recommendation:** keep `POST`, carry `"base_rev": "<token>"` in the JSON body, and return
**409 Conflict** with the current rev and a diff summary. That matches the existing idiom, keeps
the fetch calls in `playlist.html` unchanged in shape, and avoids claiming HTTP conditional-request
semantics the routes don't actually implement. Emit the same token as an `ETag` header on plan
`GET`s anyway — free, standards-shaped, and useful to any agent harness using `curl`.

**Token computation.** `hashlib.file_digest(f, "sha256")` (3.11+) over the plan's JSON files. Do
**not** use `st_mtime` alone: two writes inside one filesystem timestamp tick are indistinguishable,
which is exactly the agent-writes-then-GUI-writes race this module exists to catch. `st_mtime_ns`
plus `st_size` is an acceptable fast pre-check to skip hashing, never the token itself.

**Security note specific to this feature.** The `http.server` docs warn that `send_header()` and
`send_response_only()` **do not validate CRLF** — header injection. Plan names here are free-form
user strings ("2001 expanded 25th anniversary mix"). If a plan name ever reaches a response header
(an `ETag`, a `Location` after create, a `Content-Disposition` on export), it must be sanitized or
slug-substituted first. Bind to `127.0.0.1` as today.

---

## Configuration Requirements

- **`pyproject.toml`** — resolve `requires-python` (`>=3.13` declared vs. 3.14.3 in use). No new
  runtime dependency is needed for any of the ten modules; everything above is stdlib.
- **No new config file.** The active-plan pointer (step 2's gap-#7 decision) is plan state, not
  configuration: `brain/data/plans/active.json`, inside the already-gitignored data dir.
- **`.gitignore`** — confirm `brain/data/` already covers `plans/`; it does.
- **Optional dev group.** `pytest` is absent and tests run fine under `unittest`. Adding pytest is
  not required by this feature and would be scope creep; if it is ever added, do it as
  `[dependency-groups] dev = ["pytest"]` so the runtime install stays clean.
- **`architecture.json`** — populate `context_urls` per module from the table above.

---

## Best Practices

1. **Contract bunches into supernodes; do not penalize edges.** The classic reduction (Chisman,
   cited in both CTSP papers) is "transform CTSP into TSP by adding or subtracting an arbitrarily
   large constant *M* to the cost of each intercluster edge." That guarantee holds for an *exact*
   solver. `greedy_mix_order` (`brain/mix_graph.py:317`) is a **nearest-neighbour tour**, and a
   greedy heuristic can still strand a cluster member no matter how large *M* is. The reduction that
   is correct-by-construction for a greedy orderer is **contraction**: collapse each bunch into one
   pseudo-track whose *entry* features are the first member's and *exit* features the last member's,
   run the existing tour over the contracted set, then expand. Contiguity becomes structurally
   impossible to violate, and — the actual defect step 2 named — **the bunch seams get scored**,
   because the in-edge is scored against the head and the out-edge against the tail. This also
   removes the `force_adjacent` displacement bug: `force_adjacent` (`mix_order_brief.py:199`) pulls
   both members out and reinserts them, so chaining `(A,B)` then `(B,C)` leaves A stranded, and
   nothing checks the post-condition. Keep `assert_bunches_intact(order)` as a post-condition anyway.
2. **Route by table, match on `urlparse(path).path`, constrain the slug in the regex.** `self.path`
   includes the query string; a slug pattern of `[a-z0-9-]+` is the traversal defence, applied
   before the filesystem sees anything.
3. **Never hold a SQLite connection across request threads.** `check_same_thread=True` is the
   default and `ThreadingHTTPServer` is thread-per-request; use `with closing(sqlite3.connect(...))`
   per call, as `brain/mix_directives.py:115` already does.
4. **Every plan write is temp-file → fsync → `os.replace` in the same directory.** An agent harness
   and the GUI can write concurrently; a half-written plan JSON is the one failure mode that loses
   hand-authored dj_notes.
5. **Rev tokens are content hashes, not mtimes.** `hashlib.file_digest`. Same-tick writes are the
   precise race being defended against.
6. **Ship "Move up / Move down" buttons alongside drag.** MDN documents real DnD caveats: text
   inside a `draggable` element can no longer be selected normally (Alt required), `dataTransfer` is
   readable only during `drop`, `dragover` **must** call `preventDefault()` or `drop` never fires,
   and touch support is absent. Buttons are the accessibility answer *and* the faster path for
   nudging one track. Announce position changes via `aria-live` ("moved to 3 of 12").
7. **Do not use `Element.moveBefore()`.** It is the right primitive for state-preserving reorder but
   is **not Baseline** (~67%, Safari unconfirmed). Re-render the list from the plan data on refresh;
   the lists are tens of items, not thousands.
8. **If plan state ever lands in SQLite, use `PRAGMA user_version`.** The repo's current pattern is
   additive `ALTER TABLE` guarded by `PRAGMA table_info` (`library_index.py:124-140`), which has no
   notion of ordering or of a failed partial migration. The standard fix is numbered migrations with
   the version flip as the last statement *inside* the transaction, so the version advances only if
   everything succeeded. This matters for `plan_migration`, whose stated requirement is "fail loudly
   and atomically on partial migration" — the current pattern cannot express that.
9. **Keep the runtime-dependency count at zero for these modules.** Slugging colloquial plan names
   is `unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')` plus a `re` pass and a
   collision-suffix loop — no `python-slugify`. Handle the empty-slug case (a name of only emoji or
   CJK normalizes to `""`) with a fallback id rather than letting an empty directory name through.
10. **New modules take paths as parameters.** The whole test suite isolates by patching module-level
    `DEFAULT_*` constants with `tempfile.TemporaryDirectory`; a module that hardcodes
    `brain/data/plans/` is untestable in this repo's style. Verified: 168 tests pass under
    `uv run python -m unittest discover -s tests`.

---

## Research notes per module

| Module | What research settled | What is still a product call |
|---|---|---|
| `plan_store` | stdlib slug recipe; `Path.copy()` for duplicate (3.14 only — see version mismatch) | retention / soft vs. hard delete (gap #10) |
| `plan_paths` | nothing external needed | — |
| `plan_revision` | `file_digest` for tokens; 409-in-body over `If-Match`/412, with `ETag` emitted anyway; atomic-replace recipe | — |
| `plan_notes` | per-call `closing(connect())`; stay on legacy transaction control | — |
| `plan_bunches` | — | **bunch scope: plan-local or library-level?** (gap #4) — still the highest-value unanswered question |
| `order_constraints` | **contraction over penalty-M** (best. practice 1); post-condition assert | how bunches interact with `regions` when both apply |
| `transition_overrides` | — | — |
| `plan_migration` | `PRAGMA user_version` if DB-resident; atomic-replace if file-resident | archives vs. named plans (gap #8) |
| `plan_api` | route table; CRLF sanitisation of plan names in headers; rev check in the dispatcher | switching during a live run (gap #11) |
| `plan_ui` | DnD event contract + `preventDefault()`; move-up/down + `aria-live`; avoid `moveBefore()`; extract `playlist.js` first | — |

---

## Decisions needed before Step 4

1. **`requires-python`: `>=3.13` or `>=3.14`?** Determines whether `Path.copy()` is usable and
   whether 3.13 is a supported target at all. Currently the declared floor and the installed
   interpreter disagree.
2. **Bunch scope** (carried from step 2, still open): plan-local, or a library-level object plans
   reference? Moves `plan_bunches` off "foundational" and onto `library_index`.
3. The three remaining step-2 gaps — bunch integrity on member removal (#5), archives vs. named
   plans (#8), switching during a live run (#11) — are product calls that research cannot settle.

---
*Proceeding to Step 4: Data Model Design*

Sources: [Python 3.14 whatsnew](https://docs.python.org/3/whatsnew/3.14.html) ·
[http.server](https://docs.python.org/3/library/http.server.html) ·
[sqlite3](https://docs.python.org/3/library/sqlite3.html) ·
[pathlib](https://docs.python.org/3/library/pathlib.html) ·
[hashlib](https://docs.python.org/3/library/hashlib.html) ·
[MDN If-Match](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/If-Match) ·
[MDN 412](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/412) ·
[MDN HTML Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API) ·
[MDN Element.moveBefore](https://developer.mozilla.org/en-US/docs/Web/API/Element/moveBefore) ·
[Chrome: moveBefore](https://developer.chrome.com/blog/movebefore-api) ·
[Smashing: Accessible List Reordering](https://www.smashingmagazine.com/2018/01/dragon-drop-accessible-list-reordering/) ·
[React Aria: Taming the dragon](https://react-aria.adobe.com/blog/drag-and-drop) ·
[SQLite PRAGMA user_version](https://sqlite.org/pragma.html#pragma_user_version) ·
[levlaz: SQLite migrations](https://levlaz.org/sqlite-db-migrations-with-pragma-user_version/) ·
[Clustered TSP via TSP methods](https://arxiv.org/abs/2007.05254) ·
[Ordered Clustered TSP](https://pmc.ncbi.nlm.nih.gov/articles/PMC3950363/)
