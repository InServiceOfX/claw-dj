use std::{
    env,
    path::{Path, PathBuf},
    time::Duration,
};

use anyhow::{Context, Result, anyhow};
use rusqlite::{Connection, OpenFlags, OptionalExtension, params};
use tracing::info;

use crate::command::Deck;

pub const QUEUE_NAME: &str = "__clawdj_queue";
const MIX_DB_ENV: &str = "CLAWDJ_MIXXX_DB";

#[must_use]
pub fn default_mixxx_db_path() -> PathBuf {
    if let Ok(path) = env::var(MIX_DB_ENV) {
        return PathBuf::from(path);
    }

    let home = env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."));

    if cfg!(target_os = "macos") {
        return home.join(
            "Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/mixxxdb.sqlite",
        );
    }

    if let Some(xdg_data_home) = env::var_os("XDG_DATA_HOME") {
        return PathBuf::from(xdg_data_home).join("Mixxx/mixxxdb.sqlite");
    }

    home.join(".local/share/Mixxx/mixxxdb.sqlite")
}

pub fn open_mixxx_database(path: &Path) -> Result<Connection> {
    let connection = Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_URI,
    )
    .with_context(|| format!("failed to open Mixxx database at {}", path.display()))?;

    connection
        .pragma_update(None, "journal_mode", "WAL")
        .context("failed to enable WAL mode")?;
    connection
        .busy_timeout(Duration::from_millis(5_000))
        .context("failed to set SQLite busy timeout")?;

    Ok(connection)
}

pub fn queue_init(connection: &Connection) -> Result<i64> {
    ensure_queue_playlist(connection)
}

pub fn queue_set(connection: &Connection, deck: Deck, track_id: i64) -> Result<()> {
    let playlist_id = ensure_queue_playlist(connection)?;
    let transaction = connection
        .unchecked_transaction()
        .context("failed to start queue_set transaction")?;

    transaction
        .execute(
            "DELETE FROM PlaylistTracks WHERE playlist_id = ?1",
            params![playlist_id],
        )
        .context("failed to clear existing queue entries")?;
    transaction
        .execute(
            "INSERT INTO PlaylistTracks (playlist_id, track_id, position, pl_datetime_added)
             VALUES (?1, ?2, 0, CURRENT_TIMESTAMP)",
            params![playlist_id, track_id],
        )
        .context("failed to insert queue track")?;
    transaction
        .execute(
            "UPDATE Playlists SET date_modified = CURRENT_TIMESTAMP WHERE id = ?1",
            params![playlist_id],
        )
        .context("failed to update queue playlist timestamp")?;
    transaction.commit().context("failed to commit queue_set")?;

    info!(
        deck = deck.as_u8(),
        track_id, "updated __clawdj_queue row 0"
    );
    Ok(())
}

pub fn queue_clear(connection: &Connection) -> Result<()> {
    let playlist_id = ensure_queue_playlist(connection)?;
    let transaction = connection
        .unchecked_transaction()
        .context("failed to start queue_clear transaction")?;

    transaction
        .execute(
            "DELETE FROM PlaylistTracks WHERE playlist_id = ?1",
            params![playlist_id],
        )
        .context("failed to clear queue rows")?;
    transaction
        .execute(
            "UPDATE Playlists SET date_modified = CURRENT_TIMESTAMP WHERE id = ?1",
            params![playlist_id],
        )
        .context("failed to update queue playlist timestamp")?;
    transaction
        .commit()
        .context("failed to commit queue_clear")?;

    Ok(())
}

fn ensure_queue_playlist(connection: &Connection) -> Result<i64> {
    if let Some(id) = lookup_queue_playlist(connection)? {
        return Ok(id);
    }

    connection
        .execute(
            "INSERT INTO Playlists (name, position, hidden, date_created, date_modified, locked)
             VALUES (
                ?1,
                COALESCE((SELECT MAX(position) + 1 FROM Playlists), 0),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                0
             )",
            params![QUEUE_NAME],
        )
        .context("failed to create __clawdj_queue playlist")?;

    lookup_queue_playlist(connection)?
        .ok_or_else(|| anyhow!("__clawdj_queue playlist was not found after creation"))
}

fn lookup_queue_playlist(connection: &Connection) -> Result<Option<i64>> {
    connection
        .query_row(
            "SELECT id FROM Playlists WHERE name = ?1 LIMIT 1",
            params![QUEUE_NAME],
            |row| row.get(0),
        )
        .optional()
        .context("failed to query __clawdj_queue playlist")
}

#[cfg(test)]
mod tests {
    use std::{
        fs,
        path::PathBuf,
        sync::atomic::{AtomicU64, Ordering},
        time::{SystemTime, UNIX_EPOCH},
    };

    use rusqlite::Connection;

    use super::{QUEUE_NAME, open_mixxx_database, queue_clear, queue_init, queue_set};
    use crate::command::Deck;

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    #[test]
    fn queue_commands_only_touch_owned_playlist_rows() {
        let fixture_path = temp_db_path("fixture");
        let path = temp_db_path("copy");
        initialize_test_database(&fixture_path);
        fs::copy(&fixture_path, &path).unwrap();

        {
            let connection = open_mixxx_database(&path).unwrap();
            let playlist_id = queue_init(&connection).unwrap();
            queue_set(&connection, Deck::One, 1).unwrap();

            let row: (i64, i64, i64) = connection
                .query_row(
                    "SELECT playlist_id, track_id, position FROM PlaylistTracks WHERE playlist_id = ?1",
                    [playlist_id],
                    |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
                )
                .unwrap();

            assert_eq!(row, (playlist_id, 1, 0));
            assert_eq!(
                connection
                    .query_row::<String, _, _>(
                        "SELECT name FROM Playlists WHERE id = ?1",
                        [playlist_id],
                        |row| row.get(0),
                    )
                    .unwrap(),
                QUEUE_NAME
            );
            assert_eq!(
                connection
                    .query_row::<i64, _, _>("SELECT COUNT(*) FROM library", [], |row| row.get(0),)
                    .unwrap(),
                1
            );
            assert_eq!(
                connection
                    .query_row::<i64, _, _>("SELECT COUNT(*) FROM track_locations", [], |row| row
                        .get(0),)
                    .unwrap(),
                1
            );

            queue_clear(&connection).unwrap();
            assert_eq!(
                connection
                    .query_row::<i64, _, _>(
                        "SELECT COUNT(*) FROM PlaylistTracks WHERE playlist_id = ?1",
                        [playlist_id],
                        |row| row.get(0),
                    )
                    .unwrap(),
                0
            );
        }

        let _ = fs::remove_file(fixture_path);
        let _ = fs::remove_file(path);
    }

    fn temp_db_path(label: &str) -> PathBuf {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let suffix = COUNTER.fetch_add(1, Ordering::Relaxed);
        std::env::temp_dir().join(format!(
            "clawdj-mixxx-test-{label}-{timestamp}-{suffix}.sqlite"
        ))
    }

    fn initialize_test_database(path: &PathBuf) {
        let connection = Connection::open(path).unwrap();
        connection
            .execute_batch(
                "
                CREATE TABLE Playlists (
                    id INTEGER PRIMARY KEY,
                    name varchar(48),
                    position INTEGER,
                    hidden INTEGER DEFAULT 0 NOT NULL,
                    date_created datetime,
                    date_modified datetime,
                    locked INTEGER DEFAULT 0
                );
                CREATE TABLE PlaylistTracks (
                    id INTEGER PRIMARY KEY,
                    playlist_id INTEGER REFERENCES library_old(id),
                    track_id INTEGER REFERENCES library_old(id),
                    position INTEGER,
                    pl_datetime_added
                );
                CREATE TABLE library_old (id INTEGER PRIMARY KEY, title TEXT);
                CREATE TABLE library (id INTEGER PRIMARY KEY, title TEXT);
                CREATE TABLE track_locations (id INTEGER PRIMARY KEY, location TEXT);
                INSERT INTO library_old (id, title) VALUES (1, 'seed');
                INSERT INTO library (id, title) VALUES (1, 'seed');
                INSERT INTO track_locations (id, location) VALUES (1, '/tmp/test.mp3');
                ",
            )
            .unwrap();
    }
}
