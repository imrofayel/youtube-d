from flask import Flask, render_template, request, jsonify, send_file, Response
import os
import glob
import json
from yt_dlp import YoutubeDL
import re
import time
import zipfile
import shutil

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

def cleanup_downloads():
    downloads_dir = os.path.join(os.getcwd(), 'DOWNLOADS')
    if os.path.exists(downloads_dir):
        for file in os.listdir(downloads_dir):
            file_path = os.path.join(downloads_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

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
    # Clean any leftover files before starting
    cleanup_downloads()
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
        # Clean any leftover files before starting new download
        cleanup_downloads()
        
        video_url = request.form.get('video_url')
        format_type = request.form.get('format')
        quality = request.form.get('quality')
        
        if not video_url:
            return jsonify({'message': 'Please provide a video URL'}), 400

        # Create DOWNLOADS directory if it doesn't exist
        downloads_dir = os.path.join(os.getcwd(), 'DOWNLOADS')
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)

        # Set up progress hook and options
        app.progress_hook = ProgressHook()
        
        if format_type == 'mp4':
            format_str = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best[ext=mp4]'
        else:
            format_str = f'bestaudio[abr<={quality}]'
        
        ydl_opts = {
            'format': format_str,
            'progress_hooks': [app.progress_hook],
            'outtmpl': os.path.join(downloads_dir, '%(playlist_index)s - %(title).200s.%(ext)s'),
            'quiet': True,
            'restrictfilenames': True,
            'windowsfilenames': True,
            'merge_output_format': 'mp4' if format_type == 'mp4' else None,
            'nooverwrites': True,
            'no_color': True,
            'ignoreerrors': True,
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
            
            # Check if it's a playlist
            playlist_title = info.get('playlist_title', 'Downloads')
            
        # Find all downloaded files
        files = os.listdir(downloads_dir)
        if not files:
            return jsonify({'message': 'Download failed'}), 500
        
        # Create zip file if multiple files (playlist)
        if len(files) > 1:
            # Create zip file
            zip_filename = os.path.join(downloads_dir, f"{sanitize_filename(playlist_title)}.zip")
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    file_path = os.path.join(downloads_dir, file)
                    if os.path.isfile(file_path):
                        zipf.write(file_path, arcname=file)
            
            # Send zip file
            response = send_file(
                zip_filename,
                as_attachment=True,
                download_name=os.path.basename(zip_filename)
            )
        else:
            # Send single file
            downloaded_file = os.path.join(downloads_dir, files[0])
            safe_filename = sanitize_filename(os.path.basename(downloaded_file))
            
            response = send_file(
                downloaded_file,
                as_attachment=True,
                download_name=safe_filename
            )
        
        # Wait a moment to ensure file is sent
        time.sleep(1)
        
        # Clean up files
        cleanup_downloads()
        
        return response
    
    except Exception as e:
        print(f"Error: {str(e)}")
        cleanup_downloads()  # Clean up on error
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
