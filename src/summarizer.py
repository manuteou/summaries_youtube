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