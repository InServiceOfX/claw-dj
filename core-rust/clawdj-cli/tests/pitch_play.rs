//! Subprocess checks: default score inspection must not connect, even on port 0.
use serde_json::{Value, json};
use std::{
    io::Write,
    process::{Command, Stdio},
};

fn score() -> Value {
    json!({"deck":3,"bpm":120.,"cue_seconds":10.,"source_end_seconds":12.,
        "duration_seconds":100.,"sample_rate":44100.,"prepare_seconds":0.1,
        "max_late_seconds":0.05,"notes":[
            {"beat":0.,"semitones":0.,"gate_beats":0.5},
            {"beat":2.,"semitones":2.,"gate_beats":0.5}]})
}
fn run(input: Value, live: bool) -> std::process::Output {
    let mut cmd = Command::new(env!("CARGO_BIN_EXE_clawdj"));
    cmd.args(["pitch-play", "--port", "0"]);
    if live {
        cmd.arg("--live");
    }
    let mut child = cmd
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(input.to_string().as_bytes())
        .unwrap();
    child.wait_with_output().unwrap()
}
#[test]
fn default_is_connection_free_dry_run() {
    let result = run(score(), false);
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    let a: Value = serde_json::from_slice(&result.stdout).unwrap();
    assert_eq!(a[0]["on_seconds"], 0.1);
    assert_eq!(a[1]["semitones"], 2.);
    assert_eq!(a[1]["off_seconds"], 1.35);
}
#[test]
fn invalid_live_score_rejected_before_connect() {
    let mut s = score();
    s["notes"][0]["semitones"] = json!(12);
    let result = run(s, true);
    let error = String::from_utf8_lossy(&result.stderr);
    assert!(!result.status.success());
    assert!(error.contains("pitch must be"));
    assert!(!error.contains("not reachable"));
}
#[test]
fn unknown_fields_are_not_silently_ignored() {
    let mut s = score();
    s["tag"] = json!("unsupported");
    let result = run(s, false);
    assert!(!result.status.success());
    assert!(String::from_utf8_lossy(&result.stderr).contains("unknown field"));
}
