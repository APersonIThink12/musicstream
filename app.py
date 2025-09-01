from flask import Flask, render_template, request, send_file, jsonify, session
import os
import sqlite3
import json
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from yt_dlp import YoutubeDL

app = Flask(__name__)
app.secret_key = os.urandom(24)
executor = ThreadPoolExecutor(max_workers=2)
download_tasks = {}

def init_db():
    with sqlite3.connect('playlists.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                songs TEXT NOT NULL
            )
        ''')

@app.before_request
def before_request():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

@app.route('/')
def index():
    user_folder = Path('music') / session['user_id']
    songs = []
    if user_folder.exists():
        songs = [f.stem for f in user_folder.glob('*.mp3')]
    return render_template('index.html', songs=songs)

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    task_id = str(uuid.uuid4())
    download_tasks[task_id] = {'status': 'pending', 'user_id': session['user_id']}
    executor.submit(download_song, query, task_id)
    return jsonify({'task_id': task_id})

def download_song(query, task_id):
    try:
        user_id = download_tasks[task_id]["user_id"]
        user_folder = os.path.join("music", user_id)
        os.makedirs(user_folder, exist_ok=True)

        # Define paths to both ffmpeg and ffprobe
        ffmpeg_dir = r"C:\ffmpeg\ffmpeg-master-latest-win64-gpl-shared\bin"
        ffmpeg_path = os.path.join(ffmpeg_dir, "ffmpeg.exe")
        ffprobe_path = os.path.join(ffmpeg_dir, "ffprobe.exe")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(user_folder, '%(title)s.%(ext)s'),
            'default_search': 'ytsearch1',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'ffmpeg_location': ffmpeg_dir,  # Point to the directory containing both executables
            'prefer_ffmpeg': True
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            download_tasks[task_id].update({
                'status': 'complete',
                'title': info['title']
            })
    except Exception as e:
        print(f'Download error: {e}')
        download_tasks[task_id]['status'] = 'failed'

@app.route('/download_status/<task_id>')
def download_status(task_id):
    if task_id not in download_tasks:
        return jsonify({'status': 'not_found'})
    
    status = download_tasks[task_id]['status']
    if status == 'complete':
        result = {'status': status}
        download_tasks.pop(task_id)
        return jsonify(result)
    
    return jsonify({'status': status})

@app.route('/play/<song>')
def play_song(song):
    user_folder = Path('music') / session['user_id']
    song_path = user_folder / f'{song}.mp3'
    if song_path.exists():
        return send_file(str(song_path))
    return 'Song not found', 404

@app.route('/playlists')
def view_playlists():
    with sqlite3.connect('playlists.db') as conn:
        playlists = conn.execute(
            'SELECT id, name FROM playlists WHERE user_id = ?',
            (session['user_id'],)
        ).fetchall()
    return render_template('playlists.html', playlists=playlists)

@app.route('/playlist/<int:playlist_id>')
def view_playlist(playlist_id):
    with sqlite3.connect('playlists.db') as conn:
        playlist = conn.execute(
            'SELECT name, songs FROM playlists WHERE id = ? AND user_id = ?',
            (playlist_id, session['user_id'])
        ).fetchone()
    
    if playlist:
        return render_template('playlist.html',
                             playlist_name=playlist[0],
                             songs=json.loads(playlist[1]),
                             playlist_id=playlist_id)
    return redirect(url_for('index'))

@app.route('/playlist/create', methods=['POST'])
def create_playlist():
    name = request.form.get('name')
    if not name:
        return jsonify({'success': False, 'error': 'Name required'})
    
    with sqlite3.connect('playlists.db') as conn:
        conn.execute(
            'INSERT INTO playlists (user_id, name, songs) VALUES (?, ?, ?)',
            (session['user_id'], name, '[]')
        )
    return jsonify({'success': True})

@app.route('/playlist/<int:playlist_id>/add', methods=['POST'])
def add_to_playlist(playlist_id):
    song_name = request.form.get('song_name')
    
    with sqlite3.connect('playlists.db') as conn:
        current_songs = conn.execute(
            'SELECT songs FROM playlists WHERE id = ? AND user_id = ?',
            (playlist_id, session['user_id'])
        ).fetchone()
        
        if current_songs:
            songs = json.loads(current_songs[0])
            if song_name not in songs:
                songs.append(song_name)
                conn.execute(
                    'UPDATE playlists SET songs = ? WHERE id = ?',
                    (json.dumps(songs), playlist_id)
                )
    
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)