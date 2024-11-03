import sqlite3
from ytmusicapi import YTMusic
from flask import Flask, render_template, request, redirect, url_for, jsonify
import yt_dlp

ytmusic = YTMusic("oauth.json")
app = Flask(__name__)



@app.route('/', methods=['POST', 'GET'])
def main():
    if request.method == 'POST':
        videoId = request.form.get('id')
        if not videoId:
            videoId = request.form.get('id_library')
        if not videoId:
            videoId = request.form.get("id_next")
        title = request.form.get('title')
        if not title:
            title = request.form.get('title_library')
        if not title:
            title = request.form.get('title_next')
        thumbnail = request.form.get('thumbnail')
        con = sqlite3.connect("songs.db")
        cursor = con.cursor()

        cursor.execute('SELECT * FROM songs WHERE videoid = ?', (videoId,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO songs (videoid, title)
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
def next_song():
    con = sqlite3.connect("songs.db")
    con.row_factory = sqlite3.Row
    cursor = con.cursor()
    results = cursor.execute("SELECT title, videoid FROM songs").fetchall()
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
    albums = ytmusic.get_library_albums(limit=24)
    return render_template('libraries.html', albums=albums)




@app.route('/delete', methods=['POST'])
def delete():
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    cursor.execute("DELETE FROM songs")
    con.commit()
    con.close()
    return render_template("next.html")
    




if __name__ == '__main__':
    app.run(debug=True)


