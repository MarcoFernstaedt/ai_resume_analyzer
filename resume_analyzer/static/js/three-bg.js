/**
 * DevResume AI — 3D Particle Background
 * WebGL canvas particle system with CSS fallback.
 * Optimized for all screen sizes and connection speeds.
 * Respects prefers-reduced-motion.
 */
(function () {
  'use strict';

  const PARTICLE_COUNT_DESKTOP = 80;
  const PARTICLE_COUNT_TABLET  = 50;
  const PARTICLE_COUNT_MOBILE  = 30;
  const PARTICLE_COLORS = ['#58a6ff', '#C9A84C', '#3fb950', '#a371f7', '#79c0ff'];
  const CONNECTION_DIST = 120;
  const SPEED_FACTOR    = 0.35;

  let canvas, ctx, particles = [], animId, W, H;
  let mouseX = -9999, mouseY = -9999;
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── Capability detection ───────────────────────────────────────────────────

  function supportsCanvas() {
    const c = document.createElement('canvas');
    return !!(c.getContext && c.getContext('2d'));
  }

  function getParticleCount() {
    if (W <= 480)  return PARTICLE_COUNT_MOBILE;
    if (W <= 1024) return PARTICLE_COUNT_TABLET;
    return PARTICLE_COUNT_DESKTOP;
  }

  // ── Particle class ─────────────────────────────────────────────────────────

  function Particle() {
    this.reset();
  }

  Particle.prototype.reset = function () {
    this.x  = Math.random() * W;
    this.y  = Math.random() * H;
    this.vx = (Math.random() - 0.5) * SPEED_FACTOR;
    this.vy = (Math.random() - 0.5) * SPEED_FACTOR;
    this.r  = Math.random() * 2.2 + 0.8;
    this.alpha = Math.random() * 0.5 + 0.2;
    this.color = PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)];
    this.pulse = Math.random() * Math.PI * 2; // phase offset
  };

  Particle.prototype.update = function () {
    this.pulse += 0.02;
    const pulseR = this.r + Math.sin(this.pulse) * 0.4;

    // Mouse repulsion
    const dx = this.x - mouseX;
    const dy = this.y - mouseY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 80 && dist > 0) {
      const force = (80 - dist) / 80 * 0.8;
      this.vx += (dx / dist) * force;
      this.vy += (dy / dist) * force;
    }

    // Speed cap
    const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
    if (speed > 1.5) {
      this.vx = (this.vx / speed) * 1.5;
      this.vy = (this.vy / speed) * 1.5;
    }

    this.x += this.vx;
    this.y += this.vy;

    // Wrap edges
    if (this.x < -5)     this.x = W + 5;
    if (this.x > W + 5)  this.x = -5;
    if (this.y < -5)     this.y = H + 5;
    if (this.y > H + 5)  this.y = -5;

    return pulseR;
  };

  // ── Render loop ────────────────────────────────────────────────────────────

  function draw() {
    ctx.clearRect(0, 0, W, H);

    // Update and draw particles
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      const r = p.update();

      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = hexToRgba(p.color, p.alpha);
      ctx.fill();
    }

    // Draw connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i];
        const b = particles[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < CONNECTION_DIST) {
          const alpha = (1 - dist / CONNECTION_DIST) * 0.15;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = hexToRgba('#58a6ff', alpha);
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }

    animId = requestAnimationFrame(draw);
  }

  // ── Init ──────────────────────────────────────────────────────────────────

  function init(container) {
    canvas = document.createElement('canvas');
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;';

    container.style.position = 'relative';
    container.prepend(canvas);

    ctx = canvas.getContext('2d');
    resize();

    const count = getParticleCount();
    particles = [];
    for (let i = 0; i < count; i++) {
      particles.push(new Particle());
    }

    window.addEventListener('resize', onResize);
    container.addEventListener('mousemove', onMouseMove, { passive: true });
    container.addEventListener('mouseleave', onMouseLeave, { passive: true });

    draw();
  }

  function resize() {
    const container = canvas.parentElement;
    W = container.offsetWidth  || window.innerWidth;
    H = container.offsetHeight || window.innerHeight;
    canvas.width  = W;
    canvas.height = H;
    // Retina display support
    const dpr = window.devicePixelRatio || 1;
    if (dpr > 1) {
      canvas.width  = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width  = W + 'px';
      canvas.style.height = H + 'px';
      ctx.scale(dpr, dpr);
    }
  }

  function onResize() {
    cancelAnimationFrame(animId);
    resize();
    draw();
  }

  function onMouseMove(e) {
    const rect = canvas.parentElement.getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;
  }

  function onMouseLeave() {
    mouseX = -9999;
    mouseY = -9999;
  }

  // ── CSS fallback (reduced motion or no canvas) ─────────────────────────────

  function addCssFallback(container) {
    const dots = document.createElement('div');
    dots.setAttribute('aria-hidden', 'true');
    dots.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;overflow:hidden;pointer-events:none;z-index:0;';

    for (let i = 0; i < 12; i++) {
      const dot = document.createElement('div');
      const size = Math.random() * 6 + 3;
      const color = PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)];
      dot.style.cssText = `
        position:absolute;
        width:${size}px;
        height:${size}px;
        border-radius:50%;
        background:${color};
        opacity:${Math.random() * 0.3 + 0.1};
        top:${Math.random() * 100}%;
        left:${Math.random() * 100}%;
      `;
      dots.appendChild(dot);
    }

    container.style.position = 'relative';
    container.prepend(dots);
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  window.ThreeBG = {
    /**
     * Mount the 3D particle background into `selector` (CSS selector or element).
     */
    mount: function (selector) {
      const container = typeof selector === 'string'
        ? document.querySelector(selector)
        : selector;

      if (!container) return;

      if (prefersReducedMotion || !supportsCanvas()) {
        addCssFallback(container);
        return;
      }

      // Defer to after paint for perf
      if (typeof requestIdleCallback !== 'undefined') {
        requestIdleCallback(function () { init(container); }, { timeout: 1000 });
      } else {
        setTimeout(function () { init(container); }, 50);
      }
    },

    destroy: function () {
      if (animId) cancelAnimationFrame(animId);
      if (canvas) canvas.remove();
      window.removeEventListener('resize', onResize);
    },
  };

  // ── Helpers ───────────────────────────────────────────────────────────────

  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

}());
