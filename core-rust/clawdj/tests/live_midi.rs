use clawdj::{open_output_port, port_presence_summary};

#[test]
fn opens_live_port_when_requested_and_available() {
    if std::env::var("CLAWDJ_LIVE").ok().as_deref() != Some("1") {
        eprintln!("skipping live MIDI test; set CLAWDJ_LIVE=1 to enable");
        return;
    }

    let summary = port_presence_summary().expect("failed to enumerate MIDI ports");
    if !summary.clawdj_present {
        eprintln!("skipping live MIDI test; no clawdj MIDI port present");
        return;
    }

    let _connection = open_output_port().expect("failed to open live clawdj MIDI output port");
}
