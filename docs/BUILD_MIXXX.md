# Building the patched Mixxx fork (macOS + Linux)

The control API (`--control-api-port`, everything `hands/mixxx_control.py`
and `core-rust/clawdj/src/control_api.rs` talk to) lives on the
`localhost-control-api` branch of the fork at
`repos/mixxxes/mixxx` (`git@github.com:ernestyalumni/mixxx.git`). Stock
Mixxx does NOT have this — you must build this fork, not `brew install
mixxx` / `apt install mixxx`. No CMake flag gates it; it's compiled in
whenever the binary exists, off unless you pass `--control-api-port`.

## macOS (arm64) — verified 2026-07-13 on this machine

```bash
cd repos/mixxxes/mixxx
git checkout localhost-control-api   # or whatever branch has the patch — check git log for "control API"

export BUILDENV_RELEASE=1
source tools/macos_buildenv.sh setup   # downloads the arm64 deps bundle into buildenv/
mkdir build-arm64 && cd build-arm64
cmake -DCMAKE_TOOLCHAIN_FILE="$MIXXX_VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" \
      -DCMAKE_BUILD_TYPE=RelWithDebInfo \
      -DBULK=ON -DCOREAUDIO=ON -DHSS1394=ON -DMACOS_BUNDLE=ON -DMODPLUG=ON \
      -DQT6=ON -DQML=ON -DWAVPACK=ON \
      -DVCPKG_TARGET_TRIPLET=arm64-osx-min1100-release ..
cmake --build . --parallel 10          # ~25 min on 10 cores

# The build-tree Mixxx.app is NOT self-contained — bundle it:
cmake --install . --prefix stage       # -> build-arm64/stage/Mixxx.app
```

**Do NOT run `tools/macos_release_buildenv.sh` directly** — it's CI-only
and exits immediately. Use `macos_buildenv.sh setup` with
`BUILDENV_RELEASE=1` set instead, as above.

**Gotcha that cost real time (fixed in the fork, commit `722eac1bce`):**
macOS bundles from `cmake --install` are App-Sandboxed. Without
`com.apple.security.network.server` in the entitlements, the control
API's `listen()` fails with a silent "Unknown error" (EPERM) even though
`--control-api-port` parses fine — the port just never opens. Already
fixed in `packaging/macos/Mixxx.entitlements` on this fork; if building
from a checkout that predates that commit, add the key yourself and
re-sign:

```bash
codesign --force -s - --entitlements packaging/macos/Mixxx.entitlements \
  path/to/Mixxx.app
```

This produces an **ad-hoc-signed, unnotarized** app — fine for yourself,
but anyone else downloading it will hit Gatekeeper ("Mixxx can't be
opened because it is from an unidentified developer"). Workaround for
recipients: right-click → Open (not double-click) the first time, or
`xattr -cr Mixxx.app` to strip the quarantine flag. Real notarization
needs an Apple Developer account ($99/yr) — not set up here.

Install as the default app and launch with the control API:
```bash
ditto build-arm64/stage/Mixxx.app /Applications/Mixxx.app
open -a Mixxx --args --control-api-port 9995
```

## Linux — NOT yet independently re-verified on this exact fork checkout

Reconstructed from the fork's own CI recipe (`.github/workflows/build.yml`,
Ubuntu job) and `tools/debian_buildenv.sh` — high confidence since it's
the fork's own tested CI config, but treat the first run as unverified
until it's actually been done end-to-end here. A prior Linux box did
build this successfully in a `BuildGcc/` directory (see `docs/HANDOFF.md`
/ `docs/QUICK_MIX_DEMO.md`), but the exact commands used there weren't
recorded — use the CI-derived recipe below instead of guessing at that
history.

```bash
cd repos/mixxxes/mixxx
git checkout localhost-control-api

./tools/debian_buildenv.sh setup       # apt-installs Qt6/build deps (Debian/Ubuntu + derivatives)
mkdir BuildGcc && cd BuildGcc
cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo \
      -DQT6=ON -DQML=ON -DBULK=ON -DFFMPEG=ON -DLOCALECOMPARE=ON \
      -DMAD=ON -DMODPLUG=ON -DWAVPACK=ON -DINSTALL_USER_UDEV_RULES=OFF ..
make -j$(nproc)
```

**Known OOM gotcha (HANDOFF.md, hit on a 16-core/15GiB machine):** RelWithDebInfo
link jobs can OOM-freeze the machine at high `-j`. If the build stalls or
the machine hangs, use `nice -n19 make -j4` instead of a high parallelism
count, especially on <16 GiB RAM.

Run it:
```bash
./mixxx --developer --controller-debug --control-api-port 9995
# log should show: [clawdj] init: clawdj mapping loaded
```

**Portability note:** unlike the macOS bundle, this Linux build links
against system Qt6/libs — the binary is NOT portable across distros or
even Ubuntu versions without matching library versions. Building a truly
portable artifact (AppImage) is not currently set up; see "Prebuilt
binaries" below for what that means for distribution.

## Prebuilt binaries on GitHub — feasible, worth doing, with caveats

**macOS: yes, straightforwardly.** `cmake --install`'s bundle is
self-contained (`fixup_bundle` copies in its Qt/dependency libs), so
zipping `stage/Mixxx.app` and attaching it to a **GitHub Release** (not a
regular repo file — Release assets support up to 2 GB, well over our
~184 MB bundle, and don't bloat the git history the way committing a
binary would) works for anyone on arm64 macOS. They still hit the
Gatekeeper friction above — document the `xattr -cr` workaround
prominently in the release notes, since that's the single biggest
"why won't this open" support question you'll get.

**Linux: partial.** A `.deb` built by the CI recipe above only installs
cleanly on the *same* Ubuntu/Debian version+arch it was built on — not a
universal Linux binary. Real portability would need an AppImage build
(Mixxx upstream doesn't currently produce one either, per the CI
matrix). For now, either (a) publish per-distro `.deb`s and accept the
narrower audience, or (b) just document the build-from-source steps above
as the Linux path and only ship a macOS prebuilt binary. (a)+the source
docs together is the pragmatic move — most Linux users building
open-source audio tools are comfortable compiling anyway.

**GPL compliance:** Mixxx is GPLv2. Redistributing binaries requires
source availability — trivially satisfied here since the fork's source
*is* the public GitHub repo the Release lives under. No extra written
offer needed as long as the Release links back to the exact commit/tag
that produced the binary.

**Practical setup:** tag a release (`git tag v0.1-clawdj-macos && git push
--tags`), zip `stage/Mixxx.app`, attach via `gh release create v0.1-clawdj-macos
Mixxx-macos-arm64.zip --notes "..."` (or the GitHub web UI), and note the
exact source commit hash in the release body so it's reproducible.
