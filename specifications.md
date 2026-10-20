# Spécifications Techniques - Atelier_Savoir

## 1. Vue d'ensemble du projet
**Atelier_Savoir** est une application web locale et intelligente dédiée au stockage de cours, à l'organisation des connaissances et à la génération automatique de flashcards (notions clés, définitions, formules scientifiques en LaTeX comme $E = mc^2$, théorèmes) grâce à une **IA locale (Ollama)**. Le code est versionné sur GitHub et structuré pour être piloté via **Claude CLI**.

---

## 2. Architecture Technique
- **Backend :** Python (Flask)
  - Gestion de la base de données relationnelle (SQLite / `savoir.db`) pour stocker les cours, chapitres et flashcards.
  - API REST pour l'import de documents (Markdown, TXT, PDF) et l'interrogation d'Ollama.
  - Intégration Ollama (API locale `http://localhost:11434`) pour analyser le contenu des cours et extraire automatiquement les flashcards pertinentes.
- **Frontend :** HTML5, Tailwind CSS, JavaScript moderne
  - Interface utilisateur épurée et moderne, adaptée aux révisions intensives (Mode sombre / clair).
  - Mode révision interactif (système de cartes à retourner type Anki) avec suivi de progression.
- **Dépôt GitHub :** Versioning complet, gestion des branches par fonctionnalités (`feature/...`) et automatisation via Claude CLI.

---

## 3. Design UI / UX & Visuels
- **Palette de couleurs :** Charte « néon holographique 3D » de la suite Atelier : bleu nuit profond, structure en cyan électrique (halos et reflets en mode sombre), couleur signature violette `#9B5DE5` (réflexion) pour les actions et repères ; ambre pour les fiches en cours, vert émeraude pour les notions maîtrisées, framboise pour les fiches à revoir.
- **Navigation principale (Sidebar) :**
  - Tableau de bord / Accueil (`/`)
  - Mes Cours & Documents (`/courses`)
  - Générateur de Flashcards IA (`/flashcards/generate`)
  - Espace de Révision (`/study`)
  - Paramètres & Modèle Ollama (`/settings`)
- **Écran de Révision des Flashcards (Mode Anki Local) :**
  - Carte interactive centrale avec effet 3D flip (Recto : Question / Notion / Formule $ \int f(x)dx $ ; Verso : Définition / Réponse).
  - Boutons d'évaluation : "À revoir", "Correct", "Maîtrisé".

---

## 4. Fonctionnalités Clés
1. **Bibliothèque de cours :** Dépôt et indexation locale des cours par matière/chapitre.
2. **Extraction Intelligente par Ollama :** Analyse du texte du cours pour isoler automatiquement les définitions et formules mathématiques ou physiques.
3. **Révision active :** Interface de flashcards gamifiée et 100% locale (confidentialité totale des cours).
4. **Intégration Claude CLI :** Pilotage du développement, ajout de fonctionnalités de mémorisation espérée, et gestion des commits GitHub.
