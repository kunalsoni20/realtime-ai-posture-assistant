import os
import time
import tempfile
import cv2
import numpy as np
import pandas as pd
import streamlit as st

import database as db
from processor import ExerciseVideoProcessor
from voice_coach import CoachLLM, TextToSpeech

# 1. Page Configuration & Modern Dark UI Theme Setup
st.set_page_config(
    page_title="AI Gym Coach & Posture Assistant",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inject Custom Styles & Fonts (Neon Emerald #10b981 & Cyan #06b6d4)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* Metric HUD Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        margin-bottom: 12px;
    }
    .metric-label {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        color: #f8fafc;
    }
    .metric-value-emerald {
        color: #10b981;
        text-shadow: 0 0 16px rgba(16, 185, 129, 0.4);
    }
    .metric-value-cyan {
        color: #06b6d4;
        text-shadow: 0 0 16px rgba(6, 182, 212, 0.4);
    }
    
    /* Posture Feedback Status Badges */
    .status-badge-good {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid #10b981;
        color: #10b981;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1rem;
        text-align: center;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.25);
    }
    .status-badge-warning {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid #ef4444;
        color: #ef4444;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1rem;
        text-align: center;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.25);
        animation: pulseWarning 1.5s infinite;
    }
    @keyframes pulseWarning {
        0%, 100% { box-shadow: 0 0 5px rgba(239, 68, 68, 0.3); }
        50% { box-shadow: 0 0 18px rgba(239, 68, 68, 0.6); }
    }

    /* AI Coach Card */
    .coach-box {
        background: linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
        border: 1px solid rgba(6, 182, 212, 0.3);
        border-radius: 12px;
        padding: 16px;
        margin-top: 12px;
    }
</style>
""", unsafe_allow_html=True)

# 3. Session State Initialization
if "user" not in st.session_state:
    st.session_state["user"] = db.get_or_create_user("Athlete_Kunal", "Muscle Building", "Intermediate")
if "processor" not in st.session_state:
    st.session_state["processor"] = ExerciseVideoProcessor()
if "coach_llm" not in st.session_state:
    st.session_state["coach_llm"] = CoachLLM()
if "is_running" not in st.session_state:
    st.session_state["is_running"] = False
if "session_start_time" not in st.session_state:
    st.session_state["session_start_time"] = None
if "last_voice_feedback" not in st.session_state:
    st.session_state["last_voice_feedback"] = ""
if "last_rep_count" not in st.session_state:
    st.session_state["last_rep_count"] = 0

processor = st.session_state["processor"]
coach = st.session_state["coach_llm"]

# 4. Sidebar: User Profile & Session Defaults
with st.sidebar:
    st.title("🏋️ AI Gym Coach")
    st.caption("Real-Time Posture Correction & Rep Counter")
    st.markdown("---")

    # User Profile / Login Form UI
    st.subheader("👤 Athlete Profile")
    curr_user = st.session_state["user"]
    with st.expander(f"Logged in as: **{curr_user['username']}**", expanded=False):
        new_username = st.text_input("Username", value=curr_user["username"])
        new_goal = st.selectbox(
            "Primary Goal",
            ["Muscle Building", "Posture Improvement", "Weight Loss", "Endurance"],
            index=["Muscle Building", "Posture Improvement", "Weight Loss", "Endurance"].index(curr_user.get("goal", "Muscle Building"))
        )
        new_level = st.selectbox(
            "Fitness Level",
            ["Beginner", "Intermediate", "Advanced"],
            index=["Beginner", "Intermediate", "Advanced"].index(curr_user.get("fitness_level", "Intermediate"))
        )
        if st.button("Save Profile", use_container_width=True):
            st.session_state["user"] = db.get_or_create_user(new_username, new_goal, new_level)
            st.success("Profile saved!")
            st.rerun()

    # Session Defaults & Exercise Selection
    st.subheader("⚙️ Workout Configuration")
    exercise_display_names = {
        "bicep_curls": "💪 Bicep Curls",
        "squats": "🦵 Squats",
        "pushups": "🤸 Push-ups"
    }
    selected_exercise_key = st.selectbox(
        "Select Exercise",
        options=list(exercise_display_names.keys()),
        format_func=lambda x: exercise_display_names[x]
    )

    if selected_exercise_key != processor.current_key:
        processor.set_exercise(selected_exercise_key)
        st.session_state["last_rep_count"] = 0

    target_reps = st.slider("Target Goal (Reps)", min_value=5, max_value=50, value=10, step=1)

    # Video Source Selector
    st.subheader("📹 Video Source")
    video_source_mode = st.radio(
        "Source Mode",
        ["Live Webcam", "Upload Video File", "Cloud Simulation Demo"],
        index=2, # Default to Demo so Streamlit Cloud loads instantly without permissions
        help="Use Cloud Demo mode on cloud servers where webcam hardware may be restricted."
    )

    uploaded_video_file = None
    if video_source_mode == "Upload Video File":
        uploaded_video_file = st.file_uploader("Upload MP4/MOV Video", type=["mp4", "mov", "avi"])

    # AI Voice Coaching Settings
    st.subheader("🎙️ AI Voice Feedback")
    enable_voice = st.checkbox("Enable Audio Voice Coach", value=True)
    openai_key = st.text_input("OpenAI API Key (Optional)", type="password", help="Leave blank to use built-in expert sports science LLM persona.")
    if openai_key and openai_key != coach.api_key:
        coach.api_key = openai_key

    st.markdown("---")
    st.caption("Authored by Kunal Soni • Real-Time AI Workout Assistant")

# 5. Main Dashboard Tabs
tab_arena, tab_analytics, tab_guide = st.tabs([
    "🏋️ Live Workout Arena",
    "📊 Session History & Analytics",
    "📐 Biomechanics & Angle Spec"
])

# ==========================================
# TAB 1: LIVE WORKOUT ARENA
# ==========================================
with tab_arena:
    col_main, col_stats = st.columns([7, 3])

    with col_main:
        # Pre-workout briefing
        briefing = coach.get_pre_workout_briefing(
            processor.detector.name,
            st.session_state["user"].get("goal", "Muscle Building"),
            st.session_state["user"].get("fitness_level", "Intermediate")
        )
        st.info(f"💡 **Coach Advice:** {briefing}")

        # Stream / Video Placeholder
        video_placeholder = st.empty()

        # Workout Control Action Bar
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            start_btn = st.button("▶ Start Workout", use_container_width=True, type="primary", disabled=st.session_state["is_running"])
        with col_btn2:
            stop_btn = st.button("⏹ Finish & Log", use_container_width=True, disabled=not st.session_state["is_running"])
        with col_btn3:
            reset_btn = st.button("↺ Reset Reps", use_container_width=True)

        if reset_btn:
            processor.reset_reps()
            st.session_state["last_rep_count"] = 0
            st.toast("Reps reset to 0!")

        if start_btn:
            st.session_state["is_running"] = True
            st.session_state["session_start_time"] = time.time()
            st.toast("Workout session started!")
            st.rerun()

        if stop_btn:
            st.session_state["is_running"] = False
            duration = int(time.time() - (st.session_state["session_start_time"] or time.time()))
            reps = processor.detector.reps
            accuracy = processor.detector.get_accuracy_score()
            warnings = processor.detector.warning_count
            calories = round(reps * 0.45, 1)

            analysis = coach.get_post_workout_analysis(
                processor.detector.name, reps, target_reps, accuracy, warnings
            )

            # Log into SQLite Database
            db.log_workout(
                user_id=st.session_state["user"]["id"],
                exercise=processor.detector.name,
                reps=reps,
                target_reps=target_reps,
                accuracy_score=accuracy,
                warnings_count=warnings,
                duration_seconds=duration,
                calories_burned=calories,
                coach_feedback=analysis
            )

            st.balloons()
            st.success(f"🎉 **Session Logged to SQLite!** {reps} reps completed with {accuracy}% accuracy ({calories} kcal burned).")
            st.markdown(f"**AI Coach Summary:** {analysis}")

            # Audio voiceover for final analysis
            if enable_voice:
                audio_buf = TextToSpeech.synthesize(analysis)
                if audio_buf:
                    st.audio(audio_buf, format="audio/mp3", autoplay=True)

    with col_stats:
        st.subheader("⚡ Live Telemetry")
        
        rep_col, stage_col = st.columns(2)
        with rep_col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Completed Reps</div>
                <div class="metric-value metric-value-emerald">{processor.detector.reps}</div>
            </div>
            """, unsafe_allow_html=True)
        with stage_col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Stage</div>
                <div class="metric-value metric-value-cyan">{(processor.detector.stage or '--').upper()}</div>
            </div>
            """, unsafe_allow_html=True)

        angle_col, acc_col = st.columns(2)
        with angle_col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Joint Angle</div>
                <div class="metric-value">{processor.detector.current_angle}°</div>
            </div>
            """, unsafe_allow_html=True)
        with acc_col:
            acc = processor.detector.get_accuracy_score()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Form Accuracy</div>
                <div class="metric-value">{acc}%</div>
            </div>
            """, unsafe_allow_html=True)

        # Dynamic Goal Progress Bar
        progress_pct = min(processor.detector.reps / target_reps, 1.0) if target_reps > 0 else 0.0
        st.markdown(f"**Goal Progress:** {processor.detector.reps} / {target_reps} Reps ({int(progress_pct * 100)}%)")
        st.progress(progress_pct)

        # Live Posture Feedback Box
        feedback_msg = processor.detector.feedback
        is_flawed = "FIX" in feedback_msg or "SAGGING" in feedback_msg or "SWING" in feedback_msg
        if is_flawed:
            st.markdown(f'<div class="status-badge-warning">⚠ {feedback_msg}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-badge-good">✓ {feedback_msg}</div>', unsafe_allow_html=True)

    # Video Execution Loop when session is running
    if st.session_state["is_running"]:
        cap = None
        is_demo_mode = False

        if video_source_mode == "Cloud Simulation Demo":
            is_demo_mode = True
        elif video_source_mode == "Upload Video File" and uploaded_video_file is not None:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded_video_file.read())
            cap = cv2.VideoCapture(tfile.name)
        else:
            # Live Webcam via OpenCV
            cap = cv2.VideoCapture(0)

        # Continuous processing loop
        while st.session_state["is_running"]:
            if is_demo_mode:
                raw_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                annotated_bgr, metrics = processor.process_frame(raw_frame, is_demo=True)
            else:
                if cap is None or not cap.isOpened():
                    st.warning("Webcam capture unavailable. Switching to Cloud Simulation Demo Mode.")
                    is_demo_mode = True
                    continue

                ret, frame = cap.read()
                if not ret or frame is None:
                    if video_source_mode == "Upload Video File":
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        break
                annotated_bgr, metrics = processor.process_frame(frame, is_demo=False)

            # Convert BGR to RGB for Streamlit image rendering
            annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
            video_placeholder.image(annotated_rgb, channels="RGB", use_container_width=True)

            # Audio coaching event on new rep or posture warning
            curr_reps = metrics["reps"]
            if curr_reps > st.session_state["last_rep_count"]:
                st.session_state["last_rep_count"] = curr_reps
                if curr_reps == target_reps:
                    st.toast(f"🎯 Target goal of {target_reps} reps achieved!")
                    if enable_voice:
                        audio = TextToSpeech.synthesize(f"Target goal achieved! Fantastic job completing {target_reps} reps!")
                        if audio:
                            st.audio(audio, format="audio/mp3", autoplay=True)
                elif enable_voice and curr_reps % 2 == 0:
                    audio = TextToSpeech.synthesize(f"Rep {curr_reps} complete. Keep it up!")
                    if audio:
                        st.audio(audio, format="audio/mp3", autoplay=True)

            # Voice alert on persistent posture flaw
            if enable_voice and metrics["is_flawed"] and metrics["feedback"] != st.session_state["last_voice_feedback"]:
                st.session_state["last_voice_feedback"] = metrics["feedback"]
                cue = coach.get_form_correction_cue(metrics["feedback"], metrics["exercise"])
                audio = TextToSpeech.synthesize(cue)
                if audio:
                    st.audio(audio, format="audio/mp3", autoplay=True)

            # Control framerate (~25 FPS)
            time.sleep(0.04)

        if cap is not None:
            cap.release()

# ==========================================
# TAB 2: SESSION HISTORY & SQLITE ANALYTICS
# ==========================================
with tab_analytics:
    st.header("📊 Workout History & Lifetime Analytics")
    stats = db.get_user_summary_stats(st.session_state["user"]["id"])

    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    with s_col1:
        st.metric("Total Sessions", stats["total_sessions"])
    with s_col2:
        st.metric("Total Reps Completed", stats["total_reps"])
    with s_col3:
        st.metric("Average Accuracy", f"{stats['avg_accuracy']}%")
    with s_col4:
        st.metric("Est. Calories Burned", f"{stats['total_calories']} kcal")

    st.markdown("---")
    st.subheader("📋 SQLite Database Session Log")
    workouts = db.get_user_workouts(st.session_state["user"]["id"], limit=50)

    if workouts:
        df_workouts = pd.DataFrame(workouts)
        df_display = df_workouts[[
            "id", "timestamp", "exercise", "reps", "target_reps",
            "accuracy_score", "warnings_count", "duration_seconds", "calories_burned"
        ]].copy()
        df_display.columns = [
            "Session ID", "Timestamp", "Exercise", "Reps", "Goal",
            "Accuracy (%)", "Warnings", "Duration (s)", "Calories (kcal)"
        ]

        st.dataframe(df_display, use_container_width=True)

        # Reps by Session Chart
        st.subheader("📈 Repetition Progress by Session")
        st.bar_chart(df_display.set_index("Session ID")["Reps"])

        # CSV Export
        csv_data = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Session History (CSV)",
            data=csv_data,
            file_name=f"workout_history_{st.session_state['user']['username']}.csv",
            mime="text/csv"
        )
    else:
        st.info("No workout sessions logged yet. Complete your first set in the Live Workout Arena to view analytics!")

# ==========================================
# TAB 3: BIOMECHANICS & ANGLE SPEC
# ==========================================
with tab_guide:
    st.header("📐 Biomechanical Angle & Posture Tracking Specification")
    st.markdown("""
    This project evaluates body kinematics using **NumPy 2D vector trigonometry** (`np.arctan2`) calculated across **MediaPipe Pose Normalized Landmarks**.
    """)

    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1:
        st.subheader("💪 Bicep Curls")
        st.markdown("""
        - **Joints Tracked**: Shoulder, Elbow, Wrist
        - **Angle Formula**:
          $$\\theta = |\\text{atan2}(W_y - E_y, W_x - E_x) - \\text{atan2}(S_y - E_y, S_x - E_x)|$$
        - **Full ROM**: Extended (>155°) &rarr; Contracted (<45°)
        - **Monitored Flaws**: Elbow swinging, upper torso momentum cheating
        """)

    with b_col2:
        st.subheader("🦵 Squats")
        st.markdown("""
        - **Joints Tracked**: Hip, Knee, Ankle (plus Shoulder-Hip)
        - **Angle Formula**:
          $$\\theta = |\\text{atan2}(A_y - K_y, A_x - K_x) - \\text{atan2}(H_y - K_y, H_x - K_x)|$$
        - **Full ROM**: Standing (>160°) &rarr; Deep Parallel (<95°)
        - **Monitored Flaws**: Shallow depth, chest collapse, knees past toes
        """)

    with b_col3:
        st.subheader("🤸 Push-ups")
        st.markdown("""
        - **Joints Tracked**: Shoulder, Elbow, Wrist & Shoulder-Hip-Ankle
        - **Angle Formula**:
          $$\\text{Plank Alignment} = |\\text{atan2}(A_y - H_y, A_x - H_x) - \\text{atan2}(S_y - H_y, S_x - H_x)|$$
        - **Full ROM**: Top Plank (>155°) &rarr; Chest Down (<90°)
        - **Monitored Flaws**: Sagging hips, piking/raised hips, incomplete ROM
        """)
