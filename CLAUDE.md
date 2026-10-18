# CLAUDE.md — Atelier_Savoir

Contexte de référence : `specifications.md` (produit, design) et `instructions.md` (workflow Git).

## Commandes
- Lancer : `python app.py` (http://127.0.0.1:5050) ou `python desktop.py` (fenêtre native)
- App macOS : `./macos/build_app.sh` reconstruit et réinstalle `~/Applications/Atelier Savoir.app`
- Tests : `pytest -q` — Ollama est simulé via `OLLAMA_CLIENT_FACTORY`, aucun serveur requis
- CSS : `npm run css` après toute modification de classes Tailwind dans `templates/` ou `static/js/`

## Conventions
- Langue : interface, messages d'erreur et commentaires en français.
- Branches `feature/...`, commits conventionnels (`feat(ai): …`, `fix(study): …`).
- Couches : `routes/` (HTTP uniquement) → `models.py` (SQL) → `services/` (logique métier, Ollama).
- Base : ne jamais modifier une migration existante ; ajouter une entrée à `MIGRATIONS` dans `database.py`.
- 100 % local : aucune ressource externe (CDN, polices en ligne). Ajouter les dépendances front dans `static/vendor/`.
- Ollama : garder la sortie structurée (`FLASHCARD_SCHEMA`) et le prompt système strict de `services/ollama_service.py`.
- Couleurs : `nuit` (fond), `ambre` (mémorisation, actions), `emeraude` (maîtrise), `framboise` (à revoir).
- La fiche bristol (`.fiche-lignes` dans `static/css/app.css`) est l'élément signature : ne pas la banaliser.
