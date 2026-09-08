pub mod chroma;
pub mod command;
pub mod control_api;
pub mod gesture;
pub mod live;
pub mod midi;
pub mod queue;
pub mod rhythm;
pub mod stems;
pub mod verse;

pub use chroma::{ChromaReport, analyze_paths};
pub use command::{Deck, JsonCommand, Operation};
pub use live::{BeatClock, BeatTick, TransitionReport, transition};
pub use midi::{
    MIDI_NOTE_ON_STATUS, MidiMessage, PortPresenceSummary, build_message, open_input_port,
    open_output_port, port_presence_summary, send_message,
};
pub use queue::{
    QUEUE_NAME, default_mixxx_db_path, open_mixxx_database, queue_clear, queue_init, queue_set,
};
pub use stems::{
    StemKind, StemPair, StemPairReport, StemTrack, classify_stem, is_showcase_acapella,
    is_vocal_over_bed, pair_vocals,
};
pub use verse::{
    CuePlacement, LyricSegment, VerseCueDecision, VerseCueRequest, classify_cue, has_vocal_verses,
    respect_verse_entry, respect_verse_exit,
};
