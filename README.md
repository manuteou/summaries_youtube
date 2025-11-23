Scrpit qui resume une video youtube


Summaries --|
            | --src
            | --ffmpeg

DIR ffmpeg mettre le bin de ffmpeg pour le systeme
utlisation de ollama pour les modeles en local

fichier env:
OUTPUT_DIR= repertoire de sortie du resumé par default (src/summaries)
MODEL= modele utilisé par whiper par (defaut tiny)
DEVICE= traitement du décodage (par defaut cpu)
FORMAT= format de sortie du texte (dafaut markdown)
OLLAMA_MODEL= modele utilisée par ollama pour résumer
OLLAMA_HOST= ip serveur ollama
FFMPEG= chemin de FFMPEG

lancement du script :

python cly.py --url 'url_de_la_video'
uv run cly.py --url 'url_de_la_video'
            