from pytubefix import YouTube
import re

yt = YouTube('https://www.youtube.com/watch?v=9jX2ZT0-iiA')
caption = yt.captions['a.fr']
r = caption.generate_srt_captions()


def extraire_dialogues(fichier_srt, bloc=3):
    lignes = r.splitlines()
    lignes = [ligne.strip() for ligne in lignes if ligne.strip()]
    i = 0
    text_ligne = []
    for ligne in lignes:
        i+=1
        if i%3==0:
           text_ligne.append(ligne)
    texte = " ".join(text_ligne)
    return texte

# Exemple d'utilisation
result = extraire_dialogues(r, bloc=3)
print(result)
