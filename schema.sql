PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS event_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    event_date TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS game_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    day_id INTEGER NOT NULL,
    capacity INTEGER NOT NULL CHECK(capacity > 0),
    start_time TEXT,
    end_time TEXT,
    UNIQUE(game_id, day_id),
    FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY(day_id) REFERENCES event_days(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_day_id INTEGER NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    class_name TEXT NOT NULL,
    cancel_token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(game_day_id) REFERENCES game_days(id) ON DELETE CASCADE
);

-- Une personne peut s'inscrire à plusieurs jeux,
-- mais le backend interdit deux inscriptions le même jour.
