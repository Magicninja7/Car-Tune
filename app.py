import sqlite3
from ytmusicapi import YTMusic
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session
import requests
import yt_dlp
import json
import os
import re
from builtins import zip
from openai import OpenAI
from flask_socketio import SocketIO, send
import anthropic
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user


ytmusic = YTMusic("browser.json")
app = Flask(__name__)




app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'




'''
This module provides a Flask web application for interacting with YouTube Music. It allows users to search for songs,
play videos, view library albums, and manage a local SQLite database of songs.
Modules:
    sqlite3: A module for interacting with SQLite databases.
    ytmusicapi: A module for interacting with YouTube Music API.
    flask: A micro web framework for Python.
    yt_dlp: A module for downloading videos from YouTube and other video platforms.
Functions:
    main(): Handles the main route for the web application. Processes both GET and POST requests.
    play(): Handles the '/play/' route to play a video. Retrieves video details and generates a streaming URL.
    get_streaming_url(video_id): Generates a streaming URL for a given video ID using yt_dlp.
    search(): Handles the '/search' route to search for songs on YouTube Music.
    next_song(): Handles the '/next' route to display the next song from the local database.
    hihihiha(): Handles the '/songs_albums' route to display songs from a specific album.
    libraries(): Handles the '/libraries' route to display the user's library albums.
    delete(): Handles the '/delete' route to delete all songs from the local database.
Templates:
    search.html: Template for the search page.
    main.html: Template for the main video playback page.
    next.html: Template for displaying the next song.
    songs_albums.html: Template for displaying songs from a specific album.
    libraries.html: Template for displaying library albums.
'''

downloaded = []

song_queue = []
def get_songs_in_queue():
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    songs_in_queue = cursor.execute("SELECT videoid, title FROM songs").fetchall()
    con.close()
    return songs_in_queue

i = 1
songs_in_queue = get_songs_in_queue()
for videoid, title in songs_in_queue:
    song_queue.append({
        "videoid": videoid,
        "title": title,
        "index": i
    })
    i += 1
current_song = len(song_queue) - 1 if len(song_queue) > 0 else 0


@app.route('/', methods=['POST', 'GET'])
@login_required
def main():
    if request.method == 'POST':
        videoId = request.form.get('id') or request.form.get('id_library') or request.form.get("id_next")
        title = request.form.get('title') or request.form.get('title_library') or request.form.get('title_next')
        thumbnail = request.form.get('thumbnail')
        place = request.form.get("place_next")
        

        global current_song

        if not place:
            current_song = len(song_queue) - 1
            con = sqlite3.connect("songs.db")
            cursor = con.cursor()

            cursor.execute('''
                INSERT INTO songs (videoid, title)
                VALUES (?, ?)
            ''', (videoId, title))
            con.commit()
            con.close()

            current_song += 1
            song_queue.append({
                "videoid": videoId,
                "title": title,
                "index": current_song
            })
        else:
            current_song = int(place)  

        #stats beggining
        con = sqlite3.connect("songs.db")
        cursor = con.cursor()
        data = cursor.execute("SELECT listened FROM stats WHERE email = ?", (current_user.email,)).fetchone()
        if data is None or data[0] is None:
            listened = 1
        else:
            listened = int(data[0]) + 1
        cursor.execute("UPDATE stats SET listened = ? WHERE email = ?", (listened, current_user.email))

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key is None:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0,
            system="Given a song title, give what mood the song is in. Return only the mood of the song.",
            messages=[
                {
                    "role": "user", 
                    "content": [{"type": "text", "text": title}]
                }
            ]
        )
        mood = message.content[0].text

        # Ensure that 'listened' has a value before inserting
        listened = 0  # or any appropriate default value
        cursor.execute("INSERT INTO stats (moods, email, listened) VALUES (?, ?, ?)", (mood, current_user.email, listened))
        con.commit()
        con.close()
        #stats end

        
        return redirect(url_for('play', videoId=videoId, title=title, thumbnail=thumbnail, index=current_song))
    
    return render_template('search.html')



@app.route('/play/')
@login_required
def play():
    videoId = request.args.get('videoId')
    title = request.args.get('title')
    index = request.args.get('index')
    video_details = ytmusic.get_song(videoId)["videoDetails"]
    if video_details.get("thumbnail") and video_details["thumbnail"].get("thumbnails"):
        thumbnail = video_details["thumbnail"]["thumbnails"][-1]["url"]
    else:
        microformat = ytmusic.get_song(videoId)["microformat"]["microformatDataRenderer"]
        if microformat.get("thumbnail") and microformat["thumbnail"].get("thumbnails"):
            thumbnail = microformat["thumbnail"]["thumbnails"][-1]["url"]
    streaming_url = get_streaming_url(videoId) if videoId else None
    

    return render_template('main.html', 
                           videoId=videoId, 
                           streaming_url=streaming_url,
                           title=title,
                           thumbnail=thumbnail,
                           index=index)

def get_streaming_url(video_id):
    url = f"https://music.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url'] if 'url' in info else None
    return audio_url




@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    results = []
    thumbnails = []
    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            results = ytmusic.search(query, filter="songs")
            for song in results:
                videoId = song.get("videoId")
                if videoId:
                    video_details = ytmusic.get_song(videoId).get("videoDetails", {})
                    thumbnail = video_details.get("thumbnail", {}).get("thumbnails", [])
                    if thumbnail:
                        thumbnails.append(thumbnail[-1]["url"])
                    else:
                        thumbnails.append('')
                else:
                    thumbnails.append('')
    return render_template('search.html', results=results, thumbnails=thumbnails, zip=zip)


@app.route('/next', methods=['GET'])
@login_required
def next_song():
    con = sqlite3.connect("songs.db")
    con.row_factory = sqlite3.Row
    cursor = con.cursor()
    results = cursor.execute("SELECT title, videoid FROM songs").fetchall()
    con.close()
    results_with_thumbnails = []
    for i in results:
        videoId = i["videoid"]
        video_details = ytmusic.get_song(videoId)["videoDetails"]
        if video_details.get("thumbnail") and video_details["thumbnail"].get("thumbnails"):
            thumbnail = video_details["thumbnail"]["thumbnails"][-1]["url"]
        else:
            microformat = ytmusic.get_song(videoId)["microformat"]["microformatDataRenderer"]
            if microformat.get("thumbnail") and microformat["thumbnail"].get("thumbnails"):
                thumbnail = microformat["thumbnail"]["thumbnails"][-1]["url"]
            else:
                thumbnail = ''
        y = 1
        results_with_thumbnails.append({
            "title": i["title"],
            "videoid": videoId,
            "thumbnail": thumbnail,
            "place": y
        })
        
    return render_template('next.html', results=results_with_thumbnails)




@app.route('/songs_albums', methods=['POST', 'GET'])
@login_required
def hihihiha():
    songs = []
    if request.method == 'POST':
        browse_id = request.form.get('hihihiha')       
        try:
            album_details = ytmusic.get_album(browse_id)
            
            if "tracks" in album_details:
                songs = album_details["tracks"]
        except Exception as e:
            songs = []
    
    return render_template('songs_albums.html', songs=songs)




@app.route('/libraries', methods=["GET"])
@login_required
def libraries():
    albums = ytmusic.get_library_albums(limit=24)
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name != 'songs'
        AND name != 'stats'
        AND name != 'login'
        AND name != 'ids'
    """)
    tables = cursor.fetchall()
    table_names = [table[0] for table in tables]
    select_queries = [f"SELECT videoid, title FROM {table}" for table in table_names]
    combined_query = " UNION ALL ".join(select_queries)
    cursor.execute(combined_query)
    results = cursor.fetchall()
    con.commit()
    con.close()


    return render_template('libraries.html', table_names=table_names, albums=albums)




@app.route('/delete', methods=['POST'])
@login_required
def delete():
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    cursor.execute("DELETE FROM songs")
    con.commit()
    con.close()
    return redirect("/next") 

@app.route('/delete_next', methods=['POST'])
@login_required
def delete_next():
    song = request.form.get('id_delete')
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    cursor.execute("DELETE FROM songs WHERE videoid = ?", (song,))
    con.commit()
    con.close()
    return redirect("/next") 

@app.route('/add_playlist', methods=['POST'])
@login_required
def add_playlist():
    playlist_name = request.form.get('playlist_name')
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    create_table_query = f"""
    CREATE TABLE {playlist_name} (
        place INTEGER PRIMARY KEY,
        videoid INTEGER NOT NULL,
        title TEXT NOT NULL
    );
    """
    cursor.execute(create_table_query)
    con.commit()
    con.close()
    return redirect("/libraries")

@app.route('/songs_playlists', methods=['POST', 'GET'])
@login_required
def wrrr():
    results_with_thumbnails = []
    if request.method == 'POST':
        playlist_name = request.form.get('wrrr')
        con = sqlite3.connect("songs.db")
        cursor = con.cursor()
        cursor.execute(f"SELECT videoid, title FROM {playlist_name}")
        results = cursor.fetchall()
        con.close()
        for i in results:
            videoId = i[0]
            title_data = i[1]

            try:
                video_details = ytmusic.get_song(videoId)["videoDetails"]
                if video_details.get("thumbnail") and video_details["thumbnail"].get("thumbnails"):
                    thumbnail = video_details["thumbnail"]["thumbnails"][-1]["url"]
                else:
                    microformat = ytmusic.get_song(videoId)["microformat"]["microformatDataRenderer"]
                    if microformat.get("thumbnail") and microformat["thumbnail"].get("thumbnails"):
                        thumbnail = microformat["thumbnail"]["thumbnails"][-1]["url"]
                    else:
                        thumbnail = ''
            except KeyError:
                thumbnail = ''
    
            results_with_thumbnails.append({
            "title": title_data,
            "videoid": videoId,
            "thumbnail": thumbnail,
            "playlist_name": playlist_name
        })
    videoId_rick = ytmusic.search('Never Gonna Give You Up', filter="songs")[0]['videoId']
    streaming_url_rick = get_streaming_url(videoId_rick)

    return render_template('songs_playlists.html', songs=results_with_thumbnails, rick_astley=streaming_url_rick)



@app.route('/play_playlist', methods=['POST'])
@login_required
def play_playlist():
    playlist_name = request.form.get('playlist_name_play')
    song_data = request.form.get('song_name_play')
    try:
        song = json.loads(song_data)
        title = song.get('title')
        videoId = song.get('videoid')
    except json.JSONDecodeError:
        print('Invalid song data format')
        return redirect('/libraries')
    
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    try:
        cursor.execute(f"INSERT INTO {playlist_name} (videoid, title) VALUES (?, ?)", (videoId, title))
    except sqlite3.OperationalError:
        print('Table doesn\'t exist')
    con.commit()
    con.close()
    return redirect('/libraries')


@app.route('/delete_playlist', methods=['POST'])
@login_required
def del_playlist():
    playlist_name = request.form.get('playlist_delete_playlist')
    videoid = request.form.get('id_delete_playlist')
    valid_playlist_names = ["Focus"]
    if playlist_name not in valid_playlist_names:
        return "Invalid playlist name", 400 
    query = f"DELETE FROM {playlist_name} WHERE videoid = ?"
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    cursor.execute(query, (videoid,))
    con.commit()
    con.close()
    
    return redirect('/libraries')





@app.route('/forward_song', methods=['POST'])
@login_required
def forward_song():
    global current_song
    current_song += 1
    if current_song > len(song_queue):
        current_song = len(song_queue)
    return redirect(url_for('play', videoId=song_queue[current_song-1]["videoid"], title=song_queue[current_song-1]["title"]))


@app.route('/previous_song', methods=['POST'])
@login_required
def previous_song():
    global current_song 
    current_song -= 1
    if current_song < 0:
        current_song = 1
    return redirect(url_for('play', videoId=song_queue[current_song-1]["videoid"], title=song_queue[current_song-1]["title"]))








ids = []
con = sqlite3.connect('songs.db')
con.row_factory = sqlite3.Row  # Enable dictionary-like access
cursor = con.cursor()

# Execute the query
cursor.execute("SELECT videoid, title, thumbnail FROM ids")
rows = cursor.fetchall()

# Populate ids with dictionaries
ids = []
for row in rows:
    ids.append({
        "videoid": row["videoid"],
        "title": row["title"],
        "thumbnail": row["thumbnail"]
    })
con.commit()
con.close()



@app.route('/download', methods=['POST'])
@login_required
def download():
    global ids
    output_dir = os.path.join(os.getcwd(), "downloads")
    print(ids)
    print(output_dir)

    videoid = request.form.get('videoid_d')
    title = request.form.get('title_d')
    url = get_streaming_url(videoid) if videoid else None

    if not url:
        return "URL not provided", 400
    if videoid not in [item['videoid'] for item in ids]:
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                output_path = os.path.join(output_dir, f"{videoid}.mp3")
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        f.write(chunk)
                video_details = ytmusic.get_song(videoid)["videoDetails"]
                if video_details.get("thumbnail") and video_details["thumbnail"].get("thumbnails"):
                    thumbnail = video_details["thumbnail"]["thumbnails"][-1]["url"]
                else:
                    microformat = ytmusic.get_song(videoid)["microformat"]["microformatDataRenderer"]
                    if microformat.get("thumbnail") and microformat["thumbnail"].get("thumbnails"):
                        thumbnail = microformat["thumbnail"]["thumbnails"][-1]["url"]
                ids.append({
                    "videoid": videoid,
                    "title": title,
                    "thumbnail": thumbnail
                })

                con = sqlite3.connect("songs.db")
                cursor = con.cursor()
                cursor.execute('''
                    INSERT INTO ids (videoid, title, thumbnail)
                    VALUES (?, ?, ?)
                ''', (videoid, title, thumbnail))
                con.commit()
                con.close()
                break  # Exit the retry loop if successful
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == retries - 1:
                    return "Failed to download the file after multiple attempts", 500
    return redirect('/show_downloads')



@app.route('/show_downloads', methods=['GET'])
@login_required
def show_downloads():
    global ids
    return render_template('list_downloads.html', ids=ids)





@app.route('/play_downloads', methods=['POST', 'GET'])
@login_required
def play_downloads():
    global ids
    output_dir = os.path.join(os.getcwd(), "downloads")
    files = os.listdir(output_dir)
    videoid = request.form.get('id_download')
    title = request.form.get('title_download')

    for file in files:
        if os.path.splitext(file)[0] == videoid:
            chosen_song = file
            break

    for i in ids:
        if i['videoid'] == videoid:
            thumbnail = i['thumbnail']

    return render_template('play_downloads.html', ids=ids, chosen_song=chosen_song, title=title, videoid=videoid, thumbnail=thumbnail)



@app.route('/downloads/<filename>')
@login_required
def download_file(filename):
    return send_from_directory('downloads', filename)






@app.route('/chatgpt', methods=['POST', 'GET'])
@login_required
def chatgpt():
    if request.method == 'POST':
        user_i =  request.form.get('chat_gpt_input')


    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key is None:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        temperature=0,
        system="You are a music suggestion model. For the user input, please suggest a song, album or podcast that you think the user would like. Return only the title of the song/album/podcast. The content shouls be available on YT Music.",
        messages=[
            {
                "role": "user", 
                "content": [{"type": "text", "text": user_i}]
            }
        ]
    )

    suggestion = message.content[0].text
    return render_template('search.html', response=suggestion)


#session
class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('songs.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, email FROM login WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return User(id=user[0], email=user[1])
    return None


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        
        conn = sqlite3.connect('songs.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM login WHERE email = ?", (email,))
        rows = cursor.fetchall()
        
        if len(rows) > 0:
            return render_template("register.html", error="Email used")
        if len(password) < 8:
            return render_template("register.html", error="Password must contain at least 8 characters")
        if password != confirm:
            return render_template("register.html", error="Passwords do not match")
        
        cursor.execute("INSERT INTO login (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = sqlite3.connect('songs.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password FROM login WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user is None:
            return render_template("login.html", error="Email not found")
        if user[2] != password:
            return render_template("login.html", error="Password incorrect")

        user_obj = User(id=user[0], email=user[1])
        login_user(user_obj)
        return redirect('/')

    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
#end session


















#add websockets for live comments
#radio via https://pypi.org/project/radios/
#reccomendation system, based on last played songs
#context aware - suggest music based on user location; time of day; weather; etc

#dynamic theme, based on music
#music while browsing in website
#soundscape integration (rain, fireplace, thunderstorm, (sounds) etc)

#help suggest music and create playlist etc (ai)
#mood and lyric tracking, for better suggestions (ai)
#equalizer (maybe with ai)
#album art generator (ai)
#audio analasis (python + ai)



if __name__ == '__main__':
    app.run(debug=True)


 