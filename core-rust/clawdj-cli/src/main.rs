use std::{path::PathBuf, thread, time::Duration};

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use clawdj::{
    JsonCommand, command::Deck, open_mixxx_database, open_output_port, port_presence_summary,
    queue_clear, queue_init, queue_set, send_message,
};
use midir::{MidiOutput, os::unix::VirtualOutput};
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
        Commands::DemoMix => run_demo_mix(),
        Commands::DemoTransition => run_demo_transition(),
        Commands::DemoJuggle => run_demo_juggle(),
        Commands::DemoLoop => run_demo_loop(),
        Commands::Queue { command, db_path } => run_queue(command, db_path),
    }
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

fn run_demo_mix() -> Result<()> {
    let midi_out =
        MidiOutput::new("clawdj-demo-out").context("failed to initialize MIDI output")?;
    let mut connection = midi_out
        .create_virtual("clawdj")
        .context("failed to create virtual MIDI output named clawdj")?;

    println!("virtual MIDI output 'clawdj' is live");
    println!("launch or restart Mixxx now so it can enumerate the port");
    thread::sleep(Duration::from_secs(240));

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
    let midi_out =
        MidiOutput::new("clawdj-transition-out").context("failed to initialize MIDI output")?;
    let mut connection = midi_out
        .create_virtual("clawdj")
        .context("failed to create virtual MIDI output named clawdj")?;

    println!("virtual MIDI output 'clawdj' is live");
    println!("launch or restart Mixxx now so it can enumerate the port");
    thread::sleep(Duration::from_secs(75));

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
    let midi_out =
        MidiOutput::new("clawdj-juggle-out").context("failed to initialize MIDI output")?;
    let mut connection = midi_out
        .create_virtual("clawdj")
        .context("failed to create virtual MIDI output named clawdj")?;

    println!("virtual MIDI output 'clawdj' is live");
    println!("launch or restart Mixxx now so it can enumerate the port");
    thread::sleep(Duration::from_secs(60));

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
    let midi_out =
        MidiOutput::new("clawdj-loop-out").context("failed to initialize MIDI output")?;
    let mut connection = midi_out
        .create_virtual("clawdj")
        .context("failed to create virtual MIDI output named clawdj")?;

    println!("virtual MIDI output 'clawdj' is live");
    println!("launch or restart Mixxx now so it can enumerate the port");
    thread::sleep(Duration::from_secs(120));

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
