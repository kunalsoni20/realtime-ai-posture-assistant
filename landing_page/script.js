document.addEventListener('DOMContentLoaded', () => {
    // Dynamic Hero Counter Simulation
    const repElem = document.getElementById('heroRepCounter');
    const angleElem = document.getElementById('heroAngleDisplay');
    
    let currentReps = 12;
    let angle = 92.4;
    let angleDirection = 1;

    // Simulate animated live kinematic angles
    setInterval(() => {
        if (angleDirection === 1) {
            angle += 2.8;
            if (angle >= 165.0) {
                angleDirection = -1;
            }
        } else {
            angle -= 3.2;
            if (angle <= 88.0) {
                angleDirection = 1;
                currentReps++;
                if (repElem) {
                    repElem.textContent = currentReps;
                    repElem.classList.add('pulse-number');
                    setTimeout(() => repElem.classList.remove('pulse-number'), 400);
                }
            }
        }
        if (angleElem) {
            angleElem.textContent = `${angle.toFixed(1)}°`;
        }
    }, 70);

    // Smooth scroll for in-page anchors
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
});
