import sqlite3
from ytmusicapi import YTMusic
from flask import Flask, render_template, request, redirect, url_for
import yt_dlp

ytmusic = YTMusic("oauth.json")
app = Flask(__name__)



@app.route('/', methods=['POST', 'GET'])
def main():
    if request.method == 'POST':
        videoId = request.form.get('id')
        if not videoId:
            videoId = request.form.get('id_library')
        elif not videoId:
            videoId = request.form.get("id_next")
        title = request.form.get('title')
        if not title:
            title = request.form.get('title_library')
        elif not title:
            title = request.form.get('title_next')
        thumbnail = request.form.get('thumbnail')
        con = sqlite3.connect("songs.db")
        cursor = con.cursor()

        cursor.execute('SELECT * FROM contacts WHERE videoid = ?', (videoId,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO contacts (videoid, title)
                VALUES (?, ?)
            ''', (videoId, title))
        con.commit()
        con.close()
        
        return redirect(url_for('play', videoId=videoId, title=title, thumbnail=thumbnail))
    
    return render_template('search.html')

@app.route('/play/')
def play():
    videoId = request.args.get('videoId')
    title = request.args.get('title')
    thumbnail = request.args.get('thumbnail')
    streaming_url = get_streaming_url(videoId) if videoId else None
    return render_template('main.html', 
                           videoId=videoId, 
                           streaming_url=streaming_url,
                           title=title,
                           thumbnail=thumbnail)

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
def search():
    results = []
    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            results = ytmusic.search(query, filter="songs")
    return render_template('search.html', results=results)

@app.route('/next', methods=['GET', 'POST'])
def next():
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    results = cursor.execute("SELECT title, videoid FROM contacts").fetchall()
    con.close()
    return render_template('next.html', results=results)




@app.route('/songs_albums', methods=['POST', 'GET'])
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
def libraries():
    albums = ytmusic.get_library_albums()
    # Debug print
    if albums:
        print("First album data:", albums[0].keys())
    return render_template('libraries.html', albums=albums)



@app.route('/delete', methods=['POST'])
def delete():
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    cursor.execute("DELETE FROM contacts")
    con.commit()
    con.close()
    return render_template("next.html")
    


if __name__ == '__main__':
    app.run(debug=True)


