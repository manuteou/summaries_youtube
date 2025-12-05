# 🎬 YouTube Summarizer & Synthesizer

Une application puissante alimentée par l'IA pour **résumer**, **synthétiser** et **analyser** des vidéos YouTube ou des fichiers locaux. 
Utilise **Ollama** (LLM local) et **Whisper** (Transcription) pour garantir confidentialité et performance sans frais d'API.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-App-red) ![Ollama](https://img.shields.io/badge/AI-Ollama-orange)

---

## 🚀 Pourquoi cet outil ?

Ne perdez plus de temps à regarder des heures de vidéo pour trouver une information.
*   **Veille Technologique** : Scannez 10 vidéos sur un sujet en 2 minutes.
*   **Études & Recherche** : Synthétisez des conférences ou des cours complexes.
*   **Création de Contenu** : Transformez des vidéos en articles de blog ou posts LinkedIn en un clic.

---

## ✨ Fonctionnalités Clés

### 🔍 1. Recherche & Veille (Moteur Dynamique)
*   **Recherche YouTube intégrée** : Plus besoin de copier-coller des liens.
*   **Filtres Avancés** : Triez par *Date*, *Pertinence*, *Vues* ou filtrez par *Durée* (Court, Moyen, Long).
*   **Affichage Dynamique** : Grille infinie de résultats. Chargez autant de vidéos que nécessaire.
*   **Vignettes Intelligentes** : Aperçu de la durée, date de mise en ligne relative (ex: "il y a 2 jours") et description scrollable.

### 📝 2. Synthèse Multi-Sources
Sélectionnez plusieurs vidéos (ex: 5 topos sur "L'IA en 2025") et générez une **synthèse unique** qui compile et structure les informations de toutes les sources.

### 🧠 3. Intelligence Artificielle (Local & Privé)
*   **Transcription** : Utilise **Whisper** (modèle configurable : `base`, `small`, `medium`...) pour convertir l'audio en texte.
*   **Analyse** : Utilise **Ollama** (ex: `mistral`, `llama3`) pour comprendre et résumer le contenu.
*   **3 Modes de Résumés** :
    *   `Short` : L'essentiel en quelques points.
    *   `Medium` : Un résumé équilibré et structuré.
    *   `Long` : Analyse approfondie type "compte-rendu" avec détails.

### 🎨 4. Édition & Raffinement (Onglet Result)
Une fois le résumé généré, vous avez le contrôle total :
*   **Éditeur Riche** : Modifiez le texte, ajoutez des titres, du gras, des listes...
*   **✨ Refine / Regenerate** : Demandez à l'IA de réécrire le texte selon vos critères via des menus simples :
    *   **Taille** : Plus court / Plus long
    *   **Ton** : Professionnel, Formel, Familier
    *   **Format** : Rapport Structuré, Dissertation, Article de Blog, Liste à puces...
    *   **Langue** : Traduction instantanée (Anglais, Espagnol, Allemand...)
    *   *Ou vos propres instructions manuelles !*
*   **Export Multiformat** : Sauvegardez en **PDF**, **HTML**, **Markdown** ou **Texte**.

### 🛠️ 5. Autres Modes
*   **Mode Manuel** : Collez une liste d'URLs spécifiques.
*   **Fichier Local** : Traitez vos propres fichiers `.mp4` (réunions, enregistrements...).

---

## ⚙️ Installation & Configuration

### Pré-requis
*   Python 3.10+
*   [FFmpeg](https://ffmpeg.org/download.html) installé et accessible dans le PATH.
*   [Ollama](https://ollama.com/) installé et un modèle téléchargé (ex: `ollama pull mistral`).

### 1. Cloner et Installer
```bash
git clone https://github.com/votre-user/summaries_youtube.git
cd summaries_youtube

# Avec uv (recommandé)
uv sync

# Ou avec pip classique
pip install -r requirements.txt
```

### 2. Configuration (.env)
Créez un fichier `.env` à la racine :

```env
# Répertoires
OUTPUT_DIR=src/summaries

# Modèles IA
MODEL=medium          # Modèle Whisper (tiny, base, small, medium, large)
DEVICE=cpu            # cpu ou cuda (si GPU NVIDIA disponible)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral  # Le modèle Ollama à utiliser

# Export défaut
FORMAT=md             # md, txt, html, pdf
```

---

## ▶️ Utilisation

Lancer l'interface graphique (recommandé) :

```bash
# Avec uv
uv run streamlit run src/app.py

# Standard
streamlit run src/app.py
```

L'application s'ouvre dans votre navigateur (généralement `http://localhost:8501`).

---

## 📂 Structure du Projet

```
.
├── src/
│   ├── app.py           # Point d'entrée Streamlit (Interface)
│   ├── workflow.py      # Orchestrateur (Lien entre UI et Backend)
│   ├── summarizer.py    # Logique IA (Prompts & Ollama)
│   ├── transcriber.py   # Logique Whisper
│   ├── downloader.py    # Gestion YouTube & Audio
│   ├── exporter.py      # Génération PDF/HTML/MD
│   └── utils.py         # Utilitaires
├── summaries/           # Dossier de sortie des rapports
└── README.md
```

## ⚠️ Notes
*   **Performance** : La transcription (Whisper) et le résumé (Ollama) sont des tâches lourdes. Un GPU (CUDA) est fortement recommandé pour le modèle `medium` ou `large`.
*   **Contexte** : Attention à ne pas sélectionner trop de vidéos "Longues" pour une synthèse unique, cela pourrait dépasser la fenêtre de contexte du modèle LLM.

---
*Fait avec ❤️ et beaucoup de café.*
