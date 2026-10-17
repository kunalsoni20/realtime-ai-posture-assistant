import os
from io import BytesIO
import random
try:
    from gtts import gTTS
except ImportError:
    try:
        from gTTS import gTTS
    except ImportError:
        gTTS = None


class TextToSpeech:
    """
    In-memory Text-to-Speech synthesizer using gTTS.
    Caches common coaching audio clips in memory for instant playback on Streamlit.
    """
    _audio_cache = {}

    @classmethod
    def synthesize(cls, text: str, lang: str = "en") -> Optional[BytesIO]:
        """
        Converts text string into MP3 audio bytes buffer.
        Returns:
            io.BytesIO buffer containing MP3 audio, or None if generation failed.
        """
        if gTTS is None or not text or not text.strip():
            return None

        clean_text = text.strip()
        if clean_text in cls._audio_cache:
            buf = BytesIO(cls._audio_cache[clean_text])
            buf.seek(0)
            return buf

        try:
            tts = gTTS(text=clean_text, lang=lang, slow=False)
            fp = BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            raw_bytes = fp.getvalue()
            cls._audio_cache[clean_text] = raw_bytes

            buf = BytesIO(raw_bytes)
            buf.seek(0)
            return buf
        except Exception as e:
            print(f"[TextToSpeech Error]: {e}")
            return None


class CoachLLM:
    """
    AI Workout Coach powered by LLM reasoning.
    Provides motivational pre-workout briefings, real-time form correction cues,
    and post-workout analytical summaries.
    Supports OpenAI API if configured, with a built-in expert sports science persona fallback.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def get_pre_workout_briefing(self, exercise: str, goal: str, fitness_level: str) -> str:
        """Generates dynamic motivational briefing before starting a set."""
        tips = {
            "Squats": "Focus on driving through your heels and keeping your chest proud. Aim for 90-degree parallel depth.",
            "Push-ups": "Lock your core tight into a rigid plank. Avoid sagging your hips as you press the floor away.",
            "Bicep Curls": "Keep your elbows pinned to your ribs. Control the eccentric lowering phase for maximum muscle activation."
        }
        tip = tips.get(exercise, "Maintain steady breathing and prioritize full range of motion.")
        return f"Hey Athlete! For this {fitness_level} {exercise} set targeting '{goal}': {tip} Let's crush this set!"

    def get_form_correction_cue(self, feedback: str, exercise: str) -> str:
        """Returns brief, punchy voice coaching cues for instant auditory feedback."""
        cues = {
            "FIX POSTURE: KEEP CHEST UP": "Chest up! Look forward, don't round your upper back.",
            "FIX POSTURE: KNEES TOO FORWARD": "Push your hips back! Don't let your knees cave forward past your toes.",
            "FIX POSTURE: SQUAT DEEPER": "Squat deeper! Hit full 90 degrees.",
            "FIX POSTURE: KEEP ELBOW TUCKED": "Pin your elbows to your sides! Stop swinging your arms.",
            "FIX POSTURE: DO NOT SWING TORSO": "Keep your core braced! Stop using momentum to swing.",
            "FIX POSTURE: SAGGING HIPS (ENGAGE CORE)": "Squeeze your glutes and engage your core! Don't let your hips sag.",
            "FIX POSTURE: HIPS TOO HIGH": "Lower your hips into a straight plank line.",
            "FIX POSTURE: LOWER CHEST FULLY": "Lower your chest all the way to 90 degrees."
        }
        return cues.get(feedback, "Focus on smooth control and keep your core engaged!")

    def get_post_workout_analysis(self, exercise: str, reps: int, target_reps: int, accuracy: float, warnings: int) -> str:
        """
        Synthesizes post-workout coaching summary.
        If OpenAI API key is supplied, queries GPT for a coach breakdown,
        otherwise uses rule-based expert fitness persona.
        """
        # If API key is available, call OpenAI API
        if self.api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=self.api_key)
                prompt = f"""
                You are Coach Alex, an elite Olympic strength and biomechanics coach.
                The athlete just completed a workout:
                - Exercise: {exercise}
                - Repetitions Completed: {reps} / {target_reps} target
                - Biomechanical Accuracy Score: {accuracy}%
                - Form Flaw Warnings: {warnings}

                Write a concise, high-energy 2-3 sentence coaching summary:
                1. Praise their effort and goal completion.
                2. Point out specific posture tips based on accuracy and warnings.
                3. Motivate them for the next workout.
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[CoachLLM API Error]: {e}")

        # Intelligent Built-in Heuristic Coach Persona
        pct_goal = (reps / target_reps * 100) if target_reps > 0 else 100
        if accuracy >= 90 and pct_goal >= 100:
            return (f"Phenomenal workout! You crushed {reps}/{target_reps} reps with near-flawless {accuracy}% biomechanical form. "
                    f"Your movement quality and tempo were textbook perfection. Keep this elite momentum going!")
        elif accuracy >= 75 and pct_goal >= 80:
            return (f"Solid work out there! You completed {reps} reps with an admirable {accuracy}% accuracy score. "
                    f"We logged {warnings} minor posture flags, so on your next set, focus extra on full range of motion. Great consistency!")
        else:
            return (f"Good persistence pushing through {reps} reps! Your accuracy landed at {accuracy}% with {warnings} posture adjustments. "
                    f"Remember: quality form always beats quantity. Rest up, hydrate, and let's dial in the alignment next round!")
