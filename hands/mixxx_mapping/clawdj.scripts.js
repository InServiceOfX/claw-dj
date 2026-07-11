// clawdj.scripts.js
//
// Minimal Mixxx controller script that interprets MIDI from `IAC Driver clawdj`
// (or any port renamed to `clawdj`) as high-level DJ ops driven by clawdj-core.
//
// All declared via <script-binding/> in clawdj.midi.xml. We receive the raw
// MIDI bytes; non-script-binding controls (CC continuous) are wired directly
// to the engine in the XML and never touch this file.
//
// Mixxx 2.4+: this runs in QJSEngine (ES7-ish). No node modules.

// eslint-disable-next-line no-var
var clawdj = {};

clawdj.init = function (id, debugging) {
    clawdj._id = id;
    clawdj._debug = !!debugging;
    clawdj._log("init: clawdj mapping loaded");

    // Emit a one-shot heartbeat note so clawdj-core can confirm the bridge
    // is live. Channel 16, note 0x7F, velocity 0x7F.
    midi.sendShortMsg(0x9F, 0x7F, 0x7F);
};

clawdj.shutdown = function () {
    clawdj._log("shutdown");
    midi.sendShortMsg(0x9F, 0x7F, 0x00);
};

// ---------- helpers ----------

clawdj._log = function (msg) {
    if (typeof console !== "undefined" && console.log) {
        console.log("[clawdj] " + msg);
    } else {
        print("[clawdj] " + msg);
    }
};

clawdj._noteOn = function (value) {
    return value && value > 0;
};

// Load whatever is currently sitting in the playlist named `__clawdj_queue`
// at row 0. clawdj-core inserts the row before sending the load message.
//
// Strategy: the most reliable scriptable load is `LoadSelectedTrackFromGroup`,
// which loads whatever the GUI has selected. We use the [Library] sidebar
// controls to navigate to our playlist, then the [Library] track-list controls
// to position on row 0, then fire the load.
//
// IMPORTANT: this navigation moves the user's GUI cursor. That's fine for a
// dedicated AI session; for production we will switch to a sidebar focus
// approach that doesn't disturb the visible selection. Tracked as a TODO.
clawdj._loadFromQueue = function (deck) {
    // 1. Focus sidebar root, navigate to "Playlists" → "__clawdj_queue".
    //    Mixxx exposes [Library] controls: MoveLeft/MoveRight/MoveUp/MoveDown,
    //    GoToItem, MoveTrack, MoveFocus. Without a stable "select by name"
    //    API we have to either:
    //       a) ask the user to click __clawdj_queue once per session, OR
    //       b) rely on the sidebar last-selected being our playlist (we
    //          arrange this at clawdj setup time).
    //    For M0 we go with (b); the launcher leaves __clawdj_queue selected.

    // 2. Move the highlight to track row 0. MoveTrack -N is "go up N",
    //    MoveTrack +N is "go down N". We snap to top by repeatedly going up.
    var i;
    for (i = 0; i < 1024; i++) {
        engine.setValue("[Library]", "MoveTrack", -1);
    }
    // Then row index 0 is selected (the first row).

    // 3. Fire load on the right deck.
    var group = "[Channel" + deck + "]";
    engine.setValue(group, "LoadSelectedTrack", 1);
};

// ---------- transport ----------

clawdj.loadDeck1 = function (channel, control, value, status, group) {
    if (!clawdj._noteOn(value)) return;
    clawdj._log("loadDeck1");
    clawdj._loadFromQueue(1);
};
clawdj.loadDeck2 = function (channel, control, value, status, group) {
    if (!clawdj._noteOn(value)) return;
    clawdj._log("loadDeck2");
    clawdj._loadFromQueue(2);
};

clawdj.playDeck1 = function (c, ctl, v) {
    if (!clawdj._noteOn(v)) return;
    engine.setValue("[Channel1]", "play", 1);
};
clawdj.playDeck2 = function (c, ctl, v) {
    if (!clawdj._noteOn(v)) return;
    engine.setValue("[Channel2]", "play", 1);
};
clawdj.pauseDeck1 = function (c, ctl, v) {
    if (!clawdj._noteOn(v)) return;
    engine.setValue("[Channel1]", "play", 0);
};
clawdj.pauseDeck2 = function (c, ctl, v) {
    if (!clawdj._noteOn(v)) return;
    engine.setValue("[Channel2]", "play", 0);
};

clawdj.syncDeck1 = function (c, ctl, v) {
    if (!clawdj._noteOn(v)) return;
    engine.setValue("[Channel1]", "beatsync", 1);
};
clawdj.syncDeck2 = function (c, ctl, v) {
    if (!clawdj._noteOn(v)) return;
    engine.setValue("[Channel2]", "beatsync", 1);
};

clawdj.cueDeck1 = function (c, ctl, v) {
    if (!clawdj._noteOn(v)) return;
    engine.setValue("[Channel1]", "cue_goto", 1);
};
clawdj.cueDeck2 = function (c, ctl, v) {
    if (!clawdj._noteOn(v)) return;
    engine.setValue("[Channel2]", "cue_goto", 1);
};

// ---------- TODO ----------
// - atomic recipes (notes 0x10..0x1F): bass swap, EQ-kill on next beat,
//   crossfade-over-bars, loop-roll, beatjump-on-1.
// - more reliable queue navigation (without disturbing GUI selection).
// - 14-bit CC pairs for sub-percent rate precision.
// - feedback for [Channel].bpm and [Channel].playposition (MIDI CC 0x40+).
