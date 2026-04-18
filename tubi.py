
import streamlit as st
import asyncio
import threading
import time
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
import whisper
import paddleocr
import torch
import yt_dlp
import requests
import yaml
import re
from tubi_pluto_capture import TubiPlutoCapture
from clip_generator import ShowClipGenerator
from social_poster import post_to_all_platforms

st.set_page_config(page_title="TubiPluto ClipMaster", layout="wide")
torch.backends.cudnn.benchmark = True

# Config load
@st.cache_resource
def load_config():
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

config = load_config()
os.makedirs('segments', exist_ok=True)
os.makedirs('clips', exist_ok=True)

# Sidebar: Social Accounts
st.sidebar.title("🔗 Social Media Accounts")
twitter_bearer = st.sidebar.text_input("Twitter API Bearer Token", type="password")
tiktok_token = st.sidebar.text_input("TikTok Access Token", type="password")
instagram_token = st.sidebar.text_input("Instagram Token", type="password")
youtube_key = st.sidebar.text_input("YouTube API Key", type="password")

auto_post = st.sidebar.checkbox("🚀 Auto-post all clips", value=True)

# Main UI
st.title("📺 Tubi/Pluto TV → Viral 60s Clips Generator")
st.markdown("**Capture show segments → Generate 8x 60s highlight clips → Auto-post to social media.**")

tab1, tab2, tab3 = st.tabs(["🎬 Capture Segment", "✂️ Generate Clips", "📤 Auto-Post"])

with tab1:
    st.header("1. Capture Tubi/Pluto Show Segment")
   
    platform = st.radio("Platform", ["Tubi TV", "Pluto TV"])
   
    if platform == "Tubi TV":
        st.info("📺 Tubi: https://tubitv.com/ - Free movies/TV shows")
        show_url = st.text_input("Tubi Show/Movie URL",
            "https://tubitv.com/movies/123456/show-name")  # Example
    else:
        st.info("🌌 Pluto: https://pluto.tv/ - Live TV channels")
        channel = st.selectbox("Pluto Channel",
            ["News", "Movies", "Drama", "Sports", "Reality"])  # Map to IDs
        show_url = f"https://pluto.tv/live/{channel.lower()}"
   
    segment_duration = st.slider("Record Duration (minutes)", 5, 30, 10)
   
    if st.button("🎥 Capture Show Segment", type="primary"):
        with st.spinner("Capturing live/free content..."):
            capture = TubiPlutoCapture(show_url, platform, duration=segment_duration*60)
            segment_path = capture.capture_segment()
           
            st.session_state.segment_path = segment_path
            st.success(f"✅ Segment captured: {segment_path} ({segment_duration}min)")
            st.video(segment_path)

with tab2:
    st.header("2. Generate 8x 60-Second Highlight Clips")
   
    if 'segment_path' in st.session_state:
        col1, col2 = st.columns(2)
       
        with col1:
            st.video(st.session_state.segment_path, caption="Full Segment")
       
        with col2:
            if st.button("✨ AI Analyze & Generate Clips", type="primary"):
                with st.spinner("🤖 Detecting highlights: drama, action, cliffhangers..."):
                    generator = ShowClipGenerator(st.session_state.segment_path)
                    clips = generator.generate_multi_clips(num_clips=8, clip_length=60)
                   
                    st.session_state.generated_clips = clips
                    st.success(f"🎉 Generated {len(clips)} viral-ready 60s clips!")
   
    if 'generated_clips' in st.session_state:
        st.subheader("📹 Your 60s Clips")
        clip_cols = st.columns(4)
        for i, clip_path in enumerate(st.session_state.generated_clips):
            with clip_cols[i%4]:
                st.video(clip_path, format="video/mp4")
                st.caption(f"Clip #{i+1}")

with tab3:
    st.header("3. 🚀 Auto-Post to Social Media")
   
    if 'generated_clips' in st.session_state and st.button("📤 Post All Clips Now", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
       
        posted_links = []
        for i, clip_path in enumerate(st.session_state.generated_clips):
            caption = f"🔥 Must-see moment from {'Tubi' if platform=='Tubi TV' else 'Pluto TV'}! #TVClips #Viral #AI"
           
            if auto_post:
                links = post_to_all_platforms(
                    clip_path, caption,
                    twitter_bearer=twitter_bearer,
                    tiktok_token=tiktok_token,
                    instagram_token=instagram_token,
                    youtube_key=youtube_key
                )
                posted_links.extend(links)
           
            progress_bar.progress((i+1)/len(st.session_state.generated_clips))
            status_text.text(f"Posted clip {i+1}/{len(st.session_state.generated_clips)}")
       
        st.balloons()
        st.success("✅ All clips auto-posted!")
        for link in posted_links:
            st.markdown(f"**Posted:** {link}")

# Core Modules

# tubi_pluto_capture.py
class TubiPlutoCapture:
    def __init__(self, url, platform, duration=600):
        self.url = url
        self.platform = platform
        self.duration = duration
   
    def capture_segment(self):
        if self.platform == "Tubi TV":
            # Tubi HLS m3u8 extraction
            ydl_opts = {
                'format': 'best[ext=mp4]',
                'outtmpl': 'segments/tubi_%(title)s.%(ext)s',
            }
        else:  # Pluto
            ydl_opts = {
                'format': 'hls-6000',  # High quality HLS
                'outtmpl': 'segments/pluto_%(uploader)s_%(id)s.%(ext)s',
            }
       
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=True)
            video_path = ydl.prepare_filename(info)
       
        # Trim to exact duration if needed
        clip = VideoFileClip(video_path).subclip(0, min(self.duration, VideoFileClip(video_path).duration))
        out_path = video_path.replace('.mp4', '_segment.mp4')
        clip.write_videofile(out_path, verbose=False, logger=None)
        clip.close()
        return out_path

# clip_generator.py
class ShowClipGenerator:
    def __init__(self, segment_path):
        self.segment = VideoFileClip(segment_path)
        self.model = whisper.load_model("base")
        self.ocr = paddleocr.PaddleOCR(use_angle_cls=True)
   
    def generate_multi_clips(self, num_clips=8, clip_length=60):
        clips = []
       
        # 1. Audio peaks (dramatic music/dialogue)
        audio = self.segment.audio.to_soundarray()
        peaks = np.where(np.abs(audio[:,0]) > np.percentile(np.abs(audio), 92))[0]
       
        # 2. Scene changes + text detection (titles, subtitles)
        cap = cv2.VideoCapture(self.segment_path)
        scene_changes = []
        text_scenes = []
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
           
            # Scene change detection
            if frame_idx % 30 == 0:  # Every second
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if hasattr(self, 'prev_gray'):
                    diff = cv2.absdiff(gray, self.prev_gray)
                    if np.mean(diff) > 25:
                        scene_changes.append(frame_idx / self.segment.fps)
                self.prev_gray = gray
               
                # OCR for subtitles/titles
                ocr_result = self.ocr.ocr(frame, cls=True)
                if ocr_result and ocr_result[0]:
                    text_scenes.append(frame_idx / self.segment.fps)
           
            frame_idx += 1
       
        # Generate evenly spaced + peak-focused clips
        total_duration = self.segment.duration
        highlight_times = np.unique(np.concatenate([peaks[::len(peaks)//num_clips],
                                                   scene_changes, text_scenes]))
       
        for i in range(num_clips):
            start_time = max(0, highlight_times[i*len(highlight_times)//num_clips] - 10)
            end_time = min(total_duration, start_time + clip_length)
           
            clip = self.segment.subclip(start_time, end_time)
           
            # Add dynamic caption overlay
            clip = self.add_showy_overlay(clip, f"EPIC MOMENT #{i+1}")
           
            out_path = f"clips/show_clip_{int(time.time())}_{i}.mp4"
            clip.write_videofile(out_path, verbose=False, logger=None)
            clips.append(out_path)
            clip.close()
       
        self.segment.close()
        return clips
   
    def add_showy_overlay(self, clip, text):
        # Animated text overlay + graphics
        txt_clip = TextClip(text, fontsize=50, color='yellow', stroke_color='black', font='Impact')
        txt_clip = txt_clip.set_position(('center', 0.1)).set_duration(clip.duration)
        txt_clip = txt_clip.crossfadein(1).crossfadeout(1)
       
        return CompositeVideoClip([clip, txt_clip.set_fps(clip.fps)])
