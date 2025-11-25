from typing import List
import time
from rich.console import Console
console = Console()

def chunk_text(text: str, max_chars: int = 6000) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            end = text.rfind(" ", start, end)
            if end == -1:
                end = start + max_chars
        chunks.append(text[start:end].strip())
        start = end
    console.print(f"[green]nombre de partie à analyser {len(chunks)}[/green]")
    return chunks


def summarize_chunk(text: str, client, model) -> str:
    prompt = f"""
    Résume efficacement le texte suivant (issu d'une transcription audio) :
    {text}

    🎯 Objectifs :
    - Produire une synthèse claire, concise et fidèle au contenu
    - Mettre en avant les idées principales et les points clés
    - Éliminer les détails superflus ou les répétitions

    📑 Contraintes de sortie :
    - Langue : français
    - Style : ordonné, lisible et professionnel
    - Ton : neutre et informatif
    - 200 mots au total
    - pas de conclusion
    - Il est interdit de donner autre chose que le resumer en sortie
    """
    response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]


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


def enhance_markdown(text: str, client, model)-> str:
    prompt = f"""Transforme le texte suivant en **Markdown** structuré et hiérarchisé,
                en respectant strictement ces contraintes :

                - Langue : français
                - Format : Markdown avec titres, sous-titres clairs et paragraphes
                - Organisation : titres, sous-titres clairs et paragraphes
                - Conserver **tous les mots du texte original sans les modifier, supprimer ou reformuler**
                - Ne pas résumer, ne pas paraphraser, ne pas ajouter de contenu

                Texte à mettre en forme :
                {text}

            """
    response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]


def summarize_long_text(text: str, client, model, author: str) -> str:
    chunks = chunk_text(text)
    partial_summaries = []

    total_start = time.time()

    for  i,chunk in enumerate(chunks):
        start = time.time()
        summary = summarize_chunk(chunk, client, model='qwen3:4b')
        end = time.time()
        duration = end - start
        partial_summaries.append(summary)
        console.print(f"[green]analyse {i+1} effectuée en {duration:.2f} secondes[/green]")


    combined_text = "\n\n".join(partial_summaries)
    start_final = time.time()
    final_summary = summarize_text(combined_text, client, model, author)
    end_final = time.time()
    console.print(f"[green]résumé final généré en {end_final - start_final:.2f} secondes[/green]")
    console.print(f"[green]mise en forme effectuée en {end_final - start_final:.2f} secondes[/green]")
    total_end = time.time()
    console.print(f"[bold green]Travail total effectué en {total_end - total_start:.2f} secondes[/bold green]")

    return final_summary
