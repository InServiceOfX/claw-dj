"""Interrupted scans recover without stealing a live scanner's state."""
import os
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain import library_index


class ScanRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = Path(self.tmp.name) / 'library.sqlite3'
        library_index._SCHEMA_READY.clear()
        with library_index.connect(self.index) as db:
            db.execute("INSERT INTO roots(path,added_at) VALUES('/music',1)")
            db.execute("INSERT INTO tracks(track_id,root,size_bytes,mtime_ns,title,artist,first_seen_at,last_seen_at) VALUES('/music/song.flac','/music',123,456,'Song','Artist',1,1)")
            db.execute("UPDATE scan_state SET running=1,started_at=100,discovered=4000,processed=0,warnings='keep this warning' WHERE id=1")
            db.commit()

    def seed_pid(self, pid):
        with library_index.connect(self.index) as db:
            db.execute('UPDATE scan_state SET scan_pid=? WHERE id=1', (pid,))
            db.commit()

    def status(self, **kwargs):
        return library_index.scan_status(self.index, **kwargs)

    def legacy_status(self):
        return self.status(scan_worker_alive=False, editor_started_at=200.)

    def test_new_scan_records_its_owner(self):
        with library_index.connect(self.index) as db:
            library_index.begin_scan(db, 0)
        state = self.status()
        self.assertEqual(state['scan_pid'], os.getpid())
        self.assertEqual(state['running'], 1)

    def test_success_and_failure_both_clear_the_owner(self):
        from brain.scan_library import incremental_scan
        music = Path(self.tmp.name) / 'Music'
        music.mkdir()
        incremental_scan([music], index_path=self.index)
        self.assertIsNone(self.status()['scan_pid'])
        self.assertEqual(self.status()['running'], 0)
        with patch('pathlib.Path.rglob', side_effect=PermissionError('cannot list folder')):
            with self.assertRaises(PermissionError):
                incremental_scan([music], index_path=self.index)
        state = self.status()
        self.assertEqual(state['running'], 0)
        self.assertIsNone(state['scan_pid'])
        self.assertIn('cannot list folder', state['error'])

    @unittest.skipUnless(shutil.which('lsof'), 'Legacy ownership checks require lsof')
    def test_real_external_database_holder_protects_legacy_scan(self):
        code = "import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); print('ready',flush=True); sys.stdin.read(); db.close()"
        proc = subprocess.Popen([sys.executable, '-c', code, str(self.index)],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), 'ready')
            with library_index.connect(self.index):
                owners = library_index._database_owners(self.index)
            self.assertIsNotNone(owners)
            self.assertIn(proc.pid, owners)
            self.assertEqual(self.legacy_status()['running'], 1)
        finally:
            proc.communicate('', timeout=5)

    def test_dead_process_is_recovered_without_editor_context(self):
        self.seed_pid(999999)
        with patch.object(library_index, '_pid_alive', return_value=False):
            state = self.status()
        self.assertEqual(state['running'], 0)
        self.assertIsNone(state['scan_pid'])
        self.assertIn('interrupted', state['error'])

    def test_live_foreign_process_is_kept(self):
        self.seed_pid(123456)
        with patch.object(library_index, '_pid_alive', return_value=True):
            self.assertEqual(self.legacy_status()['running'], 1)

    def test_current_editor_with_finished_thread_is_recovered(self):
        self.seed_pid(os.getpid())
        self.assertEqual(self.legacy_status()['running'], 0)

    def test_active_thread_prevents_recovery_even_for_stale_pid(self):
        self.seed_pid(999999)
        with patch.object(library_index, '_pid_alive', return_value=False):
            self.assertEqual(self.status(scan_worker_alive=True, editor_started_at=200.)['running'], 1)

    def test_legacy_record_recovers_only_with_owner_evidence(self):
        with patch.object(library_index, '_database_owners', return_value={os.getpid()}):
            state = self.legacy_status()
        self.assertEqual(state['running'], 0)
        self.assertIsNotNone(state['finished_at'])
        self.assertEqual(state['discovered'], 4000)
        self.assertEqual(state['processed'], 0)
        self.assertEqual(state['warnings'], 'keep this warning')
        self.assertEqual(state['track_count'], 1)
        self.assertEqual(state['roots'], ['/music'])

    def test_another_legacy_scanner_holding_database_prevents_recovery(self):
        with patch.object(library_index, '_database_owners', return_value={os.getpid(), 123456}):
            self.assertEqual(self.legacy_status()['running'], 1)

    def test_unknown_ownership_or_recent_legacy_record_is_not_cleared(self):
        for owners in [None, set(), {123456}]:
            with self.subTest(owners=owners), patch.object(library_index, '_database_owners', return_value=owners):
                self.assertEqual(self.legacy_status()['running'], 1)
        with patch.object(library_index, '_database_owners') as inspect:
            self.assertEqual(self.status()['running'], 1)
            self.assertEqual(self.status(scan_worker_alive=False, editor_started_at=50.)['running'], 1)
            inspect.assert_not_called()

    def test_missing_started_at_is_not_guessed(self):
        with library_index.connect(self.index) as db:
            db.execute('UPDATE scan_state SET started_at=NULL WHERE id=1')
            db.commit()
        self.assertEqual(self.legacy_status()['running'], 1)

    def test_concurrent_new_scan_wins_over_stale_recovery(self):
        def owners(_):
            with library_index.connect(self.index) as db:
                library_index.begin_scan(db, 9000)
            return {os.getpid()}
        with patch.object(library_index, '_database_owners', side_effect=owners):
            state = self.legacy_status()
        self.assertEqual(state['running'], 1)
        self.assertEqual(state['discovered'], 9000)
        self.assertEqual(state['scan_pid'], os.getpid())
        self.assertIsNone(state['error'])

    def test_old_schema_poll_does_not_skip_required_migration(self):
        with library_index.connect(self.index) as db:
            db.execute('ALTER TABLE scan_state DROP COLUMN scan_pid')
            db.commit()
        library_index._SCHEMA_READY.clear()
        self.assertNotIn('scan_pid', self.status())
        self.assertNotIn(str(self.index.resolve()), library_index._SCHEMA_READY)
        with library_index.connect(self.index) as db:
            self.assertIn('scan_pid', {row[1] for row in db.execute('PRAGMA table_info(scan_state)')})

    def test_old_row_can_recover_before_pid_column_is_migrated(self):
        with library_index.connect(self.index) as db:
            db.execute('ALTER TABLE scan_state DROP COLUMN scan_pid')
            db.commit()
        with patch.object(library_index, '_database_owners', return_value={os.getpid()}):
            self.assertEqual(self.legacy_status()['running'], 0)

    def test_busy_writer_is_not_blocked_or_overwritten(self):
        locker = sqlite3.connect(self.index)
        self.addCleanup(locker.close)
        locker.execute('BEGIN IMMEDIATE')
        with patch.object(library_index, '_database_owners', return_value={os.getpid()}):
            self.assertEqual(self.legacy_status()['running'], 1)
        locker.rollback()

    def test_ownership_failure_is_conservative(self):
        for error in [FileNotFoundError(), subprocess.TimeoutExpired('lsof', 2)]:
            with self.subTest(error=error), patch.object(library_index.subprocess, 'run', side_effect=error):
                self.assertEqual(self.legacy_status()['running'], 1)

    def test_editor_passes_its_real_thread_and_start_context(self):
        from brain.playlist_editor import PlaylistApp
        app = object.__new__(PlaylistApp)
        app.collection_error = app.scan_error = app.scan_thread = None
        app.editor_started_at = 200.
        app._collection_index_path = lambda: self.index
        with patch.object(library_index, '_database_owners', return_value={os.getpid()}):
            self.assertEqual(app.ingest_status()['running'], 0)


if __name__ == '__main__':
    unittest.main()
