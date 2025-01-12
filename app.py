from flask import Flask, render_template, request, jsonify, send_file, Response
import os
import glob
import json
from yt_dlp import YoutubeDL
import re

app = Flask(__name__)

def sanitize_filename(filename):
    # Remove invalid characters and trim spaces
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip()
    # Ensure filename is not too long
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    return name + ext

class ProgressHook:
    def __init__(self):
        self.progress = 0
        
    def __call__(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes')
            downloaded_bytes = d.get('downloaded_bytes')
            if total_bytes and downloaded_bytes:
                self.progress = (downloaded_bytes / total_bytes) * 100

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/progress')
def progress():
    def generate():
        while True:
            if hasattr(app, 'progress_hook'):
                yield f"data: {json.dumps({'progress': app.progress_hook.progress})}\n\n"
            else:
                yield f"data: {json.dumps({'progress': 0})}\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download', methods=['POST'])
def download():
    try:
        video_url = request.form.get('video_url')
        format_type = request.form.get('format')
        quality = request.form.get('quality')
        
        if not video_url:
            return jsonify({'message': 'Please provide a video URL'}), 400

        # Create DOWNLOADS directory if it doesn't exist
        downloads_dir = os.path.join(os.getcwd(), 'DOWNLOADS')
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
            
        # Get initial list of files
        initial_files = set(glob.glob(os.path.join(downloads_dir, '**/*.*'), recursive=True))

        # Set up progress hook and options
        app.progress_hook = ProgressHook()
        
        if format_type == 'mp4':
            format_str = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best[ext=mp4]'
        else:
            format_str = f'bestaudio[abr<={quality}]'
        
        ydl_opts = {
            'format': format_str,
            'progress_hooks': [app.progress_hook],
            'outtmpl': os.path.join(downloads_dir, '%(title).200s.%(ext)s'),
            'quiet': True,
            'restrictfilenames': True,
            'windowsfilenames': True,
            'merge_output_format': 'mp4' if format_type == 'mp4' else None,
        }
        
        # Add format-specific options
        if format_type == 'mp3':
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality,
                }],
            })
        else:
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            })
        
        # Download the video/audio
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_title = info.get('title', 'video')
        
        # Get new list of files and find the newly added file
        new_files = set(glob.glob(os.path.join(downloads_dir, '**/*.*'), recursive=True))
        added_files = new_files - initial_files
        
        if not added_files:
            return jsonify({'message': 'Download failed'}), 500
            
        # Get the downloaded file (should be only one)
        downloaded_file = list(added_files)[0]
        
        # Ensure the filename is valid
        safe_filename = sanitize_filename(os.path.basename(downloaded_file))
        
        # Send the file to browser
        return send_file(
            downloaded_file,
            as_attachment=True,
            download_name=safe_filename
        )
    
    except Exception as e:
        print(f"Error: {str(e)}")  # Add logging for debugging
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
