/* Page d'un cours : import de chapitre (fichier ou texte) et ajout manuel de fiches. */
(function () {
  'use strict';
  const { api, toast } = window.Atelier;

  // -------------------------------------------------- import de chapitre
  const form = document.getElementById('form-import');
  if (form) {
    const courseId = form.dataset.course;
    const fileInput = document.getElementById('chapitre-fichier');
    const fileName = form.querySelector('[data-file-name]');
    const depot = form.querySelector('.depot');
    let mode = 'fichier';

    const setMode = (next) => {
      mode = next;
      form.querySelectorAll('[role="tab"]').forEach((tab) => {
        const on = tab.dataset.mode === mode;
        tab.setAttribute('aria-selected', String(on));
        tab.classList.toggle('bg-white', on);
        tab.classList.toggle('dark:bg-sombre-eleve', on);
        tab.classList.toggle('shadow-sm', on);
      });
      form.querySelectorAll('[data-only]').forEach((el) => { el.hidden = el.dataset.only !== mode; });
    };
    form.querySelectorAll('[role="tab"]').forEach((tab) => tab.addEventListener('click', () => setMode(tab.dataset.mode)));
    setMode('fichier');

    const showFile = () => {
      fileName.textContent = fileInput.files[0] ? fileInput.files[0].name : 'Déposez un fichier ici';
    };
    fileInput.addEventListener('change', showFile);
    ['dragenter', 'dragover'].forEach((type) => depot.addEventListener(type, (e) => {
      e.preventDefault();
      depot.classList.add('is-over');
    }));
    ['dragleave', 'drop'].forEach((type) => depot.addEventListener(type, () => depot.classList.remove('is-over')));
    depot.addEventListener('drop', (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        showFile();
      }
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = e.submitter;
      const data = new FormData();
      data.append('title', form.title.value.trim());
      if (mode === 'fichier') {
        if (!fileInput.files[0]) return toast('Choisissez un fichier à importer.', 'erreur');
        data.append('file', fileInput.files[0]);
      } else {
        if (!form.content.value.trim()) return toast('Collez le texte du chapitre.', 'erreur');
        if (!form.title.value.trim()) return toast('Donnez un titre au chapitre.', 'erreur');
        data.append('content', form.content.value);
      }
      btn.disabled = true;
      btn.textContent = 'Import en cours…';
      try {
        const chapter = await api(`/api/courses/${courseId}/chapters`, { method: 'POST', body: data });
        toast(`Chapitre « ${chapter.title} » importé.`, 'succes');
        setTimeout(() => window.location.reload(), 500);
      } catch (err) {
        toast(err.message, 'erreur');
        btn.disabled = false;
        btn.textContent = 'Importer le chapitre';
      }
    });
  }

  // ------------------------------------------------------- fiche manuelle
  document.querySelectorAll('[data-toggle-form]').forEach((btn) => btn.addEventListener('click', () => {
    const target = document.getElementById(btn.dataset.toggleForm);
    target.classList.toggle('hidden');
    if (!target.classList.contains('hidden')) target.querySelector('input, textarea')?.focus();
  }));

  const ficheForm = document.getElementById('form-fiche');
  if (ficheForm) {
    ficheForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const values = Object.fromEntries(new FormData(ficheForm));
      const body = {
        course_id: Number(ficheForm.dataset.course),
        chapter_id: values.chapter_id ? Number(values.chapter_id) : null,
        origin: 'manuel',
        cards: [{ question: values.question, answer: values.answer, type: values.type }],
      };
      try {
        await api('/api/flashcards', { method: 'POST', body });
        toast('Fiche enregistrée.', 'succes');
        setTimeout(() => window.location.reload(), 400);
      } catch (err) {
        toast(err.message, 'erreur');
      }
    });
  }
})();
