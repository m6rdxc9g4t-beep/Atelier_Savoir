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
- 100 % local par défaut : aucune ressource externe (CDN, polices en ligne). Ajouter les dépendances front dans `static/vendor/`.
- IA : deux moteurs (`services/ollama_service.py` local, `services/claude_service.py` via Claude Code et l'abonnement)
  qui n'implémentent que `complete_json()` ; prompt strict, `FLASHCARD_SCHEMA` et parseur restent communs
  dans `services/flashcard_generator.py`. Ollama reste le moteur par défaut (100 % local).
- Moteur Claude : jamais de clé API (retirer `ANTHROPIC_API_KEY` de l'environnement), aucun outil (`--tools ""`),
  lancement depuis un dossier vide.
- Charte « néon monochrome » de la suite : `static/brand/atelier-brand.css` est une copie exacte
  (ne pas l'éditer ici) ; `data-atelier-app="savoir"` sur `<html>` pose la couleur signature violette `#9B5DE5`.
  Toute l'app est dans ce violet, en clair comme en sombre : aucun bleu nuit ni cyan de structure.
- Couleurs : uniquement les jetons `--atelier-*` (branchés dans `static/css/app.css`) et leurs alias Tailwind
  `fond`, `surface`, `surface-2`, `selection`, `survol`, `texte`, `doux`, `encre` (texte en signature), `bord`,
  `bord-doux`, `ligne`, `signature` ; ils changent de valeur avec `.dark`, donc pas de variante `dark:`.
  Couleurs de sens inchangées : `ambre` (en cours, avertissement), `emeraude` (maîtrise), `framboise` (à revoir).
- La fiche bristol (`.fiche-lignes` dans `static/css/app.css`) est l'élément signature : ne pas la banaliser.
