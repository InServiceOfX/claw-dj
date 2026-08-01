from __future__ import annotations

import unittest

from hands.mixxx_control import (
    MixxxControlUnavailable,
    discover_mixxx_control_port,
    mixxx_listener_ports,
    mixxx_process_ids,
    plan_control_port,
)


class MixxxControlPortTest(unittest.TestCase):
    def test_process_and_owned_listener_candidates(self) -> None:
        ps = "  12 /Applications/Mixxx.app/Contents/MacOS/Mixxx /Applications/Mixxx.app/Contents/MacOS/Mixxx\n  99 python python worker.py\n"
        self.assertEqual(mixxx_process_ids(ps_output=ps), [12])
        lsof = "p12\nn127.0.0.1:10443\nn*:8787\n"
        self.assertEqual(mixxx_listener_ports(12, lsof_output=lsof), [8787, 10443])

    def test_discovers_validated_non_default_owned_listener(self) -> None:
        probed: list[int] = []

        def probe(port: int) -> bool:
            probed.append(port)
            return port == 10443

        port = discover_mixxx_control_port(
            preferred=9995,
            process_ids=[12],
            listener_lookup=lambda _pid: [8787, 10443],
            probe=probe,
        )
        self.assertEqual(port, 10443)
        self.assertEqual(probed, [9995, 8787, 10443])

    def test_does_not_accept_arbitrary_open_listener(self) -> None:
        with self.assertRaises(MixxxControlUnavailable):
            discover_mixxx_control_port(
                process_ids=[12],
                listener_lookup=lambda _pid: [8787],
                probe=lambda _port: False,
            )

    def test_explicit_override_is_only_candidate(self) -> None:
        probed: list[int] = []
        port = discover_mixxx_control_port(
            preferred=9995,
            explicit=12001,
            process_ids=[12],
            listener_lookup=lambda _pid: [10443],
            probe=lambda candidate: probed.append(candidate) is None and candidate == 12001,
        )
        self.assertEqual(port, 12001)
        self.assertEqual(probed, [12001])

    def test_plan_metadata_port(self) -> None:
        self.assertEqual(
            plan_control_port({"runtime": {"mixxx_control_port": 10443}}),
            10443,
        )
        self.assertIsNone(plan_control_port({}))


if __name__ == "__main__":
    unittest.main()
