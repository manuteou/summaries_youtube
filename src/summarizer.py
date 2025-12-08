from typing import List
import re
import time
from tqdm import tqdm

from utils import write_data

class Summarizer:
    def __init__(self, client, model: str, prompt_manager, summary_type: str = "short"):
        self.client = client
        self.model = model
        self.summary_type = summary_type
        self.prompt_manager = prompt_manager

    def _get_chunk_size(self) -> int:
        if self.summary_type == "long":
            return 10000
        elif self.summary_type == "medium":
            return 20000
        elif self.summary_type == "news":
            return 15000
        return 6000

    def generate_global_analysis(self, text: str) -> str:
        prompt = f"""
        Tu es un analyste expert. Voici un compte-rendu détaillé composé de plusieurs sections :
        {text}
        
        Ta tâche est de rédiger une SYNTHÈSE ANALYTIQUE GLOBALE qui servira d'introduction au document.
        
        Objectifs :
        1. Identifier les thèmes majeurs transversaux.
        2. Résumer les décisions clés et les actions à entreprendre.
        3. Offrir une vue d'hélicoptère du contenu.
        
        CONTRAINTES STRICTES :
        - Titre : "Synthèse Analytique Globale" (H1)
        - Pas d'hallucinations.
        - Ne pas utiliser "Compte-Rendu Exhaustif".
        """
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return self._reformat_to_paragraphs(response["message"]["content"])

    def summarize_chunk(self, text: str) -> str:
        prompt = self.prompt_manager.get_prompt(self.summary_type, "chunk", text)
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return self._reformat_to_paragraphs(response["message"]["content"])


    def summarize_text(self, text: str, author: str) -> str:
        prompt = self.prompt_manager.get_prompt(self.summary_type, "full_text", text)
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return self._reformat_to_paragraphs(response["message"]["content"])


    def summarize_multi_texts(self, search: str, text: str) -> str:
        prompt = self.prompt_manager.get_prompt(self.summary_type, "multi", {'search': search, 'content': text})
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return self._reformat_to_paragraphs(response["message"]["content"])


    def _reformat_to_paragraphs(self, text: str) -> str:
        """
        Uses the LLM to rewrite the text, specifically transforming bullet points into paragraphs.
        """
        prompt = f"""
        Tu es un éditeur expert. Ta mission est de reformuler le texte suivant pour améliorer sa fluidité.
        
        Texte à traiter :
        {text}
        
        CONSIGNES STRICTES :
        1. **TRANSFORME TOUTES LES LISTES À PUCES EN PARAGRAPHES**. C'est ta priorité absolue.
        2. Si une liste à puces est vide, supprime la.
        3. **CONSERVE IMPÉRATIVEMENT LA STRUCTURE MARKDOWN** : Ne touche PAS aux titres (H1, H2, H3) ni au gras (**texte**).
        4. Ne change PAS le sens du texte. Garde toutes les informations.
        5. Supprime les lignes vides inutiles.
        6. Ne fais AUCUN commentaire (pas de "Voici le texte", "J'ai reformulé...").
        7. Renvoie UNIQUEMENT le texte réécrit.
        """
        
        try:
            response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
            return response["message"]["content"].strip()
        except Exception as e:
            print(f"Error in LLM reformat: {e}")
            return text.strip()

    def enhance_markdown(self, text: str)-> str:
        prompt = f"""
            Tu es une MACHINE DE FORMATAGE MARKDOWN. Tu n'es PAS un humain. Tu n'es PAS un critique littéraire.
            Ta SEULE et UNIQUE fonction est de prendre le texte en entrée et de le reformater en Markdown propre.

            Texte à traiter :
            {text}

            CONSIGNES ABSOLUES :
            1.  **RECOPIE ET FORMATE** le texte complet. Ne change PAS le sens. Ne supprime PAS d'informations.
            2.  **STRUCTURE** : Utilise des titres H1, H2, H3 pour structurer le document.
            3.  **STYLE** : Rédige UNIQUEMENT des paragraphes complets. **INTERDICTION ABSOLUE DE LISTES À PUCES**.
            4.  **NETTOYAGE** : Supprime impitoyablement toute ligne vide inutile ou puce vide.
            5.  **INTERDICTION DE PARLER** : Tu ne dois JAMAIS dire "Voici le texte", "C'est parfait", "J'ai fini".
            6.  **SORTIE PURE** : Ton output doit commencer par le premier caractère du document Markdown et finir par le dernier. RIEN D'AUTRE.

            Si tu écris une phrase comme "Ce document est parfait", TU AS ÉCHOUÉ.
            Si tu écris une phrase comme "Voici la version formatée", TU AS ÉCHOUÉ.
            Si tu mets une liste à puces, TU AS ÉCHOUÉ.

            FORMATAGE UNIQUEMENT. COMMENCE MAINTENANT.
            """
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return self._reformat_to_paragraphs(response["message"]["content"])


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
        return text.strip()

    def refine_summary(self, current_summary: str, instructions: str) -> str:
        prompt = f"""
        Tu es un assistant de rédaction expert.
        
        Texte actuel :
        {current_summary}
        
        Consigne de réécriture / modification :
        {instructions}
        
        Ta tâche :
        Réécris ou modifie le texte actuel pour respecter la consigne donnée.
        
        OBJECTIFS :
        - Conserver le sens et les informations clés (sauf si la consigne demande de raccourcir drastiquement).
        - Appliquer scrupuleusement la demande de modification.
        - Garder un ton professionnel et une mise en page Markdown propre.
        
        CONTRAINTES STRICTES :
        - PAS de méta-commentaires ("Voici le texte modifié", "J'ai appliqué...").
        - SORTIE PURE : Uniquement le nouveau texte.
        """
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return self._reformat_to_paragraphs(response["message"]["content"])
