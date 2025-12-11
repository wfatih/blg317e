// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    
    // ========================================
    // 1. COUNT UP ANIMATION
    // ========================================
    function animateCountUp(element, target, duration = 2000) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current);
        }, 16);
    }
    
    // Animate all count-up elements
    const countUpElements = document.querySelectorAll('.count-up');
    countUpElements.forEach(el => {
        const target = parseInt(el.dataset.target);
        if (!isNaN(target)) {
            setTimeout(() => {
                animateCountUp(el, target, 2000);
            }, 500);
        }
    });
    
    // ========================================
    // 2. PROGRESS BAR ANIMATIONS
    // ========================================
    function animateProgressBars() {
        // Win percentage bars
        const winBars = document.querySelectorAll('.win-fill');
        winBars.forEach(bar => {
            const percentage = parseFloat(bar.dataset.percentage);
            if (!isNaN(percentage)) {
                setTimeout(() => {
                    bar.style.width = percentage + '%';
                }, 300);
            }
        });
        
        // Statistics comparison bars
        const statBars = document.querySelectorAll('.progress-bar');
        statBars.forEach(bar => {
            const percentage = parseFloat(bar.dataset.percentage);
            if (!isNaN(percentage)) {
                setTimeout(() => {
                    if (bar.classList.contains('left')) {
                        bar.style.width = percentage + '%';
                    } else if (bar.classList.contains('right')) {
                        bar.style.width = percentage + '%';
                    }
                }, 800);
            }
        });
    }
    
    animateProgressBars();
    
    // ========================================
    // 3. CONFETTI ANIMATION (Winner Celebration)
    // ========================================
    const gameResult = document.getElementById('gameResult');
    if (gameResult && gameResult.textContent.includes('wins')) {
        setTimeout(() => {
            createConfetti();
        }, 1000);
    }
    
    function createConfetti() {
        const canvas = document.getElementById('confetti-canvas');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const confettiCount = 150;
        const confetti = [];
        const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4ade80', '#fbbf24'];
        
        class ConfettiPiece {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = -20;
                this.size = Math.random() * 8 + 4;
                this.speedY = Math.random() * 3 + 2;
                this.speedX = Math.random() * 4 - 2;
                this.color = colors[Math.floor(Math.random() * colors.length)];
                this.rotation = Math.random() * 360;
                this.rotationSpeed = Math.random() * 10 - 5;
            }
            
            update() {
                this.y += this.speedY;
                this.x += this.speedX;
                this.rotation += this.rotationSpeed;
                
                if (this.y > canvas.height) {
                    this.y = -20;
                    this.x = Math.random() * canvas.width;
                }
            }
            
            draw() {
                ctx.save();
                ctx.translate(this.x, this.y);
                ctx.rotate(this.rotation * Math.PI / 180);
                ctx.fillStyle = this.color;
                ctx.fillRect(-this.size / 2, -this.size / 2, this.size, this.size);
                ctx.restore();
            }
        }
        
        for (let i = 0; i < confettiCount; i++) {
            confetti.push(new ConfettiPiece());
        }
        
        let animationFrames = 0;
        const maxFrames = 300; // 5 seconds at 60fps
        
        function animate() {
            if (animationFrames >= maxFrames) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                return;
            }
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            confetti.forEach(piece => {
                piece.update();
                piece.draw();
            });
            
            animationFrames++;
            requestAnimationFrame(animate);
        }
        
        animate();
    }
    
    // ========================================
    // 4. INTERSECTION OBSERVER (Scroll Animations)
    // ========================================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe sections that should animate on scroll
    const animatedSections = document.querySelectorAll('.fade-in-up');
    animatedSections.forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(30px)';
        section.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
        observer.observe(section);
    });
    
    // ========================================
    // 5. HOVER 3D EFFECT FOR CARDS
    // ========================================
    const hover3DCards = document.querySelectorAll('.hover-3d');
    hover3DCards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / 10;
            const rotateY = (centerX - x) / 10;
            
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(10px)`;
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) translateZ(0)';
        });
    });
    
    // ========================================
    // 6. TEAM SCORE COMPARISON ANIMATION
    // ========================================
    function animateScoreComparison() {
        const homeScore = document.querySelector('.home-team .team-score');
        const awayScore = document.querySelector('.away-team .team-score');
        
        if (homeScore && awayScore) {
            const homeValue = parseInt(homeScore.dataset.target);
            const awayValue = parseInt(awayScore.dataset.target);
            
            if (!isNaN(homeValue) && !isNaN(awayValue)) {
                if (homeValue > awayValue) {
                    setTimeout(() => {
                        homeScore.style.transform = 'scale(1.1)';
                        homeScore.style.filter = 'drop-shadow(0 0 20px rgba(76, 175, 80, 0.6))';
                    }, 2500);
                } else if (awayValue > homeValue) {
                    setTimeout(() => {
                        awayScore.style.transform = 'scale(1.1)';
                        awayScore.style.filter = 'drop-shadow(0 0 20px rgba(76, 175, 80, 0.6))';
                    }, 2500);
                }
            }
        }
    }
    
    animateScoreComparison();
    
    // ========================================
    // 7. FORM BADGES TOOLTIP
    // ========================================
    const formBadges = document.querySelectorAll('.form-badge');
    formBadges.forEach(badge => {
        badge.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.15) rotate(5deg)';
        });
        
        badge.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1) rotate(0)';
        });
    });
    
    // ========================================
    // 8. SMOOTH SCROLL FOR NAVIGATION
    // ========================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // ========================================
    // 9. PARALLAX EFFECT ON SCROLL
    // ========================================
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.game-header');
        
        parallaxElements.forEach(el => {
            const speed = 0.5;
            el.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });
    
    // ========================================
    // 10. LOADING SKELETON FADE OUT
    // ========================================
    setTimeout(() => {
        const skeletons = document.querySelectorAll('.skeleton');
        skeletons.forEach(skeleton => {
            skeleton.style.opacity = '0';
            skeleton.style.transition = 'opacity 0.5s ease';
            setTimeout(() => {
                skeleton.style.display = 'none';
            }, 500);
        });
    }, 1000);
    
    // ========================================
    // 11. RESIZE HANDLER FOR CANVAS
    // ========================================
    window.addEventListener('resize', () => {
        const canvas = document.getElementById('confetti-canvas');
        if (canvas) {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
    });
    
    // ========================================
    // 12. ADD PULSE TO WINNER TROPHY ICON
    // ========================================
    const trophyIcon = document.querySelector('.trophy-icon');
    if (trophyIcon) {
        setInterval(() => {
            trophyIcon.classList.add('scale-pulse');
            setTimeout(() => {
                trophyIcon.classList.remove('scale-pulse');
            }, 1000);
        }, 3000);
    }
    
    // ========================================
    // 13. STATS BAR HOVER EFFECT
    // ========================================
    const statRows = document.querySelectorAll('.stat-row');
    statRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.02)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    console.log('🏀 Game Detail Animations Loaded Successfully!');
});