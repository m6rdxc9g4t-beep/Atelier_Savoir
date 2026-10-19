/* Générateur de fiches : appel à Ollama, relecture, enregistrement. */
(function () {
  'use strict';
  const form = document.getElementById('form-generation');
  if (!form) return;
  const { api, toast, renderMath } = window.Atelier;

  const el = {
    cours: document.getElementById('gen-cours'),
    chapitre: document.getElementById('gen-chapitre'),
    modele: document.getElementById('gen-modele'),
    nombre: document.getElementById('gen-nombre'),
    lancer: document.getElementById('gen-lancer'),
    attente: document.getElementById('gen-attente'),
    resultats: document.getElementById('gen-resultats'),
    liste: document.getElementById('gen-liste'),
    source: document.getElementById('gen-source'),
    compte: document.getElementById('gen-compte'),
    enregistrer: document.getElementById('gen-enregistrer'),
    relancer: document.getElementById('gen-relancer'),
    modeleFiche: document.getElementById('gen-modele-fiche'),
  };
  let derniere = null; // { chapter_id, course_id }

  // ----------------------------------------------------- listes déroulantes
  async function chargerChapitres(selection) {
    el.chapitre.innerHTML = '<option value="">Chargement…</option>';
    try {
      const course = await api(`/api/courses/${el.cours.value}`);
      if (!course.chapters.length) {
        el.chapitre.innerHTML = '<option value="">Aucun chapitre dans ce cours</option>';
        el.lancer.disabled = true;
        return;
      }
      el.chapitre.innerHTML = course.chapters.map((ch) =>
        `<option value="${ch.id}">${Atelier.escapeHtml(ch.title)} (${ch.card_count} fiches)</option>`).join('');
      if (selection) el.chapitre.value = String(selection);
      el.lancer.disabled = false;
    } catch (err) {
      toast(err.message, 'erreur');
    }
  }

  // ------------------------------------------------- moteur et modèles
  const etats = { ollama: null, claude: null };
  const moteur = () => form.querySelector('input[name="provider"]:checked')?.value || 'ollama';

  function remplirModeles() {
    const options = moteur() === 'claude'
      ? (window.CLAUDE_MODELS || []).map(([id, label]) => [id, label])
      : (etats.ollama?.models?.length ? etats.ollama.models : [form.dataset.defaultOllamaModel]).map((m) => [m, m]);
    const defaut = moteur() === 'claude' ? form.dataset.defaultClaudeModel : form.dataset.defaultOllamaModel;
    el.modele.innerHTML = options.map(([id, label]) =>
      `<option value="${Atelier.escapeHtml(id)}">${Atelier.escapeHtml(label)}</option>`).join('');
    const match = options.find(([id]) => id === defaut || id === `${defaut}:latest`);
    if (match) el.modele.value = match[0];
  }

  function afficherEtat(nom, ok, texte) {
    const cible = form.querySelector(`[data-etat-${nom}]`);
    cible.textContent = texte;
    cible.classList.toggle('is-ok', ok);
    cible.classList.toggle('is-ko', !ok);
  }

  async function chargerEtats() {
    const [ollama, claude] = await Promise.all([
      Atelier.refreshOllamaStatus(),
      api('/api/claude/status').catch(() => null),
    ]);
    etats.ollama = ollama;
    etats.claude = claude;
    if (ollama?.available) {
      afficherEtat('ollama', true, ollama.models.length ? `Prêt : ${ollama.models.length} modèle(s) installé(s)` : 'Aucun modèle installé');
    } else {
      afficherEtat('ollama', false, 'Ollama ne répond pas. Lancez l’application Ollama.');
    }
    if (claude?.available) {
      const texte = claude.subscription ? 'Prêt : connecté avec votre abonnement'
        : claude.auth_method === 'api_key' ? 'Connecté avec une clé API (facturée à l’usage)'
        : 'Prêt';
      afficherEtat('claude', true, texte);
    } else {
      afficherEtat('claude', false, claude?.error || 'Claude Code introuvable.');
    }
    remplirModeles();
  }

  form.querySelectorAll('input[name="provider"]').forEach((radio) =>
    radio.addEventListener('change', remplirModeles));

  // ------------------------------------------------------------ fiches
  function majApercu(li) {
    li.querySelector('[data-apercu-q]').textContent = li.querySelector('[data-question]').value;
    li.querySelector('[data-apercu-r]').textContent = li.querySelector('[data-reponse]').value;
    renderMath(li.querySelector('[data-apercu]'));
  }

  function majCompte() {
    const n = el.liste.querySelectorAll('[data-garder]:checked').length;
    el.compte.textContent = `${n} fiche${n > 1 ? 's' : ''} sélectionnée${n > 1 ? 's' : ''}`;
    el.enregistrer.disabled = n === 0;
  }

  function afficherFiches(cards) {
    el.liste.innerHTML = '';
    cards.forEach((card) => {
      const li = el.modeleFiche.content.firstElementChild.cloneNode(true);
      li.querySelector('[data-type]').value = card.type;
      li.querySelector('[data-question]').value = card.question;
      li.querySelector('[data-reponse]').value = card.answer;
      li.querySelectorAll('textarea').forEach((t) => t.addEventListener('change', () => majApercu(li)));
      li.querySelector('[data-garder]').addEventListener('change', (e) => {
        li.classList.toggle('opacity-50', !e.target.checked);
        majCompte();
      });
      el.liste.appendChild(li);
      majApercu(li);
    });
    majCompte();
  }

  async function generer() {
    const chapterId = el.chapitre.value;
    if (!chapterId) return toast('Choisissez un chapitre.', 'erreur');
    el.lancer.disabled = true;
    el.relancer.disabled = true;
    document.getElementById('gen-attente-texte').textContent = moteur() === 'claude'
      ? 'Claude lit le chapitre. Comptez une à deux minutes.'
      : 'Ollama lit le chapitre sur votre Mac. Comptez de quelques secondes à quelques minutes selon le modèle.';
    el.attente.classList.replace('hidden', 'flex');
    el.resultats.classList.add('hidden');
    try {
      const res = await api(`/api/chapters/${chapterId}/generate`, {
        method: 'POST',
        body: { provider: moteur(), model: el.modele.value, max_cards: Number(el.nombre.value) },
      });
      derniere = { chapter_id: res.chapter_id, course_id: res.course_id };
      if (!res.cards.length) {
        toast("Aucune nouvelle fiche trouvée dans ce chapitre. Essayez un autre modèle ou un texte plus détaillé.", 'erreur');
        return;
      }
      const n = res.cards.length;
      el.source.textContent = `${n} proposition${n > 1 ? 's' : ''} de ${res.provider_label}, modèle ${res.model}`;
      afficherFiches(res.cards);
      el.resultats.classList.remove('hidden');
      el.resultats.scrollIntoView({ block: 'start' });
    } catch (err) {
      toast(err.message, 'erreur');
    } finally {
      el.lancer.disabled = false;
      el.relancer.disabled = false;
      el.attente.classList.replace('flex', 'hidden');
    }
  }

  async function enregistrer() {
    const cards = [...el.liste.querySelectorAll('[data-fiche]')]
      .filter((li) => li.querySelector('[data-garder]').checked)
      .map((li) => ({
        question: li.querySelector('[data-question]').value.trim(),
        answer: li.querySelector('[data-reponse]').value.trim(),
        type: li.querySelector('[data-type]').value,
      }))
      .filter((c) => c.question && c.answer);
    if (!cards.length || !derniere) return;
    el.enregistrer.disabled = true;
    try {
      const res = await api('/api/flashcards', {
        method: 'POST', body: { chapter_id: derniere.chapter_id, origin: 'ia', cards },
      });
      toast(`${res.created} fiches enregistrées.`, 'succes');
      setTimeout(() => { window.location.href = `/courses/${derniere.course_id}`; }, 700);
    } catch (err) {
      toast(err.message, 'erreur');
      el.enregistrer.disabled = false;
    }
  }

  // ------------------------------------------------------------- init
  form.addEventListener('submit', (e) => { e.preventDefault(); generer(); });
  el.relancer.addEventListener('click', generer);
  el.enregistrer.addEventListener('click', enregistrer);
  el.cours.addEventListener('change', () => chargerChapitres());

  if (form.dataset.selectedCourse) el.cours.value = form.dataset.selectedCourse;
  chargerChapitres(form.dataset.selectedChapter);
  remplirModeles();
  chargerEtats();
})();
