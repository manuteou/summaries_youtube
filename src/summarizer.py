from typing import List
import time
from tqdm import tqdm

from utils import write_data

class Summarizer:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    def summarize_chunk(self, text: str) -> str:
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
- Style : rédigé en paragraphes clairs et professionnels
- Ton : neutre et informatif
- Longueur : environ 200 mots
- Pas de conclusion
- La sortie doit être uniquement le résumé demandé
- Interdiction absolue d'afficher ton raisonnement, tes étapes ou une partie "think"
- Il est interdit de donner autre chose que le résumé en sortie
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document" dans les titres ou le texte
- Éviter les listes à puces, privilégier la rédaction
"""

        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]


    def summarize_text(self, text: str, author: str) -> str:
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
- Style : rédigé en paragraphes clairs et professionnels
- Ton : neutre et informatif
- Longueur : environ 200 mots
- Pas de conclusion
- La sortie doit être uniquement le résumé demandé
- Interdiction absolue d'afficher ton raisonnement, tes étapes ou une partie "think"
- Il est interdit de donner autre chose que le résumé en sortie
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
- Le résumé doit être structuré en deux sections : 
  1. Informations descendantes
  2. Actions attendues
- Éviter les listes à puces, privilégier la rédaction
"""
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]


    def summarize_multi_texts(self, search: str, text: str) -> str:
        prompt = f"""
Tu dois rédiger une synthèse complète sur le sujet suivant : {search}.
Utilise exclusivement les informations contenues dans les transcriptions ci-dessous (issues de différentes sources) :
{text}

    
    🎯 Objectifs :
    - Produire une synthèse intégrée qui couvre toutes les sources
    - Mettre en évidence les points communs et les divergences
    - Relier les idées dans un texte continu, comme une dissertation
    - Ne pas se limiter à la dernière source
    
    
    📑 Contraintes de sortie :
    - Langue : français
    - Organisation : introduction, développement, conclusion
    - Style : rédigé en paragraphes étoffés, argumentés et liés
    - Ton : neutre, informatif et professionnel
    - Mentionner les auteurs uniquement dans le flux du texte (pas en titres séparés)
    - Utiliser toutes les sources pour enrichir le contenu
    
    ✅ Bonus :
    - Commencer par une introduction générale qui présente le thème
    - Développer les arguments en regroupant les sources par thématique dans des paragraphes détaillés
    - Terminer par une conclusion synthétique en un paragraphe
    
    🚫 Interdiction :
    - Ne pas utiliser de listes à puces
    - Ne pas donner autre chose que le résumé en sortie
    - Ne pas structurer par sections ou titres individuels
    """
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]


    def enhance_markdown(self, text: str)-> str:
        prompt = f"""
            Tu es un expert en édition et mise en page de documents.
            Ta mission est de transformer le texte brut suivant en un document Markdown **visuellement impeccable et très lisible**.

            Objectifs de mise en forme :
            - Utilise une hiérarchie de titres claire (H1, H2, H3).
            - Privilégie les **paragraphes** pour le texte.
            - Mets en **gras** les concepts clés et les termes importants.
            - Utilise des > citations pour les passages marquants.
            - Aère le texte avec des sauts de ligne appropriés.
            
            Contraintes :
            - Le contenu informatif doit rester le même (pas de suppression d'information).
            - Tu peux reformuler légèrement les phrases pour améliorer la fluidité et le style professionnel.
            - Le résultat doit être prêt à être publié.

            Texte à sublimer :
            {text}
            """
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]


    def check_synthese(self, text: str, subject: str):
        prompt = f"""
            Tu es un validateur automatique.
            Ton rôle est de vérifier si le texte fourni traite principalement du sujet demandé.

            Sujet attendu : {subject}
            Texte à analyser : {text}

            Consigne stricte :
            - Si le texte parle bien de ce sujet, réponds uniquement : True
            - Sinon, réponds uniquement : False
            - Ne donne aucune explication, aucun autre mot.
            """
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]


    def chunk_text(self, text: str, max_chars: int = 6000) -> List[str]:
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

    def sumarize_part_chunk(self, text):
        chunks = self.chunk_text(text)
        partial_summaries = []
        for chunk in tqdm(chunks, desc="Analyse des chunks", unit="chunk"):
            summary = self.summarize_chunk(chunk)
            partial_summaries.append(summary)
        return partial_summaries


    def summarize_long_text(self, text: str, author: str) -> str:
        text_parts = self.sumarize_part_chunk(text)
        text = "\n\n".join(text_parts)
        current_time = time.localtime()
        formatted_time = time.strftime("%H-%M-%S", current_time)
        write_data(
            output_dir='chunk_data', 
            data=text, 
            seg=f"{author}_{formatted_time}"
            )
        return text
