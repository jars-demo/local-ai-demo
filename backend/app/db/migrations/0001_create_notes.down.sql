-- Irreversible for data: dropping the table deletes every note. `python -m app.db.migrate down`
-- asks for --yes before it runs this.
DROP TABLE notes;
