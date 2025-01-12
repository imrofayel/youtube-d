from flask import Flask, render_template, request, jsonify
from download_video import download_youtube_video, download_youtube_music
import os

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
        if not os.path.exists('DOWNLOADS'):
            os.makedirs('DOWNLOADS')

        # Download the video
        if format_type == 'mp3':
            download_youtube_music(video_url)
        else:
            download_youtube_video(video_url)
        
        return jsonify({'message': 'Download completed successfully'}), 200
    
    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
