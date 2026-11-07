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
- Charte v2 « Linear » de la suite (règles : `Atelier_Deploy/DESIGN.md`, `Atelier_Projets/docs/SUITE.md` §1) :
  `static/brand/` (`atelier-brand.css`, `atelier-theme.js`, police Inter et sa licence) est une copie exacte
  de `Atelier_Projets/design-system/brand/` (ne pas l'éditer ici). `data-atelier-app="savoir"` sur `<html>` pose
  la signature `#a853c1`, qui ne sert qu'à l'accent (bouton principal, sélection, focus, liens, progression, icône).
  Structure commune crème en clair, bleu nuit en sombre, plate au repos, traits de 1 px, Inter partout, base 13 px
  (14 px sur téléphone). Fond fixe de la fenêtre pywebview (`desktop.window_background`) : `#f8f4ec` / `#0b1220`.
  Chiffres clés (tableau de bord, bilan de séance) : rangée `.kpis` de cartes `.atelier-kpi` (coins de 12 px).
  Pas de halo, de grille de fond, de lueur ni de barre de couleur latérale.
- Thème : `atelier-theme.js` est chargé en premier dans `<head>` ; préférence commune à la suite
  (`window.atelierTheme.get/set`, événement `atelier-theme`, valeurs `system` / `light` / `dark`).
- Couleurs : uniquement les jetons `--atelier-*` (branchés dans `static/css/app.css`) et leurs alias Tailwind
  `fond`, `barre`, `surface`, `surface-2`, `selection`, `survol`, `texte`, `doux`, `discret`, `bord`, `bord-doux`,
  `ligne`, `signature`, `encre` (texte en signature), `attention` et `erreur` (états anormaux seulement) ;
  ils changent de valeur avec `.dark`, donc pas de variante `dark:`. Tailles de texte et rayons : échelle de
  `tailwind.config.js` (variables `--t-*`, `--atelier-radius-*`).
  Couleurs de sens inchangées : `ambre` (en cours), `emeraude` (maîtrise), `framboise` (à revoir) ; en texte,
  pastille fine ou barre, leurs variantes `--*-fort` / `--ambre-pastille` de `app.css` (contrastes vérifiés sur crème et bleu nuit).
- La fiche bristol (`.fiche-lignes` dans `static/css/app.css`) est l'élément signature : ne pas la banaliser.
- Icônes : `static/img/favicon.svg` (source), `favicon-64.png`, `apple-touch-icon.png` et `macos/icon.png`
  sont l'icône carrée de l'app (dégradé de la signature, glyphe Lucide `graduation-cap` blanc).
