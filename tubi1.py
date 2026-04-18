import cv2
import numpy as np
import time
import whisper
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


class ShowClipGenerator:
    def __init__(self, segment_path):
        self.segment_path = segment_path
        self.segment = VideoFileClip(segment_path)
        self.model = whisper.load_model("base")
        # paddleocr removed — not compatible with Python 3.12+

    def generate_multi_clips(self, num_clips=8, clip_length=60):
        clips = []
        total_duration = self.segment.duration

        # Audio peaks
        audio = self.segment.audio.to_soundarray()
        audio_mono = np.abs(audio[:, 0])
        threshold = np.percentile(audio_mono, 92)
        peaks = np.where(audio_mono > threshold)[0]

        # Scene change detection only (no OCR)
        cap = cv2.VideoCapture(self.segment_path)
        scene_changes = []
        frame_idx = 0
        prev_gray = None

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % 30 == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    if np.mean(diff) > 25:
                        scene_changes.append(frame_idx / self.segment.fps)
                prev_gray = gray
            frame_idx += 1
        cap.release()

        # Build highlight times safely
        arrays = []
        if len(peaks) >= num_clips:
            arrays.append(peaks[::max(1, len(peaks) // num_clips)] / self.segment.fps)
        if scene_changes:
            arrays.append(np.array(scene_changes))

        if arrays:
            highlight_times = np.unique(np.concatenate(arrays))
        else:
            highlight_times = np.linspace(0, max(0, total_duration - clip_length), num_clips)

        for i in range(num_clips):
            idx = int(i * len(highlight_times) / num_clips)
            start_time = max(0, highlight_times[idx] - 10)
            end_time = min(total_duration, start_time + clip_length)

            if end_time - start_time < 5:
                continue

            clip = self.segment.subclip(start_time, end_time)
            clip = self.add_overlay(clip, f"EPIC MOMENT #{i+1}")

            out_path = f"clips/show_clip_{int(time.time())}_{i}.mp4"
            clip.write_videofile(out_path, verbose=False, logger=None)
            clips.append(out_path)
            clip.close()

        self.segment.close()
        return clips

    def add_overlay(self, clip, text):
        try:
            txt_clip = (TextClip(text, fontsize=50, color='yellow',
                                 stroke_color='black', font='Impact')
                        .set_position(('center', 0.1), relative=True)
                        .set_duration(clip.duration)
                        .crossfadein(0.5)
                        .crossfadeout(0.5))
            return CompositeVideoClip([clip, txt_clip])
        except Exception:
            return clip
