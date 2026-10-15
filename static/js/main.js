document.addEventListener('DOMContentLoaded', () => {
    const exerciseBtns = document.querySelectorAll('.btn-exercise');

    exerciseBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            exerciseBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const exercise = btn.dataset.exercise;

            try {
                await fetch('/api/select_exercise', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ exercise })
                });
            } catch (err) {
                console.error('Failed to change exercise:', err);
            }
        });
    });

    // Poll live metrics every 500ms
    setInterval(async () => {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) return;
            const data = await res.json();
            
            const repCounter = document.getElementById('repCounter');
            const stageIndicator = document.getElementById('stageIndicator');
            const feedbackBadge = document.getElementById('postureFeedback');

            if (repCounter) repCounter.textContent = data.reps ?? 0;
            if (stageIndicator) stageIndicator.textContent = (data.stage ?? '--').toUpperCase();
            if (feedbackBadge) {
                feedbackBadge.textContent = data.feedback ?? 'READY';
                if (data.feedback && data.feedback.includes('FIX')) {
                    feedbackBadge.style.color = '#ef4444';
                    feedbackBadge.style.background = 'rgba(239, 68, 68, 0.2)';
                } else {
                    feedbackBadge.style.color = '#10b981';
                    feedbackBadge.style.background = 'rgba(16, 185, 129, 0.2)';
                }
            }
        } catch (err) {
            // Silently handle polling errors
        }
    }, 500);
});
