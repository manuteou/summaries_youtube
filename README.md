🎬 YouTube Video Summarizer & Synthesizer
Un script CLI qui permet :
- soit de résumer une vidéo YouTube à partir de son URL,
- soit de faire une synthèse multi‑sources en lançant une recherche YouTube.
Dans les deux cas, l’audio est téléchargé, transcrit avec Whisper, puis résumé grâce à Ollama.
Le tout est exporté en Markdown ou txt pour une utilisation simple.

🚀 Fonctionnalités
- 📥 Téléchargement de l’audio via FFmpeg
- 📝 Transcription locale avec Whisper
- 🤖 Résumé ou synthèse généré(e) par un modèle Ollama
- 📂 Export automatique dans le répertoire de sortie
- 🔀 Deux modes disponibles :
- --url → résumé d’une seule vidéo
- --search → synthèse multi‑vidéos à partir d’un sujet
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
python cli.py --url "https://youtube.com/watch?v=xxxx"

# Avec uv
uv run cli.py --url "https://youtube.com/watch?v=xxxx"


2. Synthèse multi‑vidéos via recherche
# Méthode classique
python cli.py --search "impact de l'IA sur l'informatique"

# Avec uv
uv run cli.py --search "impact de l'IA sur l'informatique"


