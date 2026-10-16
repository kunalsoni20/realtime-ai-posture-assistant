document.addEventListener('DOMContentLoaded', () => {
    // Biomechanics guide content per exercise
    const BIOMECHANICS_INFO = {
        bicep_curls: {
            title: "Bicep Curls",
            joints: "Shoulder, Elbow, Wrist",
            angleLabel: "Elbow Joint Angle",
            range: "Down (>155°) → Up (<45°)",
            flaws: "Elbow swinging, torso cheat, partial ROM"
        },
        squats: {
            title: "Squats",
            joints: "Hip, Knee, Ankle (plus Shoulder-Hip)",
            angleLabel: "Knee Joint Angle",
            range: "Standing (>160°) → Squat (<95°)",
            flaws: "Shallow depth, chest collapsing, knees forward"
        },
        pushups: {
            title: "Push-ups",
            joints: "Shoulder, Elbow, Wrist & Shoulder-Hip-Ankle",
            angleLabel: "Elbow Flexion Angle",
            range: "Plank (>155°) → Chest Down (<90°)",
            flaws: "Sagging hips, piking, incomplete chest depth"
        }
    };

    // DOM Elements
    const exerciseBtns = document.querySelectorAll('.btn-exercise');
    const sourceBtns = document.querySelectorAll('.btn-source:not(.btn-upload-label)');
    const videoUploadInput = document.getElementById('videoUploadInput');
    const btnStart = document.getElementById('btnStartSession');
    const btnEnd = document.getElementById('btnEndSession');
    const btnReset = document.getElementById('btnResetReps');

    const videoFeed = document.getElementById('videoFeed');
    const webcamVideo = document.getElementById('webcamVideo');
    const webcamCanvas = document.getElementById('webcamCanvas');

    const repCounter = document.getElementById('repCounter');
    const stageBadge = document.getElementById('stageBadge');
    const postureFeedbackBox = document.getElementById('postureFeedbackBox');
    const postureFeedbackText = document.getElementById('postureFeedbackText');
    const feedbackIcon = document.getElementById('feedbackIcon');
    const accuracyValue = document.getElementById('accuracyValue');
    const accuracyProgressBar = document.getElementById('accuracyProgressBar');
    const angleText = document.getElementById('angleText');
    const angleGaugeFill = document.getElementById('angleGaugeFill');
    const angleJointLabel = document.getElementById('angleJointLabel');
    const fpsDisplay = document.getElementById('fpsDisplay');
    const activeExerciseBadge = document.getElementById('activeExerciseBadge');
    const sourceDisplayBadge = document.getElementById('sourceDisplayBadge');
    const sessionTimer = document.getElementById('sessionTimer');
    const toast = document.getElementById('toastNotification');

    const specJoints = document.getElementById('specJoints');
    const specRange = document.getElementById('specRange');
    const specFlaws = document.getElementById('specFlaws');

    let isSessionRunning = false;
    let sessionSeconds = 0;
    let sessionTimerInterval = null;

    // Browser Webcam Streaming State
    let isBrowserWebcamActive = false;
    let webcamStream = null;
    let isSendingFrame = false;

    // Toast helper
    function showToast(message) {
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3500);
    }

    // UI Updater Helper
    function updateMetricsUI(data) {
        if (!data) return;
        if (repCounter) repCounter.textContent = data.reps ?? 0;
        if (stageBadge) {
            stageBadge.textContent = (data.stage ?? '--').toUpperCase();
        }

        if (postureFeedbackText && postureFeedbackBox) {
            const feedback = data.feedback ?? 'READY';
            postureFeedbackText.textContent = feedback;

            const isWarning = feedback.includes('FIX') || feedback.includes('SAGGING') || feedback.includes('SWING');
            if (isWarning) {
                postureFeedbackBox.className = 'feedback-box status-warning';
                if (feedbackIcon) feedbackIcon.textContent = '⚠';
            } else {
                postureFeedbackBox.className = 'feedback-box status-good';
                if (feedbackIcon) feedbackIcon.textContent = '✓';
            }
        }

        if (accuracyValue && accuracyProgressBar) {
            const acc = data.accuracy ?? 100.0;
            accuracyValue.textContent = `${acc}%`;
            accuracyProgressBar.style.width = `${acc}%`;
        }

        if (angleText && angleGaugeFill) {
            const angle = data.angle ?? 0.0;
            angleText.textContent = `${angle.toFixed(1)}°`;
            const pct = Math.min(Math.max((angle / 180.0) * 100, 0), 100);
            angleGaugeFill.style.width = `${pct}%`;
        }

        if (fpsDisplay && data.fps) {
            fpsDisplay.textContent = `FPS: ${data.fps.toFixed(1)}`;
        }

        if (sourceDisplayBadge && data.source_mode) {
            sourceDisplayBadge.textContent = `SOURCE: ${data.source_mode.toUpperCase()}`;
        }
    }

    // 1. Browser Webcam Stream Logic
    async function startBrowserWebcam() {
        try {
            if (!webcamStream) {
                webcamStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 } },
                    audio: false
                });
                webcamVideo.srcObject = webcamStream;
                await webcamVideo.play();
            }
            isBrowserWebcamActive = true;
            if (sourceDisplayBadge) sourceDisplayBadge.textContent = "SOURCE: LIVE WEBCAM";
            showToast("Camera connected! Detecting posture in real time...");
            requestAnimationFrame(processWebcamLoop);
        } catch (err) {
            console.error("Camera access error:", err);
            showToast("Could not access camera. Please allow camera permissions in Brave.");
        }
    }

    function stopBrowserWebcam() {
        isBrowserWebcamActive = false;
        if (webcamStream) {
            webcamStream.getTracks().forEach(track => track.stop());
            webcamStream = null;
        }
        if (videoFeed) {
            videoFeed.src = "/video_feed";
        }
    }

    function processWebcamLoop() {
        if (!isBrowserWebcamActive) return;

        if (webcamVideo.readyState >= 2 && !isSendingFrame) {
            isSendingFrame = true;
            const ctx = webcamCanvas.getContext('2d');
            webcamCanvas.width = 640;
            webcamCanvas.height = 480;
            ctx.drawImage(webcamVideo, 0, 0, 640, 480);

            webcamCanvas.toBlob(async (blob) => {
                if (!blob) {
                    isSendingFrame = false;
                    if (isBrowserWebcamActive) requestAnimationFrame(processWebcamLoop);
                    return;
                }
                try {
                    const res = await fetch('/api/process_frame', {
                        method: 'POST',
                        headers: { 'Content-Type': 'image/jpeg' },
                        body: blob
                    });
                    if (res.ok) {
                        const data = await res.json();
                        if (data.image && isBrowserWebcamActive && videoFeed) {
                            videoFeed.src = data.image;
                        }
                        if (data.metrics) {
                            updateMetricsUI(data.metrics);
                        }
                    }
                } catch (e) {
                    // Ignore dropped frame
                } finally {
                    isSendingFrame = false;
                    if (isBrowserWebcamActive) {
                        requestAnimationFrame(processWebcamLoop);
                    }
                }
            }, 'image/jpeg', 0.80);
        } else {
            if (isBrowserWebcamActive) {
                requestAnimationFrame(processWebcamLoop);
            }
        }
    }

    // 2. Exercise Selection Handler
    exerciseBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const exerciseKey = btn.dataset.exercise;
            exerciseBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update Biomechanics Guide Spec
            const info = BIOMECHANICS_INFO[exerciseKey];
            if (info) {
                if (specJoints) specJoints.textContent = info.joints;
                if (specRange) specRange.textContent = info.range;
                if (specFlaws) specFlaws.textContent = info.flaws;
                if (angleJointLabel) angleJointLabel.textContent = info.angleLabel;
                if (activeExerciseBadge) activeExerciseBadge.textContent = info.title;
            }

            try {
                const res = await fetch('/api/select_exercise', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ exercise: exerciseKey })
                });
                const data = await res.json();
                showToast(`Switched exercise to ${data.exercise}`);
            } catch (err) {
                console.error('Failed to select exercise:', err);
            }
        });
    });

    // 3. Video Source Selector Handler
    sourceBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const sourceMode = btn.dataset.source;
            sourceBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (sourceMode === 'webcam') {
                await startBrowserWebcam();
            } else {
                stopBrowserWebcam();
                try {
                    const res = await fetch('/api/set_source', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: sourceMode })
                    });
                    const data = await res.json();
                    if (sourceDisplayBadge) {
                        sourceDisplayBadge.textContent = `SOURCE: ${data.mode.toUpperCase()}`;
                    }
                    showToast(`Video source switched to ${data.mode.toUpperCase()}`);
                } catch (err) {
                    console.error('Failed to switch video source:', err);
                }
            }
        });
    });

    // 4. Custom Video Upload Handler
    if (videoUploadInput) {
        videoUploadInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            stopBrowserWebcam();
            const formData = new FormData();
            formData.append('video', file);

            showToast(`Uploading ${file.name}...`);
            try {
                const res = await fetch('/api/upload_video', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.status === 'success') {
                    sourceBtns.forEach(b => b.classList.remove('active'));
                    if (sourceDisplayBadge) {
                        sourceDisplayBadge.textContent = `SOURCE: UPLOAD (${data.filename})`;
                    }
                    showToast(`Playing uploaded video: ${data.filename}`);
                } else {
                    showToast(`Upload failed: ${data.message}`);
                }
            } catch (err) {
                console.error('Video upload failed:', err);
                showToast('Failed to upload video file.');
            }
        });
    }

    // 5. Session Controls (Start, End, Reset)
    if (btnStart) {
        btnStart.addEventListener('click', async () => {
            try {
                await fetch('/api/session/start', { method: 'POST' });
                isSessionRunning = true;
                sessionSeconds = 0;
                btnStart.disabled = true;
                btnEnd.disabled = false;

                clearInterval(sessionTimerInterval);
                sessionTimerInterval = setInterval(() => {
                    sessionSeconds++;
                    const mins = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
                    const secs = String(sessionSeconds % 60).padStart(2, '0');
                    if (sessionTimer) sessionTimer.textContent = `${mins}:${secs}`;
                }, 1000);

                showToast('Workout session started! Metrics are being recorded.');
            } catch (err) {
                console.error('Failed to start session:', err);
            }
        });
    }

    if (btnEnd) {
        btnEnd.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/session/end', { method: 'POST' });
                const data = await res.json();
                isSessionRunning = false;
                btnStart.disabled = false;
                btnEnd.disabled = true;
                clearInterval(sessionTimerInterval);

                if (data.session) {
                    showToast(`Session logged to Pandas! ${data.session.reps_completed} reps completed (${data.session.accuracy_score}% accuracy).`);
                }
            } catch (err) {
                console.error('Failed to end session:', err);
            }
        });
    }

    if (btnReset) {
        btnReset.addEventListener('click', async () => {
            try {
                await fetch('/api/session/reset', { method: 'POST' });
                if (repCounter) repCounter.textContent = '0';
                showToast('Rep counter reset to 0.');
            } catch (err) {
                console.error('Failed to reset session:', err);
            }
        });
    }

    // 6. Polling sync for Demo Mode & Background updates (only runs when browser webcam is inactive)
    setInterval(async () => {
        if (isBrowserWebcamActive) return; // Browser webcam updates directly via frame processing loop
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) return;
            const data = await res.json();
            updateMetricsUI(data);
        } catch (err) {
            // Silently swallow transient network errors
        }
    }, 250);
});
