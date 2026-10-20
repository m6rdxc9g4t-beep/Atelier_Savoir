/* Atelier Savoir — utilitaires communs à toutes les pages. */
(function () {
  'use strict';

  // ------------------------------------------------------------- API JSON
  async function api(path, options = {}) {
    const opts = { ...options, headers: { ...(options.headers || {}) } };
    if (opts.body && !(opts.body instanceof FormData) && typeof opts.body !== 'string') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    let response;
    try {
      response = await fetch(path, opts);
    } catch (e) {
      throw new Error("Le serveur Atelier Savoir ne répond pas. Est-il toujours lancé ?");
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Erreur ${response.status}`);
    return data;
  }

  // ---------------------------------------------------------------- toast
  let toastTimer;
  function toast(message, kind = 'info') {
    const el = document.getElementById('toast');
    if (!el) return;
    const styles = {
      info: 'bg-selection text-texte',
      succes: 'bg-emeraude-600 text-white',
      erreur: 'bg-framboise-600 text-white',
    };
    el.className = el.className.replace(/\b(bg|text)-\S+/g, '').trim() + ' ' + (styles[kind] || styles.info);
    el.textContent = message;
    el.style.opacity = '1';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.style.opacity = '0'; }, kind === 'erreur' ? 6000 : 3000);
  }

  // ------------------------------------------------------- formules KaTeX
  function renderMath(root) {
    const target = root || document.body;
    const run = () => {
      if (!window.renderMathInElement) return false;
      window.renderMathInElement(target, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '\\[', right: '\\]', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
        ],
        throwOnError: false,
        ignoredClasses: ['no-math'],
        ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'option', 'select', 'input'],
      });
      return true;
    };
    if (!run()) window.addEventListener('load', run, { once: true });
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  // ---------------------------------------------------------------- thème
  const THEMES = ['systeme', 'clair', 'sombre'];
  const THEME_LABELS = { systeme: 'système', clair: 'clair', sombre: 'sombre' };

  function getTheme() {
    try { return localStorage.getItem('atelier-theme') || 'systeme'; } catch (e) { return 'systeme'; }
  }

  function applyTheme(pref) {
    const dark = pref === 'sombre' ||
      (pref === 'systeme' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('dark', dark);
    document.querySelectorAll('[data-theme-label]').forEach((el) => { el.textContent = THEME_LABELS[pref]; });
  }

  function setTheme(pref) {
    try { localStorage.setItem('atelier-theme', pref); } catch (e) { /* stockage indisponible */ }
    applyTheme(pref);
    document.dispatchEvent(new CustomEvent('atelier:theme', { detail: pref }));
  }

  // -------------------------------------------------------- statut Ollama
  async function refreshOllamaStatus() {
    const dot = document.querySelector('[data-ollama-dot]');
    const label = document.querySelector('[data-ollama-label]');
    if (!dot || !label) return null;
    try {
      const s = await api('/api/ollama/status');
      if (s.available) {
        dot.className = 'h-2 w-2 rounded-full ' + (s.model_installed ? 'bg-emeraude-400' : 'bg-ambre-400');
        label.textContent = s.model_installed ? `Ollama : ${s.model}` : `Modèle ${s.model} absent`;
      } else {
        dot.className = 'h-2 w-2 rounded-full bg-framboise-400';
        label.textContent = 'Ollama hors ligne';
      }
      return s;
    } catch (e) {
      return null;
    }
  }

  // --------------------------------------------------------- init commune
  document.addEventListener('DOMContentLoaded', () => {
    applyTheme(getTheme());
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (getTheme() === 'systeme') applyTheme('systeme');
    });
    document.querySelectorAll('[data-theme-cycle]').forEach((btn) => btn.addEventListener('click', () => {
      const next = THEMES[(THEMES.indexOf(getTheme()) + 1) % THEMES.length];
      setTheme(next);
    }));

    const sidebar = document.getElementById('sidebar');
    const backdrop = document.querySelector('[data-sidebar-backdrop]');
    const toggle = document.querySelector('[data-sidebar-toggle]');
    const setOpen = (open) => {
      sidebar.classList.toggle('is-open', open);
      backdrop.classList.toggle('hidden', !open);
      toggle?.setAttribute('aria-expanded', String(open));
    };
    toggle?.addEventListener('click', () => setOpen(!sidebar.classList.contains('is-open')));
    backdrop?.addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setOpen(false); });

    // Confirmation + suppression génériques : <button data-delete="/api/..." data-confirm="...">
    document.body.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-delete]');
      if (!btn) return;
      if (btn.dataset.confirm && !window.confirm(btn.dataset.confirm)) return;
      try {
        await api(btn.dataset.delete, { method: 'DELETE' });
        if (btn.dataset.redirect) window.location.href = btn.dataset.redirect;
        else window.location.reload();
      } catch (err) {
        toast(err.message, 'erreur');
      }
    });

    renderMath(document.querySelector('main'));
    refreshOllamaStatus();
  });

  window.Atelier = { api, toast, renderMath, escapeHtml, setTheme, getTheme, refreshOllamaStatus };
})();
