//! Client for the patched Mixxx localhost control API (line-delimited JSON
//! over TCP, default port 9995) — the Rust mirror of
//! `hands/mixxx_control.py`.
//!
//! The API is a universal gateway: `get`/`set` reach ANY existing Mixxx
//! ControlObject (see docs/MIXXX_CONTROL_SURFACE.md), `subscribe` pushes
//! `{"event":"change",...}` records, `load` puts a file on a deck.
//!
//! Pushed events interleave with replies on a shared connection, so
//! request/reply calls skip them. For beat-accurate waits, open a second
//! connection dedicated to subscriptions (`BeatWaiter`).

use std::io::{BufRead, BufReader, Write};
use std::net::TcpStream;
use std::time::Duration;

use anyhow::{Context, Result, anyhow, bail};
use serde_json::{Value, json};

pub const DEFAULT_PORT: u16 = 9995;

pub fn deck_group(deck: u8) -> String {
    format!("[Channel{deck}]")
}

pub struct ControlApi {
    writer: TcpStream,
    reader: BufReader<TcpStream>,
}

impl ControlApi {
    pub fn connect(port: u16) -> Result<Self> {
        let stream = TcpStream::connect(("127.0.0.1", port))
            .with_context(|| format!("Mixxx control API not reachable on 127.0.0.1:{port}"))?;
        stream.set_read_timeout(Some(Duration::from_secs(10)))?;
        let reader = BufReader::new(stream.try_clone()?);
        Ok(Self {
            writer: stream,
            reader,
        })
    }

    fn read_json(&mut self) -> Result<Value> {
        let mut line = String::new();
        loop {
            line.clear();
            let n = self.reader.read_line(&mut line)?;
            if n == 0 {
                bail!("control API connection closed");
            }
            if line.trim().is_empty() {
                continue;
            }
            return serde_json::from_str(line.trim()).context("invalid JSON from control API");
        }
    }

    fn request(&mut self, payload: Value) -> Result<Value> {
        let mut bytes = serde_json::to_vec(&payload)?;
        bytes.push(b'\n');
        self.writer.write_all(&bytes)?;
        loop {
            let reply = self.read_json()?;
            // Pushed subscription events can interleave with replies.
            if reply.get("event").is_some() {
                continue;
            }
            if reply.get("ok").and_then(Value::as_bool) != Some(true) {
                let message = reply
                    .get("error")
                    .and_then(Value::as_str)
                    .unwrap_or("unknown control API error");
                bail!("control API: {message}");
            }
            return Ok(reply);
        }
    }

    pub fn get(&mut self, group: &str, key: &str) -> Result<f64> {
        let reply = self.request(json!({"op": "get", "group": group, "key": key}))?;
        reply
            .get("value")
            .and_then(Value::as_f64)
            .ok_or_else(|| anyhow!("get {group},{key}: reply had no numeric value"))
    }

    pub fn set(&mut self, group: &str, key: &str, value: f64) -> Result<()> {
        self.request(json!({"op": "set", "group": group, "key": key, "value": value}))?;
        Ok(())
    }

    pub fn load(&mut self, deck: u8, path: &str, play: bool) -> Result<()> {
        self.request(json!({"op": "load", "deck": deck, "path": path, "play": play}))?;
        Ok(())
    }

    fn subscribe(&mut self, group: &str, key: &str) -> Result<()> {
        self.request(json!({"op": "subscribe", "group": group, "key": key}))?;
        Ok(())
    }
}

/// Dedicated-connection beat listener: rising edges of `[ChannelN],beat_active`.
pub struct BeatWaiter {
    api: ControlApi,
    group: String,
    last: f64,
}

impl BeatWaiter {
    pub fn new(port: u16, deck: u8) -> Result<Self> {
        let mut api = ControlApi::connect(port)?;
        let group = deck_group(deck);
        api.subscribe(&group, "beat_active")?;
        Ok(Self {
            api,
            group,
            last: 0.0,
        })
    }

    /// Block until the deck's next beat (rising edge). Errors if the read
    /// times out — a stopped deck emits no beats.
    pub fn wait_next_beat(&mut self) -> Result<()> {
        loop {
            let event = self.api.read_json()?;
            if event.get("event").and_then(Value::as_str) != Some("change") {
                continue;
            }
            if event.get("group").and_then(Value::as_str) != Some(self.group.as_str())
                || event.get("key").and_then(Value::as_str) != Some("beat_active")
            {
                continue;
            }
            let value = event.get("value").and_then(Value::as_f64).unwrap_or(0.0);
            let rising = value > 0.5 && self.last <= 0.5;
            self.last = value;
            if rising {
                return Ok(());
            }
        }
    }

    pub fn wait_beats(&mut self, beats: u32) -> Result<()> {
        for _ in 0..beats {
            self.wait_next_beat()?;
        }
        Ok(())
    }
}
