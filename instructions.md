# Instructions pour Claude CLI - Atelier_Savoir

Ce document sert de guide de référence et de contexte pour toutes les interactions avec **Claude CLI** lors du développement du projet **Atelier_Savoir** hébergé sur GitHub.

## 1. Contexte et Objectif

Tu assistes le développeur dans la création et l'évolution de l'application **Atelier_Savoir**. La stack repose sur un backend Python (Flask), une base SQLite, un frontend moderne (Tailwind CSS), et une intégration d'IA locale (Ollama) pour la génération de flashcards pédagogiques.

## 2. Workflow Git & Claude CLI Recommandé

* **Création d'une branche de travail :**

  ```bash
  git checkout -b feature/nom-de-la-tache
  ```

* **Génération de code :** Demande à Claude d'implémenter les routes, les modèles de données ou les composants d'interface.

* **Validation et Commit :**

  ```bash
  git add .
  git commit -m "feat(ai): intégration du parser Ollama pour extraire les flashcards"
  git push origin feature/nom-de-la-tache
  ```

## 3. Directives de Développement

* **Backend :** Structurer proprement le code (`app.py`, `models.py`, service Ollama). Gérer l'extraction de texte de manière robuste.
* **Frontend :** Assurer une interface fluide, responsive et agréable pour l'œil (utilisation de Tailwind CSS et transitions CSS fluides pour le retournement des cartes de flashcards).
* **Ollama :** Utiliser des prompts système stricts pour qu'Ollama retourne des flashcards structurées au format JSON (ex: `[{"question": "...", "answer": "..."}]`).

## 4. Prochaines étapes suggérées pour Claude

1. Initialiser l'arborescence des dossiers (`/static`, `/templates`, `app.py`, `database.py`).
2. Mettre en place le système d'upload et de stockage des cours dans SQLite.
3. Créer le service de communication avec l'API Ollama locale (`http://localhost:11434`) pour générer les flashcards à partir d'un texte de cours.
