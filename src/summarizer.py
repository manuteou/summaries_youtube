from typing import List
import time
from tqdm import tqdm

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
- Donner un titre thématique et descriptif (jamais générique) à toutes les parties
- Mettre en avant les actions attendues par les participants et les campus
- Les informations descendantes doivent être mises en avant dans le texte

📑 Contraintes de sortie :
- Langue : français
- Style : ordonné, lisible et professionnel
- Ton : neutre et informatif
- Longueur : exactement 200 mots (ni plus, ni moins)
- Pas de conclusion
- La sortie doit être uniquement le résumé demandé
- Interdiction absolue d'afficher ton raisonnement, tes étapes ou une partie "think"
- Il est interdit de donner autre chose que le résumé en sortie
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document" dans les titres ou le texte
"""

    response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]


def summarize_text(text: str, client, model, author: str) -> str:
    prompt = f"""
Tu es un assistant qui doit produire uniquement un résumé.

Texte à résumer (issu d'une transcription audio) :
{text}

🎯 Objectifs :
- Synthèse claire, concise et fidèle au contenu
- Mettre en avant les idées principales et les points clés
- Éliminer les détails superflus ou les répétitions
- Donner un titre thématique et descriptif (jamais générique) à toutes les parties
- Mettre en avant les actions attendues par les participants et les campus
- Identifier et hiérarchiser toutes les informations descendantes (directives, décisions, annonces)
- Distinguer clairement les informations descendantes des actions attendues
- Mentionner les responsables ou destinataires si précisés

📑 Contraintes de sortie :
- Langue : français
- Style : ordonné, lisible et professionnel
- Ton : neutre et informatif
- Longueur : exactement 200 mots (ni plus, ni moins)
- Pas de conclusion
- La sortie doit être uniquement le résumé demandé
- Interdiction absolue d'afficher ton raisonnement, tes étapes ou une partie "think"
- Il est interdit de donner autre chose que le résumé en sortie
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
- Le résumé doit être structuré en deux sections : 
  1. Informations descendantes
  2. Actions attendues
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
                - Conserver **tous les mots du texte original sans les modifier, supprimer ou reformuler**
                - Ne pas résumer, ne pas paraphraser, ne pas ajouter de contenu

                Texte à mettre en forme :
                {text}

            """
    response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]


def sumarize_part_chunk(text, client, model):
    chunks = chunk_text(text)
    partial_summaries = []
    for chunk in tqdm(chunks, desc="Analyse des chunks", unit="chunk"):
        summary = summarize_chunk(chunk, client, model=model)
        partial_summaries.append(summary)
    return partial_summaries


def summarize_long_text(text: str, client, model, author: str) -> str:
    text = sumarize_part_chunk(text,client, model)
    text = "\n\n".join(text)
    #final_summary = summarize_text(text, client, model, author)
    return text
