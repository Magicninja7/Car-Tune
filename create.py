import sqlite3

conn = sqlite3.connect('songs.db')
cursor = conn.cursor()

create_table_query = """
CREATE TABLE songs (
    place INTEGER PRIMARY KEY,
    videoid INTEGER NOT NULL,
    title TEXT NOT NULL
);
"""

cursor.execute(create_table_query)

conn.commit()
conn.close()
