from pytubefix import YouTube


yt = YouTube('https://www.youtube.com/watch?v=GQ-qucP4g_s')
caption = yt.captions['a.fr']
r = caption.generate_srt_captions()


def extraire_dialogues(fichier_srt):
    lignes = fichier_srt.splitlines()
    lignes = [ligne.strip() for ligne in lignes if ligne.strip()]
    i = 0
    text_ligne = []
    for ligne in lignes:
        i+=1
        if i%3==0:
           text_ligne.append(ligne)
    texte = " ".join(text_ligne)
    return texte


result = extraire_dialogues(r)
print(result)
