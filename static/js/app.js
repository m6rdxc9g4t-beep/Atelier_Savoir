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
    el.dataset.kind = kind;
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
  // Préférence commune à la suite : static/brand/atelier-theme.js (window.atelierTheme),
  // valeurs « system », « light », « dark ». Les sélecteurs [data-theme-choice] la reflètent.
  function getTheme() {
    return window.atelierTheme ? window.atelierTheme.get() : 'system';
  }

  function setTheme(pref) {
    if (window.atelierTheme) window.atelierTheme.set(pref);
  }

  function syncThemeControls() {
    const pref = getTheme();
    document.querySelectorAll('[data-theme-choice]').forEach((b) => {
      b.setAttribute(b.getAttribute('role') === 'radio' ? 'aria-checked' : 'aria-pressed',
        String(b.dataset.themeChoice === pref));
    });
  }

  // -------------------------------------------------------- statut Ollama
  // Témoin muet : rien de coloré quand Ollama répond avec son modèle ; ambre ou rouge sinon.
  async function refreshOllamaStatus() {
    const box = document.querySelector('[data-ollama-status]');
    const label = document.querySelector('[data-ollama-label]');
    if (!box || !label) return null;
    try {
      const s = await api('/api/ollama/status');
      if (s.available) {
        box.dataset.etat = s.model_installed ? 'ok' : 'partiel';
        label.textContent = s.model_installed ? `Ollama : ${s.model}` : `Modèle ${s.model} absent`;
      } else {
        box.dataset.etat = 'panne';
        label.textContent = 'Ollama hors ligne';
      }
      return s;
    } catch (e) {
      return null;
    }
  }

  // --------------------------------------------------------- init commune
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-theme-choice]').forEach((b) =>
      b.addEventListener('click', () => setTheme(b.dataset.themeChoice)));
    window.addEventListener('atelier-theme', syncThemeControls);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) syncThemeControls(); });
    syncThemeControls();

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
