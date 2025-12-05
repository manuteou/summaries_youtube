🎬 YouTube Video Summarizer & Synthesizer
Un script CLI qui permet :
- soit de résumer une vidéo YouTube à partir de son URL,
- soit de faire une synthèse multi‑sources en lançant une recherche YouTube.
- soit de faire une synthèse à partir d'une video mp4.
Dans tout les cas, l’audio ou les sous titre sont téléchargés, transcrit avec Whisper si nécessaire, puis résumé grâce à Ollama.
Le tout est exporté en Markdown ou txt pour une utilisation simple.

🚀 Fonctionnalités
- 📥 Téléchargement de l’audio via FFmpeg
- 📝 Transcription locale avec Whisper
- 🤖 Résumé ou synthèse généré(e) par un modèle Ollama
- 📂 Export automatique dans le répertoire de sortie
- 🖥️ Interface graphique (Streamlit) pour une expérience visuelle
- 🔀 Trois modes disponibles :
- --url → résumé d’une seule vidéo
- --search → synthèse multi‑vidéos à partir d’un sujet
- --video-path → synthèse à partir d'une video mp4
- ⚙️ Configuration flexible via fichier .env

📂 Structure
Summaries
 ├── src
 └── ffmpeg   # mettre le binaire ffmpeg pour le système



⚙️ Configuration .env
Avant de lancer le script, configurez les variables d’environnement :
|  |  |  | 
| OUTPUT_DIR |  | src/summaries | 
| MODEL |  | tiny | 
| DEVICE |  | cpu | 
| FORMAT |  | markdown | 
| OLLAMA_MODEL |  |  | 
| OLLAMA_HOST |  |  | 
| FFMPEG |  |  | 




▶️ Lancement du script
Deux modes sont disponibles :
1. Résumer une seule vidéo
# Méthode classique
python cli.py --url "https://youtube.com/watch?v=xxxx" --type medium

# Avec uv
uv run cli.py --url "https://youtube.com/watch?v=xxxx" --type long


2. Synthèse multi‑vidéos via recherche
# Méthode classique
python cli.py --search "impact de l'IA sur l'informatique" --limit 5 --type medium

# Avec uv
uv run cli.py --search "impact de l'IA sur l'informatique" --limit 3 --type long

3. Synthèse vidéos mp4
# Méthode classique
python cli.py --video-path "le path du fichier.mp4" --type short

# Avec uv
uv run cli.py --video-path "le path du fichier.mp4"

4. Mode Manuel (CLI)
Permet de construire manuellement une liste de vidéos à traiter.

# Méthode classique
python cli.py --manual

# Avec uv
uv run cli.py --manual


5. Interface Graphique (Streamlit)
Profitez d'une interface visuelle pour rechercher, sélectionner et éditer vos résumés.

Fonctionnalités de l'app :
- 🔍 **Recherche Visuelle** : Aperçu des miniatures et détails des vidéos
- ✍️ **Mode Manuel** : Ajout simple d'URLs
- 📁 **Fichier Local** : Traitement de vidéos MP4
- 📝 **Édition** : Modifiez le résumé final avant de l'exporter

# Lancement
uv run streamlit run src/app.py
# ou
streamlit run src/app.py

 ✨ Nouveautés de l'Interface (v2.0) :
- **🔍 Recherche Dynamique** : Chargement infini, vignettes uniformisées avec durée et date relative.
- **✨ Refine / Regenerate** : Modifiez le résumé généré avec l'IA directement depuis l'app :
    - **Taille** : Plus court / Plus long
    - **Ton** : Professionnel, Formel, Familier
    - **Format** : Rapport, Dissertation, Article de Blog...
    - **Langue** : Traduction instantanée
- **📝 Onglet Result** : 
    - Éditeur de texte riche
    - Copie rapide du Markdown
    - Export multiformat (.pdf, .html, .md, .txt) contextuel


🎯 Options de Résumé (`--type`)
Le script propose 3 niveaux de détail :
- `short` (défaut) : Concis (~200 mots). Idéal pour un aperçu rapide.
- `medium` : Équilibré (~500-800 mots). Le meilleur compromis pour comprendre les nuances.
- `long` : Exhaustif (illimité). Pour une analyse en profondeur type "compte-rendu".

💡 Conseils pour la Synthèse Multi-Vidéos
Pour obtenir la meilleure qualité possible sans dépasser la fenêtre de contexte du modèle (8k tokens), voici les ratios recommandés :

| Objectif | Type | Limit recommandée |
| :--- | :--- | :--- |
| **Analyse approfondie** (Thèse) | `long` | **2 à 3** vidéos max |
| **Compromis idéal** (Qualité/Quantité) | `medium` | **4 à 5** vidéos |
| **Veille / Scanning** (Tendances) | `short` | **5 à 10** vidéos |

> **Note** : Si vous demandez trop de vidéos en mode `long`, le modèle risque d'oublier le début des informations lors de la synthèse finale.



