use std::{
    path::PathBuf,
    thread,
    time::{Duration, Instant},
};

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use clawdj::{
    JsonCommand, analyze_paths, command::Deck, open_mixxx_database, open_output_port,
    port_presence_summary, queue_clear, queue_init, queue_set, send_message,
};
use tracing::info;
use tracing_subscriber::{EnvFilter, layer::SubscriberExt, util::SubscriberInitExt};

#[derive(Debug, Parser)]
#[command(name = "clawdj")]
#[command(about = "Drive Mixxx through the clawdj virtual MIDI bridge")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Debug, Subcommand)]
enum Commands {
    Setup,
    Load {
        deck: Deck,
        track_id: i64,
    },
    Cmd {
        json: String,
    },
    /// Print live beat ticks + measured BPM from Mixxx's feedback bus.
    Monitor {
        #[arg(long, default_value_t = 10)]
        seconds: u64,
    },
    /// Beat-anchored transition: measure the outgoing deck's live BPM, start
    /// the incoming deck on a beat, sync it, crossfade over N beats.
    Transition {
        #[arg(long)]
        from: Deck,
        #[arg(long)]
        to: Deck,
        #[arg(long, default_value_t = 16)]
        beats: u32,
    },
    DemoMix,
    DemoTransition,
    DemoJuggle,
    DemoLoop,
    Queue {
        #[command(subcommand)]
        command: QueueCommands,
        #[arg(long)]
        db_path: Option<PathBuf>,
    },
    /// Chromagram fingerprints + cosine similarity for a small ordered set.
    /// Not for full-library scans — decode cost scales with track count.
    Chroma {
        /// Write JSON report here (fingerprints + similarity matrix).
        #[arg(long)]
        out: PathBuf,
        /// Audio file paths (mp3/m4a/flac/wav). Prefer ≤16 tracks.
        #[arg(last = true, required = true)]
        paths: Vec<PathBuf>,
    },
    /// Read/write any Mixxx control over the TCP control API (port 9995).
    Ctl {
        #[command(subcommand)]
        command: CtlCommands,
        #[arg(long, default_value_t = clawdj::control_api::DEFAULT_PORT)]
        port: u16,
    },
    /// Beat-accurate DJ gestures over the control API (see
    /// docs/MIXXX_CONTROL_SURFACE.md for the vocabulary).
    Gesture {
        #[command(subcommand)]
        command: GestureCommands,
        #[arg(long, default_value_t = clawdj::control_api::DEFAULT_PORT)]
        port: u16,
    },
}

#[derive(Debug, Subcommand)]
enum CtlCommands {
    Get {
        group: String,
        key: String,
    },
    Set {
        group: String,
        key: String,
        value: f64,
    },
}

#[derive(Debug, Subcommand)]
enum GestureCommands {
    /// Turntable brake to a stop.
    Brake {
        #[arg(long)]
        deck: u8,
        #[arg(long, default_value_t = 1.2)]
        seconds: f64,
    },
    /// Throw the platter backwards, then stop.
    Spinback {
        #[arg(long)]
        deck: u8,
        #[arg(long, default_value_t = 1.6)]
        seconds: f64,
        #[arg(long, default_value_t = 4.0)]
        intensity: f64,
    },
    /// Beat-anchored EQ kill-switch bass swap between two decks.
    KillSwap {
        #[arg(long)]
        from: u8,
        #[arg(long)]
        to: u8,
    },
    /// Restore all EQ kill switches on a deck.
    KillRestore {
        #[arg(long)]
        deck: u8,
    },
    /// Slip-reverse (censor) for N beats, snapping back on grid.
    Censor {
        #[arg(long)]
        deck: u8,
        #[arg(long, default_value_t = 2)]
        beats: u32,
    },
    /// Beat-anchored slip loop-roll stutter fill.
    Stutter {
        #[arg(long)]
        deck: u8,
        #[arg(long, default_value_t = 4)]
        rolls: u32,
        #[arg(long, default_value_t = 0.5)]
        size: f64,
    },
    /// Smoothstep crossfade over N beats of the outgoing deck's live tempo.
    Fade {
        #[arg(long)]
        from: u8,
        #[arg(long)]
        to: u8,
        #[arg(long, default_value_t = 16)]
        beats: u32,
    },
}

#[derive(Debug, Subcommand)]
enum QueueCommands {
    Init,
    Set { deck: Deck, track_id: i64 },
    Clear,
}

fn main() -> Result<()> {
    init_tracing();
    let cli = Cli::parse();

    match cli.command {
        Commands::Setup => run_setup(),
        Commands::Load { deck, track_id } => {
            run_operation(clawdj::Operation::Load { deck, track_id })
        }
        Commands::Cmd { json } => {
            let command: JsonCommand =
                serde_json::from_str(&json).context("failed to parse command JSON")?;
            run_operation(command.into_operation()?)
        }
        Commands::Monitor { seconds } => run_monitor(seconds),
        Commands::Transition { from, to, beats } => run_transition(from, to, beats),
        Commands::DemoMix => run_demo_mix(),
        Commands::DemoTransition => run_demo_transition(),
        Commands::DemoJuggle => run_demo_juggle(),
        Commands::DemoLoop => run_demo_loop(),
        Commands::Queue { command, db_path } => run_queue(command, db_path),
        Commands::Chroma { out, paths } => run_chroma(out, paths),
        Commands::Ctl { command, port } => run_ctl(command, port),
        Commands::Gesture { command, port } => run_gesture(command, port),
    }
}

fn run_chroma(out: PathBuf, paths: Vec<PathBuf>) -> Result<()> {
    if paths.len() > 24 {
        eprintln!(
            "warning: {} paths is a lot for chromagram; prefer the filtered ordered set (≤12–16)",
            paths.len()
        );
    }
    let report = analyze_paths(&paths)?;
    if let Some(parent) = out.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let json = serde_json::to_string_pretty(&report)?;
    std::fs::write(&out, format!("{json}\n"))?;
    println!(
        "chroma: {} tracks -> {} (similarity on diagonal = 1.0)",
        report.track_count,
        out.display()
    );
    Ok(())
}

fn run_setup() -> Result<()> {
    let summary = port_presence_summary()?;

    println!("Input ports:");
    for port in &summary.input_ports {
        println!("  - {port}");
    }

    println!("Output ports:");
    for port in &summary.output_ports {
        println!("  - {port}");
    }

    println!("clawdj present: {}", summary.clawdj_present);
    Ok(())
}

fn run_operation(operation: clawdj::Operation) -> Result<()> {
    let mut connection = open_output_port()?;
    if let clawdj::Operation::Load { deck, track_id } = operation {
        info!(deck = deck.as_u8(), track_id, "track id received for load");
        let message = operation.to_message();
        send_message(&mut connection, &message)?;
        return Ok(());
    }

    let message = operation.to_message();
    send_message(&mut connection, &message)
}

fn run_monitor(seconds: u64) -> Result<()> {
    let clock = clawdj::BeatClock::start()?;
    println!("listening for beat ticks for {seconds}s (start a deck if silent)...");

    let deadline = Instant::now() + Duration::from_secs(seconds);
    let mut last_tick: [Option<Instant>; 2] = [None, None];
    while let Some(remaining) = deadline.checked_duration_since(Instant::now()) {
        let Ok(tick) = clock_next_any(&clock, remaining) else {
            break;
        };
        let slot = usize::from(tick.deck - 1);
        let bpm_note = match last_tick[slot] {
            Some(previous) => {
                let gap = tick.at.duration_since(previous).as_secs_f64();
                format!("{:6.2} BPM", 60.0 / gap)
            }
            None => "  (first)".to_owned(),
        };
        last_tick[slot] = Some(tick.at);
        println!("deck {}  beat  {bpm_note}", tick.deck);
    }
    Ok(())
}

// The monitor wants ticks from either deck; BeatClock::next_beat filters to
// one, so peel ticks off directly via a throwaway single-deck wait per deck.
fn clock_next_any(clock: &clawdj::BeatClock, timeout: Duration) -> Result<clawdj::BeatTick> {
    clock.next_any(timeout)
}

fn run_transition(from: Deck, to: Deck, beats: u32) -> Result<()> {
    let clock = clawdj::BeatClock::start()?;
    let mut connection = open_output_port()?;
    println!(
        "transition deck {} -> deck {} over {beats} beats (measuring live BPM...)",
        from.as_u8(),
        to.as_u8()
    );
    let report = clawdj::transition(&mut connection, &clock, from, to, beats)?;
    println!(
        "done: measured {:.2} BPM, faded over {:.1}s",
        report.measured_bpm,
        report.fade.as_secs_f64()
    );
    Ok(())
}

fn run_demo_mix() -> Result<()> {
    let mut connection = open_output_port()?;
    println!("connected to the live clawdj MIDI port");

    for message in [
        [0xBF, 0x00, 0x00], // crossfader left
        [0x9F, 0x02, 0x7F], // deck 1 play
    ] {
        connection.send(&message).context("failed to send MIDI")?;
        thread::sleep(Duration::from_millis(250));
    }

    thread::sleep(Duration::from_secs(12));

    connection
        .send(&[0x9F, 0x03, 0x7F])
        .context("failed to start deck 2")?;
    for value in (0..=127).step_by(4) {
        connection
            .send(&[0xBF, 0x00, value])
            .context("failed to move crossfader")?;
        thread::sleep(Duration::from_millis(180));
    }

    thread::sleep(Duration::from_secs(120));
    Ok(())
}

fn run_demo_transition() -> Result<()> {
    let mut connection = open_output_port()?;
    println!("connected to the live clawdj MIDI port");

    for message in [
        [0xBF, 0x00, 0x00], // crossfader left
        [0xBF, 0x01, 0x7F], // deck 1 volume up
        [0xBF, 0x02, 0x7F], // deck 2 volume up
        [0x9F, 0x02, 0x7F], // deck 1 play
        [0x9F, 0x07, 0x7F], // deck 2 cue
        [0x9F, 0x09, 0x7F], // deck 2 beatsync
    ] {
        send_midi(&mut connection, message)?;
        thread::sleep(Duration::from_millis(220));
    }

    thread::sleep(Duration::from_secs(8));
    send_midi(&mut connection, [0x9F, 0x09, 0x7F])?;
    send_midi(&mut connection, [0x9F, 0x03, 0x7F])?;
    thread::sleep(Duration::from_millis(500));
    send_midi(&mut connection, [0x9F, 0x09, 0x7F])?;

    for value in (0..=127).step_by(3) {
        send_midi(&mut connection, [0xBF, 0x00, value])?;
        thread::sleep(Duration::from_millis(230));
    }

    send_midi(&mut connection, [0x9F, 0x04, 0x7F])?;
    thread::sleep(Duration::from_secs(45));
    Ok(())
}

fn run_demo_juggle() -> Result<()> {
    let mut connection = open_output_port()?;
    println!("connected to the live clawdj MIDI port");

    // Reset both decks near their cue/start points and start with deck 1.
    send_midi(&mut connection, [0x9F, 0x04, 0x7F])?;
    send_midi(&mut connection, [0x9F, 0x05, 0x7F])?;
    send_midi(&mut connection, [0x9F, 0x06, 0x7F])?;
    send_midi(&mut connection, [0x9F, 0x07, 0x7F])?;
    send_midi(&mut connection, [0xBF, 0x00, 0x00])?;
    send_midi(&mut connection, [0x9F, 0x02, 0x7F])?;
    thread::sleep(Duration::from_secs(4));

    // Alternating cue-drop cuts: classic two-copy beat-juggle shape.
    for _ in 0..8 {
        send_midi(&mut connection, [0x9F, 0x05, 0x7F])?;
        send_midi(&mut connection, [0x9F, 0x07, 0x7F])?;
        send_midi(&mut connection, [0xBF, 0x00, 0x7F])?;
        send_midi(&mut connection, [0x9F, 0x03, 0x7F])?;
        thread::sleep(Duration::from_millis(520));

        send_midi(&mut connection, [0x9F, 0x04, 0x7F])?;
        send_midi(&mut connection, [0x9F, 0x06, 0x7F])?;
        send_midi(&mut connection, [0xBF, 0x00, 0x00])?;
        send_midi(&mut connection, [0x9F, 0x02, 0x7F])?;
        thread::sleep(Duration::from_millis(520));
    }

    // Let both run, then do fast transformer-style fader cuts.
    send_midi(&mut connection, [0x9F, 0x02, 0x7F])?;
    send_midi(&mut connection, [0x9F, 0x03, 0x7F])?;
    for value in [0x00, 0x7F].into_iter().cycle().take(24) {
        send_midi(&mut connection, [0xBF, 0x00, value])?;
        thread::sleep(Duration::from_millis(180));
    }

    // Short stutter punches on both intros.
    for _ in 0..6 {
        send_midi(&mut connection, [0xBF, 0x00, 0x00])?;
        send_midi(&mut connection, [0x9F, 0x06, 0x7F])?;
        send_midi(&mut connection, [0x9F, 0x02, 0x7F])?;
        thread::sleep(Duration::from_millis(220));
        send_midi(&mut connection, [0x9F, 0x04, 0x7F])?;

        send_midi(&mut connection, [0xBF, 0x00, 0x7F])?;
        send_midi(&mut connection, [0x9F, 0x07, 0x7F])?;
        send_midi(&mut connection, [0x9F, 0x03, 0x7F])?;
        thread::sleep(Duration::from_millis(220));
        send_midi(&mut connection, [0x9F, 0x05, 0x7F])?;
    }

    // Land on deck 2 and let it ride.
    send_midi(&mut connection, [0xBF, 0x00, 0x7F])?;
    send_midi(&mut connection, [0x9F, 0x07, 0x7F])?;
    send_midi(&mut connection, [0x9F, 0x03, 0x7F])?;
    thread::sleep(Duration::from_secs(16));
    Ok(())
}

fn send_midi(connection: &mut midir::MidiOutputConnection, message: [u8; 3]) -> Result<()> {
    connection.send(&message).context("failed to send MIDI")
}

fn run_demo_loop() -> Result<()> {
    let mut connection = open_output_port()?;
    println!("connected to the live clawdj MIDI port");

    send_midi(&mut connection, [0xBF, 0x00, 0x7F])?;
    send_midi(&mut connection, [0x9F, 0x03, 0x7F])?;
    thread::sleep(Duration::from_millis(600));

    for _ in 0..12 {
        send_midi(&mut connection, [0x9F, 0x07, 0x7F])?;
        send_midi(&mut connection, [0x9F, 0x03, 0x7F])?;
        thread::sleep(Duration::from_millis(260));
        send_midi(&mut connection, [0xBF, 0x00, 0x00])?;
        thread::sleep(Duration::from_millis(90));
        send_midi(&mut connection, [0xBF, 0x00, 0x7F])?;
        thread::sleep(Duration::from_millis(260));
    }

    for _ in 0..8 {
        send_midi(&mut connection, [0x9F, 0x05, 0x7F])?;
        thread::sleep(Duration::from_millis(120));
        send_midi(&mut connection, [0x9F, 0x07, 0x7F])?;
        send_midi(&mut connection, [0x9F, 0x03, 0x7F])?;
        thread::sleep(Duration::from_millis(180));
    }

    send_midi(&mut connection, [0xBF, 0x00, 0x7F])?;
    send_midi(&mut connection, [0x9F, 0x03, 0x7F])?;
    thread::sleep(Duration::from_secs(8));
    Ok(())
}

fn run_queue(command: QueueCommands, db_path: Option<PathBuf>) -> Result<()> {
    let path = db_path.unwrap_or_else(clawdj::default_mixxx_db_path);
    let connection = open_mixxx_database(&path)?;

    match command {
        QueueCommands::Init => {
            let playlist_id = queue_init(&connection)?;
            println!("initialized {playlist_id} at {}", path.display());
        }
        QueueCommands::Set { deck, track_id } => {
            queue_set(&connection, deck, track_id)?;
            println!(
                "set {} row 0 for deck {} to track_id {}",
                clawdj::QUEUE_NAME,
                deck.as_u8(),
                track_id
            );
        }
        QueueCommands::Clear => {
            queue_clear(&connection)?;
            println!("cleared {}", clawdj::QUEUE_NAME);
        }
    }

    Ok(())
}

fn init_tracing() {
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .with(tracing_subscriber::fmt::layer())
        .init();
}

fn run_ctl(command: CtlCommands, port: u16) -> Result<()> {
    let mut api = clawdj::control_api::ControlApi::connect(port)?;
    match command {
        CtlCommands::Get { group, key } => {
            println!("{}", api.get(&group, &key)?);
        }
        CtlCommands::Set { group, key, value } => {
            api.set(&group, &key, value)?;
            println!("ok");
        }
    }
    Ok(())
}

fn run_gesture(command: GestureCommands, port: u16) -> Result<()> {
    use clawdj::gesture;
    let mut api = clawdj::control_api::ControlApi::connect(port)?;
    match command {
        GestureCommands::Brake { deck, seconds } => gesture::brake(&mut api, deck, seconds)?,
        GestureCommands::Spinback {
            deck,
            seconds,
            intensity,
        } => gesture::spinback(&mut api, deck, seconds, intensity)?,
        GestureCommands::KillSwap { from, to } => gesture::kill_swap(&mut api, from, to, port)?,
        GestureCommands::KillRestore { deck } => gesture::kill_restore(&mut api, deck)?,
        GestureCommands::Censor { deck, beats } => gesture::censor(&mut api, deck, beats, port)?,
        GestureCommands::Stutter { deck, rolls, size } => {
            gesture::stutter(&mut api, deck, rolls, size, port)?
        }
        GestureCommands::Fade { from, to, beats } => {
            gesture::fade(&mut api, from, to, beats, port)?
        }
    }
    println!("gesture done");
    Ok(())
}
