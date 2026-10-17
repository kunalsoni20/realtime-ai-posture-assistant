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

    /* Athlete Profile Card */
    .profile-card {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 182, 212, 0.05) 100%);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 12px;
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
if "last_completed_workout" not in st.session_state:
    st.session_state["last_completed_workout"] = None

processor = st.session_state["processor"]
coach = st.session_state["coach_llm"]

# 4. Sidebar: Athlete Sign Up, Login & Session Settings
with st.sidebar:
    st.title("🏋️ AI Gym Coach")
    st.caption("Real-Time Posture Correction & Rep Counter")
    st.markdown("---")

    # Dedicated Athlete Profile & Authentication
    st.subheader("👤 Athlete Profile & Auth")
    curr_user = st.session_state["user"]
    
    # Active Athlete Card
    st.markdown(f"""
    <div class="profile-card">
        <div style="font-size: 0.8rem; color: #10b981; font-weight: 700; text-transform: uppercase;">Active Athlete</div>
        <div style="font-size: 1.3rem; font-weight: 800; color: #f8fafc;">{curr_user['username']}</div>
        <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">🎯 {curr_user.get('goal', 'Muscle Building')} • ⚡ {curr_user.get('fitness_level', 'Intermediate')}</div>
    </div>
    """, unsafe_allow_html=True)

    auth_tab_login, auth_tab_signup = st.tabs(["🔑 Switch Athlete", "➕ Sign Up"])

    with auth_tab_login:
        all_users = db.get_all_users()
        user_names = [u["username"] for u in all_users]
        curr_uname = curr_user["username"]
        default_idx = user_names.index(curr_uname) if curr_uname in user_names else 0
        
        selected_user = st.selectbox("Select Profile", user_names, index=default_idx)
        if st.button("Log In as Selected", use_container_width=True):
            user_data = next((u for u in all_users if u["username"] == selected_user), None)
            if user_data:
                st.session_state["user"] = user_data
                st.toast(f"Switched athlete to {selected_user}!")
                st.rerun()

    with auth_tab_signup:
        with st.form("signup_form", clear_on_submit=True):
            signup_username = st.text_input("New Username", placeholder="e.g. Kunal_Athlete")
            signup_goal = st.selectbox(
                "Primary Goal",
                ["Muscle Building", "Posture Improvement", "Weight Loss", "Endurance"]
            )
            signup_level = st.selectbox(
                "Fitness Level",
                ["Beginner", "Intermediate", "Advanced"]
            )
            signup_submitted = st.form_submit_button("Create Profile & Sign In", use_container_width=True, type="primary")
            if signup_submitted:
                uname = signup_username.strip()
                if uname:
                    new_user = db.get_or_create_user(uname, signup_goal, signup_level)
                    st.session_state["user"] = new_user
                    st.balloons()
                    st.toast(f"Welcome, {uname}! Profile created in SQLite.")
                    st.rerun()
                else:
                    st.error("Please enter a valid username.")

    st.markdown("---")

    # Workout Configuration
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
        ["Cloud Simulation Demo", "Live Webcam (Browser)", "Upload Video File"],
        index=0,
        help="Use Cloud Demo for real-time kinematic simulation, or Browser Camera for live webcam tracking."
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

# 5. Helper Function to Log & Finish Workout
def finish_workout_session():
    duration = int(time.time() - (st.session_state["session_start_time"] or time.time()))
    reps = processor.detector.reps
    accuracy = processor.detector.get_accuracy_score()
    warnings = processor.detector.warning_count
    calories = round(reps * 0.45, 1)

    analysis = coach.get_post_workout_analysis(
        processor.detector.name, reps, target_reps, accuracy, warnings
    )

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

    st.session_state["last_completed_workout"] = {
        "exercise": processor.detector.name,
        "reps": reps,
        "target_reps": target_reps,
        "accuracy": accuracy,
        "warnings": warnings,
        "calories": calories,
        "duration": duration,
        "analysis": analysis
    }
    st.session_state["is_running"] = False

# 6. Main Dashboard Tabs
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
        
        # Dedicated Audio Output Placeholder (Never stacks multiple players)
        audio_placeholder = st.empty()

        # Workout Control Action Bar
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if not st.session_state["is_running"]:
                start_btn = st.button("▶ Start Workout", use_container_width=True, type="primary")
                if start_btn:
                    st.session_state["is_running"] = True
                    st.session_state["session_start_time"] = time.time()
                    st.session_state["last_completed_workout"] = None
                    st.toast("Workout session started!")
                    st.rerun()
            else:
                stop_btn = st.button("⏹ Finish & Log", use_container_width=True, type="primary")
                if stop_btn:
                    finish_workout_session()
                    st.toast("Workout finished and saved!")
                    st.rerun()

        with col_btn2:
            reset_btn = st.button("↺ Reset Reps", use_container_width=True)
            if reset_btn:
                processor.reset_reps()
                st.session_state["last_rep_count"] = 0
                st.toast("Reps reset to 0!")
                st.rerun()

        with col_btn3:
            st.caption(f"Status: **{'RUNNING ⚡' if st.session_state['is_running'] else 'READY'}**")

        # Display Celebration Summary if just finished
        if st.session_state["last_completed_workout"] and not st.session_state["is_running"]:
            w = st.session_state["last_completed_workout"]
            st.balloons()
            st.success(f"🎉 **Workout Saved to SQLite!** {w['reps']} reps completed with {w['accuracy']}% accuracy ({w['calories']} kcal burned in {w['duration']}s).")
            st.markdown(f"**AI Coach Alex Summary:** {w['analysis']}")
            if enable_voice:
                aud = TextToSpeech.synthesize(w["analysis"])
                if aud:
                    audio_placeholder.audio(aud, format="audio/mp3", autoplay=True)

        # Live Webcam Browser Input on Streamlit Cloud
        if video_source_mode == "Live Webcam (Browser)":
            st.markdown("#### 📷 Live Browser Camera Input")
            cam_frame = st.camera_input("Take a snapshot to analyze your posture with MediaPipe")
            if cam_frame is not None:
                bytes_data = cam_frame.getvalue()
                cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                annotated_bgr, metrics = processor.process_frame(cv2_img, is_demo=False)
                annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
                video_placeholder.image(annotated_rgb, channels="RGB", use_container_width=True)

    with col_stats:
        st.subheader("⚡ Live Telemetry")
        
        rep_col, stage_col = st.columns(2)
        with rep_col:
            rep_holder = st.empty()
        with stage_col:
            stage_holder = st.empty()

        angle_col, acc_col = st.columns(2)
        with angle_col:
            angle_holder = st.empty()
        with acc_col:
            acc_holder = st.empty()

        progress_holder = st.empty()
        feedback_holder = st.empty()

        def update_telemetry_ui(reps: int, stage: str, angle: float, acc: float, feedback: str):
            rep_holder.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Completed Reps</div>
                <div class="metric-value metric-value-emerald">{reps}</div>
            </div>
            """, unsafe_allow_html=True)

            stage_holder.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Stage</div>
                <div class="metric-value metric-value-cyan">{(stage or '--').upper()}</div>
            </div>
            """, unsafe_allow_html=True)

            angle_holder.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Joint Angle</div>
                <div class="metric-value">{round(angle, 1)}°</div>
            </div>
            """, unsafe_allow_html=True)

            acc_holder.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Form Accuracy</div>
                <div class="metric-value">{acc}%</div>
            </div>
            """, unsafe_allow_html=True)

            pct = min(reps / target_reps, 1.0) if target_reps > 0 else 0.0
            progress_holder.markdown(f"**Goal Progress:** {reps} / {target_reps} Reps ({int(pct * 100)}%)")
            progress_holder.progress(pct)

            is_flawed = "FIX" in feedback or "SAGGING" in feedback or "SWING" in feedback
            if is_flawed:
                feedback_holder.markdown(f'<div class="status-badge-warning">⚠ {feedback}</div>', unsafe_allow_html=True)
            else:
                feedback_holder.markdown(f'<div class="status-badge-good">✓ {feedback}</div>', unsafe_allow_html=True)

        # Initial UI render when idle
        if not st.session_state["is_running"]:
            update_telemetry_ui(
                reps=processor.detector.reps,
                stage=processor.detector.stage,
                angle=processor.detector.current_angle,
                acc=processor.detector.get_accuracy_score(),
                feedback=processor.detector.feedback
            )
            # Render a crisp initial preview frame so it's never an empty void
            init_frame, _ = processor.demo_gen.generate_frame(processor.current_key)
            init_annotated = HUDOverlay.render(
                frame=init_frame,
                exercise_name=processor.detector.name,
                reps=processor.detector.reps,
                stage=processor.detector.stage,
                feedback=processor.detector.feedback,
                angle=processor.detector.current_angle,
                fps=28.5
            )
            init_rgb = cv2.cvtColor(init_annotated, cv2.COLOR_BGR2RGB)
            video_placeholder.image(init_rgb, channels="RGB", use_container_width=True)

    # Active Workout Video Execution Step
    if st.session_state["is_running"]:
        if video_source_mode == "Cloud Simulation Demo":
            dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            annotated_bgr, metrics = processor.process_frame(dummy, is_demo=True)
        elif video_source_mode == "Upload Video File" and uploaded_video_file is not None:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded_video_file.read())
            cap = cv2.VideoCapture(tfile.name)
            ret, frame = cap.read()
            if ret and frame is not None:
                annotated_bgr, metrics = processor.process_frame(frame, is_demo=False)
            else:
                annotated_bgr, metrics = processor.process_frame(np.zeros((480, 640, 3), dtype=np.uint8), is_demo=True)
            cap.release()
        else:
            dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            annotated_bgr, metrics = processor.process_frame(dummy, is_demo=True)

        # Render current frame into video placeholder
        annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
        video_placeholder.image(annotated_rgb, channels="RGB", use_container_width=True)

        # Update telemetry HUD cards live
        update_telemetry_ui(
            reps=metrics["reps"],
            stage=metrics["stage"],
            angle=metrics["angle"],
            acc=metrics["accuracy"],
            feedback=metrics["feedback"]
        )

        # Audio coaching milestones
        curr_reps = metrics["reps"]
        if curr_reps > st.session_state["last_rep_count"]:
            st.session_state["last_rep_count"] = curr_reps
            if curr_reps >= target_reps:
                finish_workout_session()
                st.rerun()
            elif enable_voice and curr_reps % 2 == 0:
                audio = TextToSpeech.synthesize(f"Rep {curr_reps} complete. Keep it up!")
                if audio:
                    audio_placeholder.audio(audio, format="audio/mp3", autoplay=True)

        # Posture correction voice alert
        if enable_voice and metrics["is_flawed"] and metrics["feedback"] != st.session_state["last_voice_feedback"]:
            st.session_state["last_voice_feedback"] = metrics["feedback"]
            cue = coach.get_form_correction_cue(metrics["feedback"], metrics["exercise"])
            audio = TextToSpeech.synthesize(cue)
            if audio:
                audio_placeholder.audio(audio, format="audio/mp3", autoplay=True)

        # Frame pacing and trigger next frame rerun smoothly
        time.sleep(0.04)
        st.rerun()

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
    st.subheader(f"📋 SQLite Database Session Log for {st.session_state['user']['username']}")
    workouts = db.get_user_workouts(st.session_state["user"]["id"], limit=50)

    if workouts:
        df_workouts = pd.DataFrame(workouts)
        df_display = df_workouts[[
            "exercise", "reps", "target_reps", "accuracy_score",
            "warnings_count", "duration_seconds", "calories_burned", "coach_feedback", "timestamp"
        ]].rename(columns={
            "exercise": "Exercise",
            "reps": "Completed Reps",
            "target_reps": "Target Goal",
            "accuracy_score": "Accuracy (%)",
            "warnings_count": "Posture Flags",
            "duration_seconds": "Duration (s)",
            "calories_burned": "Calories (kcal)",
            "coach_feedback": "Coach Alex Feedback",
            "timestamp": "Timestamp"
        })
        st.dataframe(df_display, use_container_width=True)

        # Visual Chart of Reps per Session
        st.subheader("📈 Exercise Volume Over Time")
        chart_data = df_workouts[["timestamp", "reps"]].sort_values("timestamp")
        st.bar_chart(chart_data.set_index("timestamp"))

        # Download CSV Export
        csv_bytes = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Session History (CSV)",
            data=csv_bytes,
            file_name=f"workout_history_{st.session_state['user']['username'].lower()}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No recorded workouts found for this athlete yet. Complete a workout session in the Arena to log your first record into SQLite!")

# ==========================================
# TAB 3: BIOMECHANICS & ANGLE SPEC
# ==========================================
with tab_guide:
    st.header("📐 Biomechanical Angle Specification & Trigonometry")
    st.markdown("""
    The AI Gym Coach calculates geometric joint angles in real time using 3D skeletal landmark coordinates 
    derived from Google MediaPipe Pose and vectorized NumPy planar trigonometry.
    """)

    b_col1, b_col2 = st.columns(2)

    with b_col1:
        st.subheader("Mathematical Vector Formulation")
        st.markdown(r"""
        Given three kinetic joint points $A(x_1, y_1)$, $B(x_2, y_2)$ *(vertex joint)*, and $C(x_3, y_3)$:

        $$\theta = \left| \text{arctan2}(y_3 - y_2, x_3 - x_2) - \text{arctan2}(y_1 - y_2, x_1 - x_2) \right| \times \frac{180^\circ}{\pi}$$

        If $\theta > 180^\circ$, the interior angle is corrected:
        $$\theta = 360^\circ - \theta$$

        This guarantees invariant, quadrant-safe angle measurements across left and right sides of the body.
        """)

    with b_col2:
        st.subheader("Kinematic Benchmark Thresholds")
        st.markdown("""
        | Exercise | Target Joint | Vertex Landmark | Rep Thresholds (UP / DOWN) | Key Posture Alert Criteria |
        |---|---|---|---|---|
        | **Squats** | Knee Angle | Landmark 25/26 (Knee) | **UP:** > 160°<br>**DOWN:** < 90° | Torso caving forward (< 65°) or knees past toes |
        | **Push-ups** | Elbow Angle | Landmark 13/14 (Elbow) | **UP:** > 160°<br>**DOWN:** < 90° | Sagging hips / arched lower back (Hip angle deviation > 30°) |
        | **Bicep Curls** | Elbow Flexion | Landmark 13/14 (Elbow) | **DOWN:** > 160°<br>**UP:** < 40° | Elbow drift / upper-arm swinging (> 25px offset) |
        """)
