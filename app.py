import sqlite3
from ytmusicapi import YTMusic
from flask import Flask, render_template, request, redirect, url_for, jsonify
import yt_dlp

ytmusic = YTMusic("oauth.json")
app = Flask(__name__)



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
        results_with_thumbnails.append({
            "title": i["title"],
            "videoid": videoId,
            "thumbnail": thumbnail
        })
        
    return render_template('next.html', results=results_with_thumbnails)




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
    return redirect("/next") 

@app.route('/delete_next', methods=['POST'])
def delete_next():
    song = request.form.get('id_delete')
    con = sqlite3.connect("songs.db")
    cursor = con.cursor()
    cursor.execute("DELETE FROM songs WHERE videoid = ?", (song,))
    con.commit()
    con.close()
    return redirect("/next") 



if __name__ == '__main__':
    app.run(debug=True)


