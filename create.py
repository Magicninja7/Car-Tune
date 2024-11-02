import sqlite3

# Connect to the database (or create it if it doesn’t exist)
conn = sqlite3.connect('songs.db')
cursor = conn.cursor()

# SQL command to create the 'contacts' table
create_table_query = """
CREATE TABLE songs (
    place INTEGER PRIMARY KEY,
    videoid INTEGER NOT NULL,
    title TEXT NOT NULL
);
"""

# Execute the command to create the table
cursor.execute(create_table_query)

# Commit the changes and close the connection
conn.commit()
conn.close()
