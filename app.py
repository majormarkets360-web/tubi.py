import os
import streamlit as st
import time
import yaml
from tubi_pluto_capture import TubiPlutoCapture
from clip_generator import ShowClipGenerator
from social_poster import post_to_all_platforms

st.set_page_config(page_title="TubiPluto ClipMaster", layout="wide")

os.makedirs('segments', exist_ok=True)
os.makedirs('clips', exist_ok=True)

@st.cache_resource
def load_config():
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

config = load_config()

# Sidebar
st.sidebar.title("🔗 Social Media Accounts")
twitter_bearer = st.sidebar.text_input("Twitter Bearer Token", type="password")
tiktok_token = st.sidebar.text_input("TikTok Access Token", type="password")
instagram_token = st.sidebar.text_input("Instagram Token", type="password")
youtube_key = st.sidebar.text_input("YouTube API Key", type="password")
auto_post = st.sidebar.checkbox("🚀 Auto-post all clips", value=True)

st.title("📺 Tubi/Pluto TV → Viral 60s Clips Generator")
st.markdown("**Capture segments → Generate 8x 60s clips → Auto-post to social.**")

tab1, tab2, tab3 = st.tabs(["🎬 Capture", "✂️ Generate Clips", "📤 Auto-Post"])

with tab1:
    st.header("1. Capture Show Segment")
    platform = st.radio("Platform", ["Tubi TV", "Pluto TV"])  # FIX: defined at top level of tab1

    if platform == "Tubi TV":
        show_url = st.text_input("Tubi URL", "https://tubitv.com/movies/123456/show-name")
    else:
        channel = st.selectbox("Pluto Channel", ["News", "Movies", "Drama", "Sports", "Reality"])
        show_url = f"https://pluto.tv/live/{channel.lower()}"

    segment_duration = st.slider("Duration (minutes)", 5, 30, 10)

    if st.button("🎥 Capture Segment", type="primary"):
        with st.spinner("Capturing..."):
            try:
                capture = TubiPlutoCapture(show_url, platform, duration=segment_duration * 60)
                segment_path = capture.capture_segment()
                st.session_state.segment_path = segment_path
                st.session_state.platform = platform  # FIX: save platform to session
                st.success(f"✅ Captured: {segment_path}")
                st.video(segment_path)
            except Exception as e:
                st.error(f"Capture failed: {e}")

with tab2:
    st.header("2. Generate 8x 60s Clips")
    if 'segment_path' not in st.session_state:
        st.info("Capture a segment first in Tab 1.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.video(st.session_state.segment_path, caption="Full Segment")
        with col2:
            if st.button("✨ Generate Clips", type="primary"):
                with st.spinner("Analyzing highlights..."):
                    try:
                        generator = ShowClipGenerator(st.session_state.segment_path)
                        clips = generator.generate_multi_clips(num_clips=8, clip_length=60)
                        st.session_state.generated_clips = clips
                        st.success(f"🎉 {len(clips)} clips ready!")
                    except Exception as e:
                        st.error(f"Generation failed: {e}")

    if 'generated_clips' in st.session_state:
        st.subheader("Your Clips")
        cols = st.columns(4)
        for i, path in enumerate(st.session_state.generated_clips):
            with cols[i % 4]:
                st.video(path)
                st.caption(f"Clip #{i+1}")

with tab3:
    st.header("3. Auto-Post")
    if 'generated_clips' not in st.session_state:
        st.info("Generate clips first in Tab 2.")
    elif st.button("📤 Post All Now", type="primary"):
        progress = st.progress(0)
        status = st.empty()
        posted = []
        platform_label = st.session_state.get('platform', 'Tubi TV')  # FIX: use session state

        for i, path in enumerate(st.session_state.generated_clips):
            caption = f"🔥 Must-see moment from {'Tubi' if platform_label=='Tubi TV' else 'Pluto TV'}! #TVClips #Viral"
            if auto_post:
                links = post_to_all_platforms(
                    path, caption,
                    twitter_bearer=twitter_bearer,
                    tiktok_token=tiktok_token,
                    instagram_token=instagram_token,
                    youtube_key=youtube_key
                )
                posted.extend(links)
            progress.progress((i + 1) / len(st.session_state.generated_clips))
            status.text(f"Posted {i+1}/{len(st.session_state.generated_clips)}")

        st.balloons()
        st.success("✅ Done!")
        for link in posted:
            st.markdown(f"- {link}")
