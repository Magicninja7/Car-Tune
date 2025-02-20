import sqlite3
from ytmusicapi import YTMusic
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session
import requests
import yt_dlp
import json
import re
from builtins import zip
from openai import OpenAI
from flask_socketio import SocketIO, emit
import anthropic
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import numpy as np
import scipy.signal as signal
import soundfile as sf
import os



ytmusic = YTMusic("browser.json")
app = Flask(__name__)




app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

socketio = SocketIO(app)


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
        data = cursor.execute("SELECT listened FROM stats WHERE email = ?", (current_user.email,)).fetchall()
        if data:
            listened = max(map(int, [row[0] for row in data])) + 1
        else:
            listened = 1

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key is None:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0,
            system="Given a song title and its videoid (to identify it more precisely), give what mood the song is in. Return only the mood of the song. If you don't know the song, return 'neutral'.",
            messages=[
                {
                    "role": "user", 
                    "content": [{"type": "text", "text": f'Title: "{title}", Id: "{videoId}"'}]
                }
            ]
        )
        mood = message.content[0].text


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
    albums = ''
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
        system="You are a music suggestion model. For the user input, please suggest a song, album or podcast that you think the user would like. Return only the title of the song/album/podcast. The content shouls be available on YT Music. Return only the title. No author.",
        messages=[
            {
                "role": "user", 
                "content": [{"type": "text", "text": user_i}]
            }
        ]
    )

    suggestion = message.content[0].text
    return search_for_ai(suggestion)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_for_ai(query):
    results = []
    thumbnails = []
    if request.method == 'POST':
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

#socket
@app.route('/comments')
@login_required
def comments_page():
    username = current_user.email
    return render_template('comments.html', username=username)


@socketio.on('send_comment')
@login_required
def handle_comment(data):
    comment = data['comment']
    username = current_user.email
    emit('receive_comment', {'username': username, 'comment': comment}, broadcast=True)
#endsocket

#radio
@app.route('/radio')
@login_required
def radio():
    stations = [
        {"name": "EskaRock (Warsaw)", "url": "https://waw.ic.smcdn.pl/5380-1.mp3"},
        {"name": "BBC radio 1 (UK)", "url": "https://as-hls-ww.live.cf.md.bbci.co.uk/pool_904/live/ww/bbc_radio_one/bbc_radio_one.isml/bbc_radio_one-audio%3d96000.norewind.m3u8"},
        {"name": "NPR Illanois (central USA)", "url": "http://war.str3am.com:7780/wuis.mp3"},
        {"name": "Radio ZET (Poland)", "url": "https://playerservices.streamtheworld.com/api/livestream-redirect/RADIO_ZET.mp3"},
        {"name": "RMF FM (Poland)", "url": "https://rmf-live-01.cdn.eurozet.pl/rmf_fm"},
        {"name": "India Today (India)", "url": "https://cdnstream1.com/4529_128_2.mp3"},
        {"name": "WGNA (ALbany)", "url": "https://live.amperwave.net/direct/townsquare-wgnafmmp3-ibc3.mp3&source=ts-tunein"},
        {"name": "RMF classic (Poland)", "url": "http://www.rmfon.pl/rmfclassic.pls"},
    ]
    return render_template('radio.html', stations=stations)

@app.route('/radio/play', methods=['POST'])
def play_radio():
    station_url = request.json.get('url')
    if not station_url:
        return jsonify({"error": "No station URL provided"}), 400
    return jsonify({"message": "Playing station", "url": station_url})
#endradio



#stats
@app.route('/stats', methods=['POST'])
@login_required
def stats():
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    data = cursor.execute("SELECT moods, listened FROM stats WHERE email = ?", (current_user.email,)).fetchall()
    dat = cursor.execute("SELECT listened FROM stats WHERE email = ?", (current_user.email,)).fetchall()
    if dat:
        listened = max(map(int, [row[0] for row in dat]))
    else:
        return render_template('stats.html', data='no data')
    con.close()


    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key is None:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        temperature=0,
        system="You will be given the amount of listened songs, and you need to return what songs mood does the user like listening to. Return also your explenation, but in a user-friendly way, so he can understand it. The explanation should start with '#'. Dont use '#' anywhere else. Good luck!",
        messages=[
            {
                "role": "user", 
                "content": [{"type": "text", "text": data}]
            }
        ]
    )
    stat = message.content[0].text
    exp = 0
    status = False
    for i in stat:
        if i == '#':
            status = True
            continue
        if status == True:
            exp += i
        else:
            mood += i

    return render_template('stats.html', mood=stat, exp=exp, listened=listened)
#endstats

#ai
@app.route('/ai', methods=['GET', 'POST'])
@login_required
def ai_sugg():
    if request.method == 'GET':
        a = 'Grenade'
        b = [('Count on me', 'Bruno Mars'), ('Understand', 'BoyWithUke'), ('Holiday', 'Green Day'), ('Boulevard of broken dreams', 'Green Day')]
        c = 'https://oaidalleapiprodscus.blob.core.windows.net/private/org-nkdO4LrG4s9ckJRvy7geYZuU/user-iUtxn47ufVWicYETk7ZChkLJ/img-wQBlfxSlnG738yuEsP9jSjlp.png?st=2024-12-20T12%3A58%3A04Z&se=2024-12-20T14%3A58%3A04Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=d505667d-d6c1-4a0a-bac7-5c84a87759f8&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2024-12-20T00%3A31%3A50Z&ske=2024-12-21T00%3A31%3A50Z&sks=b&skv=2024-08-04&sig=WrX6wysCh7ufL5ZNOtItxKIaClYfDiTbJ90QuhXU5xA%3D'
        return render_template('ai.html', recc_s=a, album=b, album_img=c, zip=zip)

    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    dat = cursor.execute("SELECT listened FROM stats WHERE email = ?", (current_user.email,)).fetchall()
    con.close()
    if dat:
        listened = max(map(int, [row[0] for row in dat]))
        bracket = listened - 10
    else:
        bracket = 0

    def recc_song(bracket):
        con = sqlite3.connect("songs.db")
        cursor = con.cursor()
        data = cursor.execute("SELECT moods, title FROM stats WHERE email = ? AND listened > ?", (current_user.email, bracket)).fetchall()
        con.close()
        # API key and client setup
        api_key = os.getenv("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0,
            system="Based on the mood and title of songs, give a recommendation of a song that the user would like. Return only the title of the song, and its author. Remember, title AND author Divide them by a '#'.",
            messages=[{"role": "user", "content": [{"type": "text", "text": data}]}],
        )
        return message.content[0].text

    def create_album():
        con = sqlite3.connect("songs.db")
        cursor = con.cursor()
        data = cursor.execute("SELECT moods, title FROM stats WHERE email = ?", (current_user.email,)).fetchall()
        con.close()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0,
            system="Based on the mood and title of songs, song recommendations that the user would like. Return 20 - 30 song titles, divided by #. Return the titles of the songs, and their authors. Remember, title AND author.",
            messages=[{"role": "user", "content": [{"type": "text", "text": data}]}],
        )
        return message.content[0].text

    def album_image(songs):
        client = OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"A album cover for a album with these songs: {songs}. The album photo should be based on on one of these artistic trends: surrealism, minimalism, Art Nouveau, Digital Art/Glitch Art, Geometric Abstraction.",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url

    recc_s = recc_song(bracket)
    album = create_album()
    album_parts = album.split('#')
    songs = album_parts[0::2]
    artists = album_parts[1::2]
    album_tuple = (songs, artists)
    album_img = album_image(album)

    return render_template('ai.html', recc_s=recc_s, album=album_tuple, album_img=album_img, zip=zip)
#endai


#addaiplaylist
@app.route('/add_ai', methods=['POST'])
@login_required
def addai():
    album = request.form.get('album')
    songs = album[0]
    artists = album[1]    

    print(songs)
    print(artists)
    playlist_name = request.form.get('playlist_name')
    videoid = []
    for title, artist in album:
        query = f"{title} {artist}"
        results = ytmusic.search(query, filter="songs")
        o = results[0]['videoId']
        videoid.append(o)

    full_album = songs, artists, videoid

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

    for a, b, c in full_album:
        cursor.execute(f"INSERT INTO {playlist_name} (videoid, title) VALUES (?, ?)", (b, a))
    con.commit()
    con.close()
    return redirect("/libraries")
#endaddaiplaylist



if __name__ == '__main__':
    socketio.run(app, debug=True)


 