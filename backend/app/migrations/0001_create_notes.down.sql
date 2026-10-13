-- Irreversible for data: dropping the table deletes every note. `python -m app.migrate down`
-- asks for --yes before it runs this.
DROP TABLE notes;
