# 🎬 YouTube Video Summarizer

Un script CLI qui télécharge l’audio d’une vidéo YouTube, le transcrit avec **Whisper**, puis génère un résumé grâce à **Ollama**.  
Le tout est exporté  en Markdown ou txt pour une utilisation simple.

---

## 🚀 Fonctionnalités
- 📥 Téléchargement de l’audio via **FFmpeg**
- 📝 Transcription locale avec **Whisper**
- 🤖 Résumé généré par un modèle **Ollama**
- 📂 Export automatique dans le répertoire de sortie
- ⚙️ Configuration flexible via fichier `.env`

---

## 📂 Structure

Summaries   ├── src 
            └── ffmpeg   # mettre le binaire ffmpeg pour le système


---

## ⚙️ Configuration `.env`
Avant de lancer le script, configurez les variables d’environnement :

| Variable       | Description                                      | Valeur par défaut         |
|----------------|--------------------------------------------------|---------------------------|
| `OUTPUT_DIR`   | Répertoire de sortie des résumés                 | `src/summaries`           |
| `MODEL`        | Modèle Whisper utilisé pour la transcription     | `tiny`                    |
| `DEVICE`       | Périphérique de décodage                         | `cpu`                     |
| `FORMAT`       | Format de sortie du résumé                       | `markdown`                |
| `OLLAMA_MODEL` | Modèle Ollama utilisé pour le résumé             | *(à définir)*             |
| `OLLAMA_HOST`  | Adresse IP du serveur Ollama                     | *(à définir)*             |
| `FFMPEG`       | Chemin vers le binaire FFmpeg                    | *(à définir)*             |

---

## ▶️ Lancement du script

Deux façons de lancer le script :

```bash
# Méthode classique
python cly.py --url "url_de_la_video"

# Avec uv
uv run cly.py --url "url_de_la_video"
