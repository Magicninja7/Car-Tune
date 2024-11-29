import sqlite3
'''
This script creates a SQLite database named 'songs.db' and defines a table called 'songs'.
The 'songs' table has the following columns:
- place: INTEGER, primary key
- videoid: INTEGER, not null
- title: TEXT, not null
Steps performed:
1. Connect to the SQLite database 'songs.db'. If the database does not exist, it will be created.
2. Create a cursor object to interact with the database.
3. Define a SQL query to create the 'songs' table with the specified columns.
4. Execute the SQL query to create the table.
5. Commit the transaction to save the changes.
6. Close the connection to the database.
'''


conn = sqlite3.connect('songs.db')
cursor = conn.cursor()

create_table_query = """
CREATE TABLE login (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    password TEXT NOT NULL
);
"""

cursor.execute(create_table_query)

conn.commit()
conn.close()
