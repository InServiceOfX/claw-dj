#!/usr/bin/env python3
"""clawdj bridge server: owns the virtual MIDI port 'clawdj' and relays
commands read from a FIFO into MIDI messages Mixxx receives.

FIFO protocol (one command per line), channel 16 (mido channel=15):
    note <num> [velocity]   -> Note On (velocity default 127)
    cc <num> <value>        -> Control Change
    quit                    -> exit

Example:
    echo "note 2" > /tmp/clawdj.fifo      # play deck 1
    echo "cc 0 64" > /tmp/clawdj.fifo     # crossfader to center
"""
import os
import stat

import mido

FIFO = "/tmp/clawdj.fifo"
CHANNEL = 15  # channel 16, 0-indexed


def _remove_stale_fifo(path: str) -> None:
    if not os.path.lexists(path):
        return
    if not stat.S_ISFIFO(os.stat(path, follow_symlinks=False).st_mode):
        raise RuntimeError(f"refusing to replace non-FIFO path: {path}")
    os.unlink(path)


def main() -> None:
    _remove_stale_fifo(FIFO)
    os.mkfifo(FIFO)
    try:
        with mido.open_output("clawdj", virtual=True) as port:
            print(
                f"virtual port open: {port.name}; reading commands from {FIFO}",
                flush=True,
            )
            while True:
                with open(FIFO) as fifo:  # blocks until a writer connects
                    for line in fifo:
                        parts = line.split()
                        if not parts:
                            continue
                        cmd = parts[0].lower()
                        try:
                            if cmd == "note":
                                num = int(parts[1], 0)
                                vel = int(parts[2], 0) if len(parts) > 2 else 127
                                port.send(
                                    mido.Message(
                                        "note_on",
                                        channel=CHANNEL,
                                        note=num,
                                        velocity=vel,
                                    )
                                )
                                print(f"sent note_on {num} vel {vel}", flush=True)
                            elif cmd == "cc":
                                num = int(parts[1], 0)
                                val = int(parts[2], 0)
                                port.send(
                                    mido.Message(
                                        "control_change",
                                        channel=CHANNEL,
                                        control=num,
                                        value=val,
                                    )
                                )
                                print(f"sent cc {num} val {val}", flush=True)
                            elif cmd == "quit":
                                print("quit", flush=True)
                                return
                            else:
                                print(f"unknown command: {line.strip()}", flush=True)
                        except (IndexError, ValueError) as e:
                            print(f"bad command {line.strip()!r}: {e}", flush=True)
    finally:
        _remove_stale_fifo(FIFO)


if __name__ == "__main__":
    main()
