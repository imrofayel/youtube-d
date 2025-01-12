from flask import Flask, render_template, request, jsonify, send_file
from download_video import download_youtube_video, download_youtube_music
import os
import glob

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    try:
        video_url = request.form.get('video_url')
        format_type = request.form.get('format')
        
        if not video_url:
            return jsonify({'message': 'Please provide a video URL'}), 400

        # Create DOWNLOADS directory if it doesn't exist
        downloads_dir = os.path.join(os.getcwd(), 'DOWNLOADS')
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
            
        # Get initial list of files
        initial_files = set(glob.glob(os.path.join(downloads_dir, '**/*.*'), recursive=True))
            
        # Download the video
        if format_type == 'mp3':
            download_youtube_music(video_url)
        else:
            download_youtube_video(video_url)
        
        # Get new list of files and find the newly added file
        new_files = set(glob.glob(os.path.join(downloads_dir, '**/*.*'), recursive=True))
        added_files = new_files - initial_files
        
        if not added_files:
            return jsonify({'message': 'Download failed'}), 500
            
        # Get the downloaded file (should be only one)
        downloaded_file = list(added_files)[0]
        
        # Send the file to browser
        return send_file(
            downloaded_file,
            as_attachment=True,
            download_name=os.path.basename(downloaded_file)
        )
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
