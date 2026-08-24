from pathlib import Path

from shadowlearn.database import Database


def test_database_initializes_and_survives_reopen(tmp_path: Path):
    path = tmp_path / "shadowing.db"
    database = Database(path)
    database.initialize()
    database.execute(
        "INSERT INTO generations(id,title,raw_text,normalized_text,engine,settings_json,status,created_at,updated_at) VALUES ('one','Title','Text','Text','system','{}','complete','now','now')"
    )
    reopened = Database(path)
    reopened.initialize()
    assert reopened.fetch_one("SELECT title FROM generations WHERE id='one'")["title"] == "Title"


def test_backup_passes_integrity_check():
    database = Database()
    database.initialize()
    backup = database.create_backup()
    assert backup["integrity_ok"] is True
    assert Path(backup["path"]).is_file()

