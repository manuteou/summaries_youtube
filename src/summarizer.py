def summarize_text(text: str, client, model, author: str) -> str:
    prompt = f"""
    Résume efficacement le texte de cet auteur {author} suivant (issu d'une transcription audio) :
    {text}

    🎯 Objectifs :
    - Produire une synthèse claire, concise et fidèle au contenu
    - Mettre en avant les idées principales et les points clés
    - Éliminer les détails superflus ou les répétitions

    📑 Contraintes de sortie :
    - Langue : français
    - Format : **Markdown** structuré et hiérarchisé
    - Organisation : titres, sous-titres et listes à puces
    - Style : ordonné, lisible et professionnel
    - Ton : neutre et informatif
    - tu nommeras l'auteur dans le titre

    ✅ Bonus :
    - Commence par un titre général du résumé
    - Ajoute une section "Points essentiels" en puces
    - Termine par une courte conclusion synthétique

    Il est interdit de donner autre chose que le resumer en sortie
    """
    response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]

def summarize_multi_texts(text: str, client, model) -> str:
    prompt = f"""
            Voici plusieurs transcriptions issues de différentes sources :
            {text}

🎯 Objectifs :
- Produire une synthèse qui couvre **toutes les sources**
- Mentionner les auteurs dans les sections correspondantes
- Mettre en évidence les points communs et les divergences
- Ne pas se limiter à la dernière source

📑 Contraintes de sortie :
- Langue : français
- Format : **Markdown** structuré et hiérarchisé
- Organisation : titres et sous-titres clairs
- Style : rédigé en **paragraphes continus**, comme un rapport ou une note de synthèse
- Ton : neutre, informatif et professionnel
- Tu nommeras l'auteur dans le titre de chaque section

✅ Bonus :
- Commence par un titre général du résumé
- Ajoute une section "Points essentiels" en **paragraphes courts** (pas de puces)
- Termine par une conclusion synthétique en un paragraphe

🚫 Interdiction :
- Ne pas utiliser de listes à puces
- Ne pas donner autre chose que le résumé en sortie
"""
    response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]