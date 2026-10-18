/* Espace de révision : fiche à retourner, évaluation, file de la séance.
   Raccourcis : Espace/Entrée = retourner, 1 = À revoir, 2 = Correct, 3 = Maîtrisé. */
(function () {
  'use strict';
  const { api, toast, renderMath } = window.Atelier;
  const LABELS = window.CARD_TYPE_LABELS || {};

  const $ = (sel) => document.querySelector(sel);
  const zone = $('#rev-zone');
  const fiche = $('#rev-fiche');
  const inner = fiche.querySelector('.fiche-inner');
  const notes = $('#rev-notes');
  const vide = $('#rev-vide');
  const bilan = $('#rev-bilan');
  const selCours = $('#rev-cours');
  const selMode = $('#rev-mode');

  let file = [];       // cartes restantes
  let total = 0;       // nombre de passages prévus
  let faits = 0;
  let courante = null;
  let occupe = false;
  let compte = { a_revoir: 0, correct: 0, maitrise: 0 };

  function majProgression() {
    $('#rev-compteur').textContent = `${faits} / ${total}`;
    $('#rev-progression').style.width = total ? `${Math.round((100 * faits) / total)}%` : '0%';
  }

  function retourner(force) {
    if (!courante) return;
    const flipped = typeof force === 'boolean' ? force : !fiche.classList.contains('is-flipped');
    fiche.classList.toggle('is-flipped', flipped);
    notes.classList.toggle('invisible', !flipped);
    inner.setAttribute('aria-label', flipped ? 'Réponse affichée' : 'Question affichée');
  }

  function afficher(card, focus = true) {
    courante = card;
    if (fiche.classList.contains('is-flipped')) {
      // Remise à plat instantanée : la réponse suivante ne doit pas apparaître pendant l'animation
      inner.style.transition = 'none';
      fiche.classList.remove('is-flipped');
      void inner.offsetWidth;
      inner.style.transition = '';
    }
    notes.classList.add('invisible');
    fiche.querySelector('[data-type]').textContent = LABELS[card.card_type] || 'Notion';
    fiche.querySelector('[data-contexte]').textContent = card.chapter_title || card.course_title;
    fiche.querySelector('[data-question]').textContent = card.question;
    fiche.querySelector('[data-question-rappel]').textContent = card.question;
    fiche.querySelector('[data-reponse]').textContent = card.answer;
    inner.setAttribute('aria-label', 'Question affichée');
    renderMath(fiche);
    if (focus) inner.focus({ preventScroll: true });
  }

  function montrerVide(titre, texte, actions) {
    zone.classList.add('hidden');
    bilan.classList.add('hidden');
    vide.classList.remove('hidden');
    vide.querySelector('[data-titre]').textContent = titre;
    vide.querySelector('[data-texte]').textContent = texte;
    vide.querySelector('[data-actions]').innerHTML = actions;
  }

  function terminer() {
    courante = null;
    zone.classList.add('hidden');
    Object.entries(compte).forEach(([k, v]) => { bilan.querySelector(`[data-bilan="${k}"]`).textContent = v; });
    bilan.classList.remove('hidden');
  }

  async function demarrer() {
    vide.classList.add('hidden');
    bilan.classList.add('hidden');
    compte = { a_revoir: 0, correct: 0, maitrise: 0 };
    faits = 0;
    const page = new URLSearchParams({ mode: selMode.value });
    if (selCours.value) page.set('course_id', selCours.value);
    history.replaceState(null, '', `/study?${page}`);
    const params = new URLSearchParams(page);
    params.set('limit', '30');
    try {
      const res = await api(`/api/study/session?${params}`);
      file = res.cards;
    } catch (err) {
      return toast(err.message, 'erreur');
    }
    total = file.length;
    majProgression();
    if (!file.length) {
      if (selMode.value === 'dues') {
        return montrerVide('Rien à revoir pour le moment',
          'Vos fiches reviendront au moment opportun. Vous pouvez aussi réviser librement.',
          '<button class="btn btn-primary" type="button" data-libre>Réviser librement</button>');
      }
      return montrerVide('Aucune fiche dans ce périmètre',
        'Importez un chapitre puis générez vos premières fiches.',
        '<a class="btn btn-primary" href="/flashcards/generate">Générer des fiches</a>');
    }
    zone.classList.remove('hidden');
    afficher(file.shift(), false);
  }

  async function noter(note) {
    if (!courante || occupe || !fiche.classList.contains('is-flipped')) return;
    occupe = true;
    const card = courante;
    try {
      await api(`/api/flashcards/${card.id}/review`, { method: 'POST', body: { rating: note } });
    } catch (err) {
      occupe = false;
      return toast(err.message, 'erreur');
    }
    compte[note] += 1;
    faits += 1;
    if (note === 'a_revoir') {
      // La carte revient en fin de séance
      file.push(card);
      total += 1;
    }
    majProgression();
    occupe = false;
    if (file.length) afficher(file.shift());
    else terminer();
  }

  // ------------------------------------------------------------ événements
  inner.addEventListener('click', () => retourner());
  notes.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-note]');
    if (btn) noter(btn.dataset.note);
  });
  document.addEventListener('keydown', (e) => {
    if (e.target.closest('select, input, textarea') || zone.classList.contains('hidden')) return;
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      retourner();
    } else if (e.key === '1') noter('a_revoir');
    else if (e.key === '2') noter('correct');
    else if (e.key === '3') noter('maitrise');
  });
  selCours.addEventListener('change', demarrer);
  selMode.addEventListener('change', demarrer);
  bilan.querySelector('[data-recommencer]').addEventListener('click', demarrer);
  vide.addEventListener('click', (e) => {
    if (e.target.closest('[data-libre]')) {
      selMode.value = 'toutes';
      demarrer();
    }
  });

  demarrer();
})();
