from typing import List
import time
from rich.console import Console
console = Console()
from utils import write_data

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
    console.print(f"[blue]nombre de partie à analyser[/blue] [yellow4]{len(chunks)}[/yellow4]")
    return chunks


def summarize_chunk(text: str, client, model) -> str:
    prompt = f"""
    Tu es un assistant qui doit produire uniquement un résumé.

    Texte à résumer (issu d'une transcription audio) :
    {text}

    🎯 Objectifs :
    - Synthèse claire, concise et fidèle au contenu
    - Mettre en avant les idées principales et les points clés
    - Éliminer les détails superflus ou les répétitions
    - met un titre qui resume les points important du text

    📑 Contraintes de sortie :
    - Langue : français
    - Style : ordonné, lisible et professionnel
    - Ton : neutre et informatif
    - Longueur : exactement 200 mots (ni plus, ni moins)
    - Pas de conclusion
    - La sortie doit être uniquement le résumé demandé
    - Interdiction absolue d'afficher ton raisonnement, tes étapes ou une partie "think"
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
    - Ne pas se limiter à la dernière source
   

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
    prompt = prompt = f"""
    Voici plusieurs transcriptions issues de différentes sources :
    {text}
    
    🎯 Objectifs :
    - Produire une synthèse intégrée qui couvre toutes les sources
    - Mettre en évidence les points communs et les divergences
    - Relier les idées dans un texte continu, comme une dissertation
    - Ne pas se limiter à la dernière source
    
    📑 Contraintes de sortie :
    - Langue : français
    - Organisation : introduction, développement, conclusion
    - Style : rédigé en paragraphes continus, argumentés et liés
    - Ton : neutre, informatif et professionnel
    - Mentionner les auteurs uniquement dans le flux du texte (pas en titres séparés)
    
    ✅ Bonus :
    - Commencer par une introduction générale qui présente le thème
    - Développer les arguments en regroupant les sources par thématique
    - Terminer par une conclusion synthétique en un paragraphe
    
    🚫 Interdiction :
    - Ne pas utiliser de listes à puces
    - Ne pas donner autre chose que le résumé en sortie
    - Ne pas structurer par sections ou titres individuels
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

def sumarize_part_chunk(text, client):
    chunks = chunk_text(text)
    partial_summaries = []
    for  i,chunk in enumerate(chunks):
        start = time.time()
        summary = summarize_chunk(chunk, client, model='gemma3:4b')
        write_data("./chunk_data", summary, i)
        end = time.time()
        duration = end - start
        partial_summaries.append(summary)
        console.print(f"[blue]analyse[/blue] [yellow4]{i+1}[/yellow4] [blue]effectuée en[/blue] [yellow4]{duration:.2f}[/yellow4] [blue]secondes[/blue]")
    return partial_summaries

def summarize_long_text(text: str, client, model, author: str, nbr: int =2) -> str:
    for i in range(nbr):
        text = sumarize_part_chunk(text,client)
        text = "\n\n".join(text)
        write_data("./chunk_data_all", text, i)
    start_final = time.time()
    final_summary = summarize_text(text, client, model, author)
    end_final = time.time()
    console.print(f"[blue]résumé final généré en[/blue] [yellow4]{end_final - start_final:.2f}[/yellow4] [blue]secondes[/[blue]]")
    console.print(f"[blue]mise en forme effectuée en[/blue] [yellow4]{end_final - start_final:.2f}[/yellow4] [blue]secondes[/[blue]]")
    total_end = time.time()
    console.print(f"[bold green]Travail total effectué en[/bold green] [yellow4]{total_end - total_start:.2f}[/yellow4] [bold green]secondes[/bold green]")

    return final_summary
