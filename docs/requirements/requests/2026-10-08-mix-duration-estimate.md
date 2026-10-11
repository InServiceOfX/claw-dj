# Estimated total mix play time

Ernest requests that `./scripts/run_mix.sh` show an estimate of the total play
time of the mix plan it is about to play. A rough estimate within five to ten
minutes is sufficient; exact timing is unnecessary.

Print the estimate in the startup plan summary, including dry runs. Estimate
the full plan even with `--max-events`. Use planned excerpts and transition
beats at the planned tempos, or the last clip end for simultaneous performance
timelines. Do not sum overlapping clip lengths or whole original song lengths.
Round to minutes and show hours for longer mixes. Estimation reads plan JSON
only and does not connect to Mixxx, load audio, or change the plan.

Scope: conventional brownfield `scripts/run_mix.sh` and a pure helper in
`hands/mix_duration.py`; neither is mapped to a PDD prompt/architecture unit.
