import yt_dlp
from moviepy.editor import VideoFileClip

class TubiPlutoCapture:
    def __init__(self, url, platform, duration=600):
        self.url = url
        self.platform = platform
        self.duration = duration

    def capture_segment(self):
        if self.platform == "Tubi TV":
            ydl_opts = {
                'format': 'best[ext=mp4]',
                'outtmpl': 'segments/tubi_%(title)s.%(ext)s',
            }
        else:
            ydl_opts = {
                'format': 'best',
                'outtmpl': 'segments/pluto_%(uploader)s_%(id)s.%(ext)s',
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=True)
            video_path = ydl.prepare_filename(info)

        video = VideoFileClip(video_path)
        trimmed = video.subclip(0, min(self.duration, video.duration))
        out_path = video_path.rsplit('.', 1)[0] + '_segment.mp4'
        trimmed.write_videofile(out_path, verbose=False, logger=None)
        video.close()
        trimmed.close()
        return out_path
