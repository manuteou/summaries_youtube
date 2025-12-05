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
            return 10000
        elif self.summary_type == "medium":
            return 20000
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
- **Synthèse courte des éléments** : Aller droit au but.
- Synthèse claire, concise et percutante.
- Mettre en avant les idées principales et les points clés uniquement.
- Éliminer tout détail superflu.
- Donner un titre thématique et descriptif (jamais générique) à toutes les parties.
- Mettre en avant les actions attendues par les participants et les campus.
- Les informations descendantes doivent être mises en avant dans le texte.

📑 Contraintes de sortie :
- Langue : français
- Style : rédigé en paragraphes clairs et professionnels.
- Ton : neutre, direct et informatif.
- Longueur : environ 200 mots (cible indicative, privilégier la concision).
- Pas de conclusion.
- La sortie doit être uniquement le résumé demandé.
- Interdiction absolue d'afficher ton raisonnement, tes étapes ou une partie "think".
- Il est interdit de donner autre chose que le résumé en sortie.
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document" dans les titres ou le texte.
- Éviter les listes à puces, privilégier la rédaction.
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
Tu es un rédacteur professionnel. Ta mission est de créer une synthèse concise à partir des informations suivantes :
Sujet : {text['search']}
Sources : {text['content']}

🎯 Objectif :
Produire un texte fluide et direct qui synthétise les informations clés des différentes sources sur le sujet demandé.

⛔ CONTRAINTES STRICTES (A RESPECTER IMPÉRATIVEMENT) :
- PAS de méta-commentaires (ex: "Voici le résumé", "Ce document présente...", "Dans cette synthèse...").
- PAS de phrases introductives sur ta méthode de travail (ex: "Cette tâche requiert...", "L'objectif est de...").
- PAS de plan annoncé (ex: "Nous verrons d'abord...").
- COMMENCE DIRECTEMENT par le contenu du sujet.
- Ton neutre et informatif.
- Pas de listes à puces. Utilise des paragraphes.
- Langue : Français.

Le résultat doit ressembler à un article de presse ou une note de synthèse professionnelle, pas à une réponse de chatbot.
"""

        # --- MEDIUM MODE (Balanced) ---
        elif self.summary_type == "medium":
            if context == "chunk":
                return f"""
Tu es un assistant expert en synthèse de documents.

Texte à résumer :
{text}

🎯 Objectifs :
- **Synthèse de longueur moyenne** : Équilibre parfait entre détails et concision.
- Produire un résumé équilibré et STRUCTURÉ.
- Capturer l'essentiel tout en conservant les nuances importantes.
- Développer les points clés avec des explications claires.

STRUCTURE OBLIGATOIRE :
- Utilise des **Titres H2 (##)** pour les grandes thématiques.
- Utilise des **Titres H3 (###)** pour les sous-sections.
- Le but est de générer un sommaire détaillé automatiquement.

📑 Contraintes :
- Langue : français
- Longueur : environ 500 mots (ou plus si nécessaire pour la clarté).
- Style : professionnel, fluide et agréable à lire.
- Pas de méta-commentaires (ex: "Voici le résumé").
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- NE JAMAIS inventer de dates, de lieux ou de noms s'ils ne sont pas explicitement dans le texte.
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
"""
            elif context == "full_text":
                return f"""
Tu es un assistant expert en synthèse.

Texte à résumer :
{text}

🎯 Objectifs :
- Fournir une vue d'ensemble complète et STRUCTURÉE.
- Détailler les informations descendantes et les actions attendues.
- Hiérarchiser l'information par importance.

STRUCTURE OBLIGATOIRE :
- Utilise des **Titres H2 (##)** pour les sections principales.
- Utilise des **Titres H3 (###)** pour les détails spécifiques.
- Cela permettra de générer une table des matières claire.

📑 Contraintes :
- Langue : français
- Longueur : environ 500-800 mots.
- Structure : [Choisir un titre d'intro] -> Développement par thèmes -> [Choisir un titre de conclusion].
- Pour l'Introduction, CHOISIR UN SEUL titre parmi cette liste :
  * "Aux Sources de la Réflexion"
  * "De Quoi Parlons-Nous ?"
  * "Le Début du Chemin"
  * "Les Fondations"
  * "La Question Initiale"
- Pour la Conclusion, CHOISIR UN SEUL titre parmi cette liste :
  * "Ce Qu'il Faut Retenir"
  * "Le Mots de la Fin"
  * "Ainsi s'achève notre exploration"
  * "Les Grandes Lignes"
  * "L'Essentiel"
- Style : Rédaction soignée, paragraphes bien construits.
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- NE JAMAIS inventer de dates, de lieux ou de noms s'ils ne sont pas explicitement dans le texte.
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
- Produire un texte cohérent et fluide.

STRUCTURE OBLIGATOIRE :
- Utilise des **Titres H2 (##)** pour les axes d'analyse.
- Utilise des **Titres H3 (###)** pour les points de détail.

📑 Contraintes :
- Langue : français
- Longueur : Suffisante pour couvrir le sujet en profondeur (environ 1000 mots).
- Structure : [Choisir un titre d'intro] -> Analyse thématique -> [Choisir un titre de conclusion].
- Pour l'Introduction, CHOISIR UN SEUL titre parmi cette liste :
  * "Aux Sources de la Réflexion"
  * "De Quoi Parlons-Nous ?"
  * "Le Début du Chemin"
  * "Les Fondations"
  * "La Question Initiale"
- Pour la Conclusion, CHOISIR UN SEUL titre parmi cette liste :
    * "Ce Qu'il Faut Retenir"
    * "Le Mots de la Fin"
    * "Ainsi s'achève notre exploration"
    * "Les Grandes Lignes"
    * "L'Essentiel"
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- FUSIONNER les informations. NE PAS dire "Les sources disent", "La première vidéo...". Rédiger un texte unique et cohérent.
- NE JAMAIS inventer de dates, de lieux ou de noms s'ils ne sont pas explicitement dans le texte.
- Interdiction d'utiliser les mots "Résumé", "Ce résumé", "Résumé des points clés", "Ce document"
"""

        # --- LONG MODE (Exhaustive) ---
        elif self.summary_type == "long":
            if context == "chunk":
                return f"""
Texte à traiter :
{text}

Tu es un moteur d'extraction d'information haute fidélité. Ta tâche est de traiter une SECTION d'un document pour en extraire TOUTE la substance.

🎯 Objectifs :
-   **Densité maximale** : Ne résume pas. Reformule de manière dense mais conserve 100% des informations factuelles (chiffres, noms, dates, arguments).
-   **Structure** : Utilise des sous-titres (H3) pour organiser les idées au sein de ce bloc.
-   **Style** : Académique, précis, exhaustif.

⛔ CONTRAINTES :
-   Ne supprime aucun détail technique.
-   Pas de "titre de document" (c'est juste un fragment).
-   Pas de méta-commentaires.
"""
            elif context == "full_text":
                return f"""
Texte à traiter :
{text}

Tu es un rédacteur technique chargé de produire la DOCUMENTATION DE RÉFÉRENCE définitive de ce contenu.

🎯 OBJECTIFS PRIORITAIRES :
1.  **Exhaustivité Totale** : Le lecteur ne doit plus jamais avoir besoin de consulter l'original. Tout doit être là.
2.  **Volume** : Produis un texte long (minimum 1500 mots si le contenu le permet), dense et fouillé.
3.  **Clarté Structurelle** : Utilise abondamment les titres (H2) et sous-titres (H3) pour organiser cette masse d'informations.

CONSIGNES DE RÉDACTION :
-   **Introduction** : Pose le cadre complet (qui, quoi, où, quand, pourquoi).
-   **Développement** : Suis le déroulé logique. Chaque argument doit être développé dans sa propre sous-section.
-   **Détails Techniques** : Conserve tous les chiffres, dates, noms propres et terminologies spécifiques.

⛔ INTERDITS :
-   Pas de "résumé" ou de "synthèse rapide".
-   Pas de phrases génériques.
-   Pas d'hallucinations.
-   L'expression "Compte-Rendu" est interdite.
"""
            elif context == "multi":
                return f"""
Sources :
{text['content']}

Sujet : {text['search']}

Tu es un expert en rédaction de dossiers documentaires approfondis. Ta mission est de produire un DOSSIER COMPLET et EXHAUSTIF sur le sujet.

🎯 OBJECTIFS PRIORITAIRES :
1.  **Densité Informationnelle MAXIMALE** : Ne laisse AUCUN détail de côté. Croise les sources mais conserve la richesse de chacune.
2.  **Longueur conséquente** : Vise un document de référence de 1500 à 2500 mots. Il est interdit de faire court.
3.  **Structure Granulaire** : Descends dans le détail (H2 > H3 > Listes détaillées).

STRUCTURE OBLIGATOIRE :
-   **Introduction Détaillée** : Contexte, définitions, enjeux.
-   **Développement Thématique** (Plusieurs sections H2) :
    -   Pour chaque thème, développe plusieurs sous-parties (H3).
    -   Intègre les chiffres et faits précis des vidéos.
-   **Analyse Comparative** : Si les sources divergent, explique précisément en quoi.
-   **Conclusion Synthétique**.

⛔ CONTRAINTES STRICTES :
-   **INTERDICTION DE RÉSUMER** : Tu ne dois pas "synthétiser" pour raccourcir, mais "compiler" pour tout garder.
-   **Ton** : Encyclopédique, neutre, précis.
-   **Pas de méta-commentaires** ("Dans ce dossier...", "Nous allons voir...").
-   **NE JAMAIS INVENTER** : Base-toi uniquement sur les sources fournies.
"""
        return ""

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
        - Pas de méta-commentaires.
        - Pas d'hallucinations.
        - Ne pas utiliser "Compte-Rendu Exhaustif".
        """
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options={"num_ctx": 8192, "num_predict":-1})
        return response["message"]["content"]

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
            
            ⛔ CONTRAINTES STRICTES (A RESPECTER IMPÉRATIVEMENT) :
            - PAS de méta-commentaires (ex: "Voici le texte...", "J'ai amélioré...").
            - PAS de phrases introductives.
            - SORTIE PURE : Uniquement le code Markdown du document.

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
