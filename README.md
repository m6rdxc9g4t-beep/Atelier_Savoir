# Atelier Savoir

Application web **100 % locale** pour stocker ses cours, les organiser par matière et chapitre,
et en tirer automatiquement des flashcards (définitions, formules LaTeX, théorèmes, notions clés)
grâce à une IA locale (**Ollama**). Révision active façon Anki, avec répétition espacée.

Aucune donnée ne quitte la machine : polices, KaTeX et CSS sont servis localement.

## Application macOS (double-clic)

1. Installez [Ollama](https://ollama.com) puis un modèle : `ollama pull llama3.1`.
2. Dans le Finder, double-cliquez sur **`Installer Atelier Savoir.command`** à la racine du projet.
   Le script crée l'environnement Python, installe les dépendances et place
   **Atelier Savoir.app** dans `~/Applications`.
3. Ouvrez l'app depuis le Launchpad ou Spotlight, et glissez-la dans le Dock.

L'app s'ouvre dans sa propre fenêtre, démarre Ollama s'il ne tourne pas, et s'arrête proprement
à la fermeture. Elle utilise ce dossier de projet : après un `git pull`, il suffit de la relancer ;
si vous déplacez le dossier, relancez l'installeur. Journal : `~/Library/Logs/AtelierSavoir/`.

Si macOS refuse d'ouvrir le `.command` (« développeur non identifié ») : clic droit → Ouvrir,
ou dans un terminal `./macos/build_app.sh`.

## Démarrage en ligne de commande

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt

ollama serve                        # dans un autre terminal, si Ollama n'est pas déjà lancé
ollama pull llama3.1                # ou mistral, qwen2.5:7b…

python app.py                       # http://127.0.0.1:5050
python desktop.py                   # … ou dans une fenêtre d'application
```

La base `instance/savoir.db` est créée automatiquement au premier lancement
(ou avec `flask --app app init-db`).

## Deux moteurs pour générer les fiches

| Moteur | Où tourne l'IA | Coût | Confidentialité |
|--------|----------------|------|-----------------|
| **Ollama, sur votre Mac** (par défaut) | Sur votre ordinateur | Gratuit | Rien ne quitte l'ordinateur |
| **Claude, avec votre abonnement** | Chez Anthropic, via Claude Code | Inclus dans Pro / Max (compte dans les limites d'usage) | Le texte du chapitre est envoyé à Anthropic |

Le choix se fait à chaque génération ; le moteur par défaut se règle dans **Paramètres**.

Pour Claude : installez Claude Code puis connectez-vous une fois dans un terminal.

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude        # connexion avec votre compte Claude, puis /exit
```

L'app appelle `claude -p` avec une sortie JSON validée par schéma, sans aucun outil et depuis un
dossier vide (Claude Code ne lit aucun fichier). Elle retire `ANTHROPIC_API_KEY` de l'environnement
pour que l'abonnement soit utilisé plutôt qu'une facturation à l'usage.

## Utilisation

1. **Mes cours** : créez un cours, puis importez des chapitres (PDF, Markdown, TXT, ou texte collé).
2. **Générateur IA** : choisissez le moteur (Ollama ou Claude), un chapitre et un modèle. L'IA propose
   des fiches ; relisez, corrigez, décochez, puis enregistrez.
3. **Révision** : retournez la fiche (clic ou `Espace`), puis évaluez-vous :
   `1` À revoir, `2` Correct, `3` Maîtrisé.
4. **Paramètres** : adresse d'Ollama, modèle par défaut, nombre de fiches par chapitre, thème.

## Architecture

```
Atelier_Savoir/
├── app.py                  # Fabrique Flask, navigation, filtres Jinja
├── desktop.py              # Lanceur bureau : serveur + Ollama + fenêtre native (pywebview)
├── Installer Atelier Savoir.command  # Installeur macOS (double-clic)
├── macos/                  # build_app.sh (construit le .app), icon.png
├── config.py               # Configuration (surchargeable par variables d'environnement)
├── database.py             # Connexion SQLite, schéma versionné (PRAGMA user_version)
├── models.py               # Accès aux données : cours, chapitres, fiches, révisions, réglages
├── routes/
│   ├── pages.py            # Vues HTML : /, /courses, /flashcards/generate, /study, /settings
│   └── api.py              # API REST JSON (/api/…)
├── services/
│   ├── flashcard_generator.py # Prompt système strict, découpage, parseur JSON tolérant (commun)
│   ├── ollama_service.py   # Moteur Ollama (local)
│   ├── claude_service.py   # Moteur Claude via Claude Code (abonnement)
│   ├── text_extraction.py  # Extraction PDF/MD/TXT, nettoyage, découpage en blocs
│   ├── spaced_repetition.py# Planification SM-2 simplifiée
│   └── settings_service.py # Réglages persistants et fabrique du client Ollama
├── templates/              # Jinja + Tailwind (base, tableau de bord, cours, générateur, révision…)
├── static/
│   ├── css/                # app.css (composants, fiche bristol), tailwind.css (compilé), fonts.css
│   ├── js/                 # app.js (commun), course.js, generate.js, study.js
│   ├── fonts/              # Literata, Instrument Sans (SIL OFL)
│   └── vendor/katex/       # Rendu des formules LaTeX
├── tests/test_app.py       # Tests pytest (Ollama simulé)
├── instance/               # savoir.db (ignoré par Git)
└── uploads/                # Fichiers de cours originaux (ignorés par Git)
```

### Modèle de données

| Table        | Rôle                                                                 |
|--------------|----------------------------------------------------------------------|
| `courses`    | Cours (titre, matière, description)                                  |
| `chapters`   | Chapitres d'un cours : texte extrait + fichier source                |
| `flashcards` | Question, réponse, type (`definition`, `formule`, `theoreme`, `notion`), origine (`ia`/`manuel`) et état de répétition (facilité, intervalle, échéance, statut) |
| `reviews`    | Historique des évaluations (`a_revoir`, `correct`, `maitrise`)       |
| `settings`   | Réglages modifiés depuis l'interface                                 |

### API REST

| Méthode | Route                                   | Rôle                                         |
|---------|-----------------------------------------|----------------------------------------------|
| GET/POST| `/api/courses`                          | Lister / créer un cours                      |
| GET/PATCH/DELETE | `/api/courses/<id>`            | Détail (avec chapitres) / modifier / supprimer |
| POST    | `/api/courses/<id>/chapters`            | Importer un chapitre (`file` multipart ou `content`) |
| GET/DELETE | `/api/chapters/<id>`                 | Lire / supprimer un chapitre                 |
| POST    | `/api/chapters/<id>/generate`           | Proposer des fiches (`provider` : `ollama` ou `claude`, `model`) |
| GET/POST| `/api/flashcards`                       | Lister / enregistrer des fiches (lot)        |
| PATCH/DELETE | `/api/flashcards/<id>`             | Modifier / supprimer une fiche               |
| POST    | `/api/flashcards/<id>/review`           | Évaluer une fiche (`rating`)                 |
| GET     | `/api/study/session?course_id=&mode=`   | File de révision (`dues` ou `toutes`)        |
| GET     | `/api/stats`, `/api/ollama/status`, `/api/claude/status` | Statistiques, état des moteurs |
| GET/PUT | `/api/settings`                         | Réglages                                     |

### Génération des fiches

- Les deux moteurs partagent le prompt système et le schéma `{"flashcards": [{"question", "answer", "type"}]}` :
  Ollama via `POST /api/chat` (`format` = schéma), Claude via `claude -p --json-schema`.
- Les longs chapitres sont découpés en blocs (`ATELIER_CHUNK_CHARS`, 6000 caractères par défaut)
  sans couper les formules `$$…$$`.
- Le parseur répare les antislashs LaTeX mal échappés (`\frac`, `\theta`, `\sigma`…) et ignore
  les questions déjà présentes dans le chapitre.

## Développement

```bash
pytest -q                 # tests (aucun Ollama requis)
npm install && npm run css    # recompiler Tailwind après modification des templates
npm run css:watch             # … ou en continu
```

`static/css/tailwind.css` est versionné : Node n'est nécessaire que pour modifier le style.

### Variables d'environnement

`OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`, `ATELIER_CARDS_PER_CHAPTER`, `ATELIER_CHUNK_CHARS`,
`ATELIER_AI_PROVIDER` (`ollama` ou `claude`), `ATELIER_CLAUDE_MODEL` (`sonnet`, `opus`, `haiku`),
`ATELIER_CLAUDE_TIMEOUT`, `CLAUDE_PATH` (emplacement de Claude Code s'il n'est pas trouvé),
`ATELIER_DB`, `ATELIER_UPLOADS`, `ATELIER_PORT` (5050 ; le port 5000 est pris par AirPlay sur macOS), `SECRET_KEY` (voir `.env.example`). Les réglages enregistrés depuis
`/settings` priment sur ces valeurs.
