from typing import List
import time
from tqdm import tqdm

from utils import write_data

class Summarizer:
    def __init__(self, client, model: str, summary_type: str = "short"):
        self.client = client
        self.model = model
        self.summary_type = summary_type

    def _get_chunk_size(self) -> int:
        if self.summary_type == "long":
            return 20000
        elif self.summary_type == "medium":
            return 10000
        return 6000

    def _get_prompts(self, text: str, context: str = "chunk") -> str:
        # --- SHORT MODE (Original) ---
        if self.summary_type == "short":
            if context == "chunk":
                return f"""
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
            elif context == "full_text":
                return f"""
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
            elif context == "multi":
                return f"""
Tu dois rédiger une synthèse complète sur le sujet suivant : {text['search']}.
Utilise exclusivement les informations contenues dans les transcriptions ci-dessous (issues de différentes sources) :
{text['content']}

    
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

        # --- MEDIUM MODE (Balanced) ---
        elif self.summary_type == "medium":
            if context == "chunk":
                return f"""
Tu es un assistant expert en synthèse de documents.

Texte à résumer :
{text}

🎯 Objectifs :
- Produire un résumé équilibré : ni trop concis, ni trop verbeux.
- Capturer l'essentiel tout en conservant les nuances importantes.
- Développer les points clés avec des explications claires.
- Développer les points clés avec des explications claires.
- Structurer le contenu avec des titres thématiques pertinents.

📑 Contraintes :
- Langue : français
- Longueur : environ 500 mots (ou plus si nécessaire pour la clarté)
- Style : professionnel, fluide et agréable à lire.
- Pas de méta-commentaires (ex: "Voici le résumé").
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
"""
            elif context == "full_text":
                return f"""
Tu es un assistant expert en synthèse.

Texte à résumer :
{text}

🎯 Objectifs :
- Fournir une vue d'ensemble complète et structurée.
- Détailler les informations descendantes et les actions attendues.
- Conserver le contexte et les nuances des propos tenus.
- Hiérarchiser l'information par importance.

📑 Contraintes :
- Langue : français
- Longueur : environ 500-800 mots.
- Structure : Introduction -> Développement par thèmes -> Actions/Directives.
- Style : Rédaction soignée, paragraphes bien construits.
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
"""
            elif context == "multi":
                return f"""
Rédige une synthèse thématique sur : {text['search']}.

Sources :
{text['content']}

🎯 Objectifs :
- Croiser les informations des différentes sources.
- Identifier les tendances et les consensus.
- Noter les points de désaccord ou les perspectives uniques.
- Produire un texte cohérent et fluide.

📑 Contraintes :
- Langue : français
- Longueur : Suffisante pour couvrir le sujet en profondeur (environ 1000 mots).
- Structure : Introduction -> Analyse thématique -> Conclusion.
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
"""

        # --- LONG MODE (Exhaustive) ---
        elif self.summary_type == "long":
            if context == "chunk":
                return f"""
Tu es un archiviste expert chargé de créer un compte-rendu exhaustif.

Texte à traiter :
{text}

🎯 Objectifs :
- NE RIEN OMETTRE : capture tous les détails, chiffres, noms, et nuances.
- Produire un compte-rendu extrêmement détaillé, proche du verbatim mais restructuré.
- Développer chaque idée au maximum de son potentiel informatif.
- Utiliser des titres très descriptifs pour chaque section.

📑 Contraintes :
- Langue : français
- Longueur : ILLIMITÉE (aussi long que nécessaire pour être exhaustif).
- Style : Formel, précis, dense en informations.
- Pas de résumé sommaire, on veut du détail.
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
"""
            elif context == "full_text":
                return f"""
Tu es un expert en documentation technique et administrative.

Texte à traiter :
{text}

🎯 Objectifs :
- Produire un document de référence complet.
- Détailler minutieusement toutes les décisions, annonces, et débats.
- Lister toutes les actions avec leur contexte complet.
- Restituer la chronologie ou la logique des arguments si pertinent.

📑 Contraintes :
- Langue : français
- Longueur : ILLIMITÉE.
- Structure : Très structurée (H1, H2, H3), utilisation de gras pour les points cruciaux.
- Le but est de remplacer la lecture du transcript original par ce document.
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
"""
            elif context == "multi":
                return f"""
Réalise une thèse ou un dossier complet sur le sujet : {text['search']}.

Sources :
{text['content']}

🎯 Objectifs :
- Analyser en profondeur chaque aspect du sujet à travers les sources.
- Confronter les points de vue avec précision.
- Fournir une analyse critique et détaillée.
- Intégrer un maximum de citations ou de références précises au contenu.

📑 Contraintes :
- Langue : français
- Longueur : ILLIMITÉE (viser l'exhaustivité totale).
- Format : Dossier complet avec sommaire implicite (Introduction, Contexte, Analyse détaillée par axe, Synthèse, Conclusion).
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
"""
        return ""

    def summarize_chunk(self, text: str) -> str:
        prompt = self._get_prompts(text, context="chunk")
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return response["message"]["content"]


    def summarize_text(self, text: str, author: str) -> str:
        prompt = self._get_prompts(text, context="full_text")
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return response["message"]["content"]


    def summarize_multi_texts(self, search: str, text: str) -> str:
        prompt = self._get_prompts({'search': search, 'content': text}, context="multi")
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
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
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return response["message"]["content"]


    def check_synthese(self, text: str, subject: str):
        prompt = f"""
            Tu es un validateur automatique.
            Ton rôle est de vérifier si le texte fourni traite principalement du sujet demandé.

            Sujet attendu : {subject}
            Texte à analyser : {text}

            Consigne stricte :
            - Ignore les formules de politesse ou d'introduction du texte à analyser.
            - Concentre-toi sur le FOND : est-ce que ça parle du sujet ?
            - Si le texte traite du sujet demandé (même partiellement), réponds : True
            - Si le texte est HORS SUJET ou parle de tout autre chose, réponds : False
            - Réponds UNIQUEMENT par True ou False.
            """
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return response["message"]["content"]


    def chunk_text(self, text: str) -> List[str]:
        max_chars = self._get_chunk_size()
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
