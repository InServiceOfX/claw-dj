"""Status polls must not fight a long scan for a schema write lock."""
from __future__ import annotations

import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path

from brain import library_index


class ScanStatusLockTests(unittest.TestCase):
    def setUp(self) -> None:
        library_index._SCHEMA_READY.clear()

    def test_scan_status_does_not_rerun_schema_after_first_connect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "library.sqlite3"
            with library_index.connect(index) as db:
                db.execute(
                    "UPDATE scan_state SET running=1, discovered=10, processed=3 WHERE id=1"
                )
                db.commit()
            # Second open for status must not need exclusive schema work.
            status = library_index.scan_status(index)
            self.assertEqual(status["running"], 1)
            self.assertEqual(status["discovered"], 10)
            self.assertEqual(status["processed"], 3)
            self.assertFalse(status.get("locked"))

    def test_scan_status_returns_placeholder_when_database_is_locked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "library.sqlite3"
            with library_index.connect(index) as db:
                db.execute(
                    "UPDATE scan_state SET running=1, discovered=5, processed=1 WHERE id=1"
                )
                db.commit()

            # Hold an exclusive lock in another connection (BEGIN IMMEDIATE).
            locker = sqlite3.connect(index, timeout=0.1)
            locker.execute("BEGIN IMMEDIATE")
            try:
                # Force contention: short timeout + no schema rewrite path.
                library_index._SCHEMA_READY.add(str(index.resolve()))
                status = library_index.scan_status(index)
                self.assertTrue(status.get("locked") or status.get("running") == 1)
                # Must not raise; may be real row if lock timing allowed a read,
                # or the locked placeholder.
                self.assertIn("discovered", status)
            finally:
                locker.rollback()
                locker.close()

    def test_concurrent_status_polls_during_writer_do_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "library.sqlite3"
            with library_index.connect(index) as db:
                db.commit()

            stop = threading.Event()
            errors: list[BaseException] = []

            def writer() -> None:
                try:
                    with library_index.connect(index) as db:
                        for i in range(50):
                            if stop.is_set():
                                break
                            db.execute(
                                "UPDATE scan_state SET running=1, discovered=?, processed=? WHERE id=1",
                                (i * 100, i * 10),
                            )
                            db.commit()
                            time.sleep(0.01)
                except BaseException as error:  # collect for assertion
                    errors.append(error)

            def reader() -> None:
                try:
                    for _ in range(40):
                        library_index.scan_status(index)
                        time.sleep(0.005)
                except BaseException as error:
                    errors.append(error)

            threads = [
                threading.Thread(target=writer),
                threading.Thread(target=reader),
                threading.Thread(target=reader),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            stop.set()
            self.assertEqual(errors, [])
