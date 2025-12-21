"""
summarizer.py - Refactored text summarization service

Ce module gère la génération de résumés via LLM.
Utilise les constantes centralisées et améliore le typage.
"""

from typing import List, Optional, Dict, Any
import re
import time
import os
from datetime import datetime
from tqdm import tqdm

from utils import write_data, slugify
from constants import CHUNK_SIZES, DEFAULT_CONTEXT_SIZE, DEFAULT_NUM_PREDICT


class Summarizer:
    """
    Service de résumé de texte via LLM.
    
    Attributes:
        client: Client Ollama pour les appels LLM
        model: Nom du modèle LLM
        summary_type: Type de résumé (short, medium, long, news, meeting)
        prompt_manager: Gestionnaire de prompts
    """
    
    def __init__(
        self, 
        client: Any, 
        model: str, 
        prompt_manager: Any, 
        summary_type: str = "short"
    ):
        """Initialise le service de résumé."""
        self.client = client
        self.model = model
        self.summary_type = summary_type
        self.prompt_manager = prompt_manager

    def _get_chunk_size(self) -> int:
        """Retourne la taille de chunk appropriée selon le type de résumé."""
        return CHUNK_SIZES.get(self.summary_type, CHUNK_SIZES["short"])

    def _get_llm_options(self) -> Dict[str, Any]:
        """Retourne les options par défaut pour les appels LLM."""
        return {
            "num_ctx": DEFAULT_CONTEXT_SIZE,
            "num_predict": DEFAULT_NUM_PREDICT
        }

    def _chat_and_log(
        self, 
        prompt: str, 
        context_name: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Exécute un appel LLM et log l'interaction pour debug.
        
        Args:
            prompt: Le prompt à envoyer
            context_name: Nom du contexte pour le logging
            options: Options LLM optionnelles
            
        Returns:
            Réponse du modèle
        """
        if options is None:
            options = self._get_llm_options()
            
        response = self.client.chat(
            model=self.model, 
            messages=[{"role": "user", "content": prompt}], 
            options=options
        )
        
        # Debug logging
        self._log_debug(prompt, response, context_name)
        
        return response
    
    def _log_debug(
        self, 
        prompt: str, 
        response: Dict[str, Any], 
        context_name: str
    ) -> None:
        """Log l'interaction LLM pour debug."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_context = slugify(context_name)
            debug_dir = os.path.join("debug", "debug_prompts", safe_context)
            os.makedirs(debug_dir, exist_ok=True)
            
            filename = f"{timestamp}.txt"
            file_path = os.path.join(debug_dir, filename)
            
            content = f"""
--- PROMPT ({context_name}) ---
{prompt}

--- RESPONSE ({context_name}) ---
{response.get('message', {}).get('content', '')}
"""
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content.strip())
                
        except Exception as e:
            print(f"Error logging debug info: {e}")

    # =========================================================================
    # ANALYSIS METHODS
    # =========================================================================

    def generate_global_analysis(self, text: str) -> str:
        """Génère une analyse globale introductive du contenu."""
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
        response = self._chat_and_log(prompt, "generate_global_analysis")
        return self._reformat_to_paragraphs(response["message"]["content"])

    def summarize_chunk(self, text: str) -> str:
        """Résume un chunk de texte."""
        prompt = self.prompt_manager.get_prompt(self.summary_type, "chunk", text)
        response = self._chat_and_log(prompt, "summarize_chunk")
        return self._reformat_to_paragraphs(response["message"]["content"])

    def summarize_text(self, text: str, author: str) -> str:
        """Résume un texte complet."""
        prompt = self.prompt_manager.get_prompt(self.summary_type, "full_text", text)
        response = self._chat_and_log(prompt, "summarize_text")
        return self._reformat_to_paragraphs(response["message"]["content"])

    def summarize_multi_texts(self, search: str, text: str) -> str:
        """Synthétise plusieurs textes en un seul résumé."""
        prompt = self.prompt_manager.get_prompt(
            self.summary_type, 
            "multi", 
            {'search': search, 'content': text}
        )
        response = self._chat_and_log(prompt, "summarize_multi_texts")
        return self._reformat_to_paragraphs(response["message"]["content"])

    # =========================================================================
    # TEXT PROCESSING
    # =========================================================================

    def _reformat_to_paragraphs(self, text: str) -> str:
        """
        Reformate le texte en transformant les listes en paragraphes.
        
        Utilise le LLM pour améliorer la fluidité du texte tout en
        conservant la structure Markdown.
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
            response = self._chat_and_log(prompt, "reformat_to_paragraphs")
            return response["message"]["content"].strip()
        except Exception as e:
            print(f"Error in LLM reformat: {e}")
            return text.strip()

    def enhance_markdown(self, text: str) -> str:
        """Améliore le formatage Markdown du texte."""
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
        response = self._chat_and_log(prompt, "enhance_markdown")
        return self._reformat_to_paragraphs(response["message"]["content"])

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def check_synthese(self, text: str, subject: str) -> str:
        """
        Vérifie si le résumé traite bien du sujet demandé.
        
        Returns:
            "True" ou "False" en string
        """
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
        response = self._chat_and_log(prompt, "check_synthese")
        return response["message"]["content"]

    # =========================================================================
    # CHUNKING
    # =========================================================================

    def chunk_text(self, text: str) -> List[str]:
        """Découpe le texte en chunks de taille appropriée."""
        max_chars = self._get_chunk_size()
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_chars
            if end < len(text):
                # Chercher la fin d'un mot
                space_pos = text.rfind(" ", start, end)
                if space_pos != -1:
                    end = space_pos
            chunks.append(text[start:end].strip())
            start = end
            
        return chunks

    def sumarize_part_chunk(self, text: str) -> List[str]:
        """Résume chaque chunk d'un texte long."""
        chunks = self.chunk_text(text)
        partial_summaries = []
        
        # Log chunks pour debug
        self._log_chunks(chunks)
        
        for chunk in tqdm(chunks, desc="Analyse des chunks", unit="chunk"):
            summary = self.summarize_chunk(chunk)
            partial_summaries.append(summary)
            
        return partial_summaries
    
    def _log_chunks(self, chunks: List[str]) -> None:
        """Log les chunks pour debug."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chunks_dir = os.path.join("debug", "debug_prompts", "raw_chunks", timestamp)
            os.makedirs(chunks_dir, exist_ok=True)
            
            for i, chunk in enumerate(chunks):
                file_path = os.path.join(chunks_dir, f"chunk_{i + 1}.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(chunk)
        except Exception as e:
            print(f"Error logging chunks: {e}")

    def summarize_long_text(self, text: str, author: str) -> str:
        """
        Résume un texte long en le découpant en chunks.
        
        Args:
            text: Texte à résumer
            author: Auteur/source du texte
            
        Returns:
            Résumé complet
        """
        text_parts = self.sumarize_part_chunk(text)
        combined_text = "\n\n".join(text_parts)
        
        # Sauvegarder pour debug
        current_time = time.localtime()
        formatted_time = time.strftime("%H-%M-%S", current_time)
        write_data(
            output_dir='chunk_data', 
            data=combined_text, 
            seg=f"{author}_{formatted_time}"
        )
        
        return combined_text.strip()

    # =========================================================================
    # REFINEMENT
    # =========================================================================

    def refine_summary(self, current_summary: str, instructions: str) -> str:
        """
        Affine un résumé selon les instructions utilisateur.
        
        Args:
            current_summary: Résumé actuel à modifier
            instructions: Instructions de modification
            
        Returns:
            Résumé modifié
        """
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
        response = self._chat_and_log(prompt, "refine_summary")
        return self._reformat_to_paragraphs(response["message"]["content"])
