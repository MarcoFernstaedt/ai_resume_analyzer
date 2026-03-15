/* =========================================================
   DevResume AI - Main JS
   Animations, interactions, accessibility
   ========================================================= */

'use strict';

// ─── Mobile Sidebar ───────────────────────────────────────
const hamburger = document.getElementById('hamburger');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('mobile-overlay');

function toggleSidebar() {
  const open = sidebar.classList.toggle('open');
  overlay.classList.toggle('active', open);
  hamburger?.setAttribute('aria-expanded', open.toString());
  if (open) sidebar.querySelector('a')?.focus();
}

hamburger?.addEventListener('click', toggleSidebar);
overlay?.addEventListener('click', toggleSidebar);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && sidebar?.classList.contains('open')) toggleSidebar();
});

// ─── File Drop Zone ───────────────────────────────────────
const dropZone = document.querySelector('.file-drop');
if (dropZone) {
  const input = dropZone.querySelector('input[type="file"]');
  const label = dropZone.querySelector('.file-drop-text');

  ['dragenter', 'dragover'].forEach(e =>
    dropZone.addEventListener(e, (ev) => { ev.preventDefault(); dropZone.classList.add('dragover'); })
  );
  ['dragleave', 'drop'].forEach(e =>
    dropZone.addEventListener(e, () => dropZone.classList.remove('dragover'))
  );
  dropZone.addEventListener('drop', (ev) => {
    ev.preventDefault();
    const files = ev.dataTransfer.files;
    if (files.length && input) {
      const dt = new DataTransfer();
      dt.items.add(files[0]);
      input.files = dt.files;
      updateFileName(files[0].name);
    }
  });

  input?.addEventListener('change', (e) => {
    if (e.target.files.length) updateFileName(e.target.files[0].name);
  });

  function updateFileName(name) {
    if (label) label.innerHTML = `<strong>Selected:</strong> ${escapeHtml(name)}`;
    dropZone.style.borderColor = 'var(--accent-green)';
  }
}

// ─── Score Ring Animation ─────────────────────────────────
document.querySelectorAll('.score-ring[data-score]').forEach(ring => {
  const score = parseInt(ring.dataset.score, 10);
  const circle = ring.querySelector('.score-circle');
  if (!circle) return;
  const r = parseFloat(circle.getAttribute('r'));
  const circumference = 2 * Math.PI * r;
  circle.style.strokeDasharray = circumference;
  circle.style.strokeDashoffset = circumference;
  const color = score >= 80 ? '#3fb950' : score >= 60 ? '#d29922' : '#f85149';
  circle.setAttribute('stroke', color);

  setTimeout(() => {
    const offset = circumference - (score / 100) * circumference;
    circle.style.transition = 'stroke-dashoffset 1.2s ease';
    circle.style.strokeDashoffset = offset;
  }, 300);
});

// ─── Progress Bar Animate ─────────────────────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const bar = entry.target;
      const target = bar.dataset.width || '0';
      bar.style.width = target + '%';
      observer.unobserve(bar);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.progress-bar[data-width]').forEach(bar => {
  bar.style.width = '0%';
  observer.observe(bar);
});

// ─── Typing Effect ────────────────────────────────────────
function typeWriter(el, text, speed = 40, delay = 0) {
  setTimeout(() => {
    let i = 0;
    el.textContent = '';
    el.classList.remove('typewriter');
    const interval = setInterval(() => {
      el.textContent += text[i];
      i++;
      if (i >= text.length) clearInterval(interval);
    }, speed);
  }, delay);
}

document.querySelectorAll('[data-typewriter]').forEach((el, idx) => {
  const text = el.dataset.typewriter;
  typeWriter(el, text, 50, idx * 200);
});

// ─── Animate on scroll ───────────────────────────────────
const fadeObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('animate-fadeInUp');
      fadeObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.05 });

document.querySelectorAll('.card, .stat-card, .question-card').forEach(el => {
  el.style.opacity = '0';
  fadeObserver.observe(el);
});

// ─── Tech Tag Selection (Assessment) ─────────────────────
document.querySelectorAll('.tech-tag-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    btn.classList.toggle('selected');
    const tech = btn.dataset.tech;
    const hidden = document.getElementById('tech-stack-hidden');
    if (!hidden) return;
    let techs = hidden.value ? hidden.value.split(',').filter(Boolean) : [];
    if (btn.classList.contains('selected')) {
      techs.push(tech);
    } else {
      techs = techs.filter(t => t !== tech);
    }
    hidden.value = techs.join(',');
    // Update visual count
    const counter = document.getElementById('selected-count');
    if (counter) counter.textContent = techs.length;
  });
});

// ─── Auto-dismiss messages ────────────────────────────────
document.querySelectorAll('.alert[data-auto-dismiss]').forEach(alert => {
  setTimeout(() => {
    alert.style.transition = 'opacity 0.5s ease';
    alert.style.opacity = '0';
    setTimeout(() => alert.remove(), 500);
  }, 4000);
});

// ─── Copy to clipboard ───────────────────────────────────
document.querySelectorAll('[data-copy]').forEach(btn => {
  btn.addEventListener('click', async () => {
    const text = document.querySelector(btn.dataset.copy)?.textContent;
    if (!text) return;
    await navigator.clipboard.writeText(text);
    const orig = btn.textContent;
    btn.textContent = '✓ Copied!';
    setTimeout(() => btn.textContent = orig, 2000);
  });
});

// ─── Form submit loading state ────────────────────────────
document.querySelectorAll('form[data-loading]').forEach(form => {
  form.addEventListener('submit', () => {
    const btn = form.querySelector('button[type="submit"]');
    if (btn && !btn.dataset.noLoading) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Processing...';
    }
  });
});

// ─── Salary range display ─────────────────────────────────
const salMin = document.getElementById('id_salary_min');
const salMax = document.getElementById('id_salary_max');
const salDisplay = document.getElementById('salary-display');
if (salMin && salMax && salDisplay) {
  const update = () => {
    const min = parseInt(salMin.value || 0);
    const max = parseInt(salMax.value || 0);
    if (min || max) {
      salDisplay.textContent = `$${min.toLocaleString()} – $${max.toLocaleString()}`;
    }
  };
  salMin.addEventListener('input', update);
  salMax.addEventListener('input', update);
}

// ─── Smooth counter animation ─────────────────────────────
document.querySelectorAll('.stat-value[data-count]').forEach(el => {
  const target = parseInt(el.dataset.count, 10);
  const duration = 1200;
  const start = performance.now();
  const initial = parseInt(el.textContent) || 0;

  const animate = (time) => {
    const elapsed = time - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(initial + (target - initial) * eased);
    if (progress < 1) requestAnimationFrame(animate);
  };
  requestAnimationFrame(animate);
});

// ─── Util ─────────────────────────────────────────────────
function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}
