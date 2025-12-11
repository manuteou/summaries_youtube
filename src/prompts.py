from typing import List, Union

class PromptManager:
    def get_prompt(self, summary_type: str, context: str, text: str) -> str:
        """
        Retrieves the appropriate prompt based on summary type and context.
        """
        if summary_type == "short":
            return self._get_short_prompt(context, text)
        elif summary_type == "medium":
            return self._get_medium_prompt(context, text)
        elif summary_type == "long":
            return self._get_long_prompt(context, text)
        elif summary_type == "news":
            return self._get_news_prompt(context, text)
        elif summary_type == "analysis":
             return self._get_analysis_prompt(context, text)
        else:
            return self._get_short_prompt(context, text) # Default

    def _get_short_prompt(self, context: str, text: str) -> str:
        if context == "chunk":
            return f"""
   Tu es un assistant qui doit produire uniquement un résumé.

Texte à résumer (issu d'une transcription audio) :
{text}

OBJECTIFS :
- **Synthèse courte des éléments** : Aller droit au but.
- Synthèse claire, concise et percutante.
- Mettre en avant les idées principales et les points clés uniquement.
- Éliminer tout détail superflu.
- Donner un titre thématique et descriptif (jamais générique) à toutes les parties.
- Mettre en avant les actions attendues par les participants et les campus.
- Les informations descendantes doivent être mises en avant dans le texte.

CONTRAINTES DE SORTIE :
- Langue : français
- Style : rédigé en paragraphes clairs et professionnels.
- Ton : neutre, direct et informatif.
- Longueur : environ 200 mots (cible indicative, privilégier la concision).
- Pas de conclusion.
- La sortie doit être uniquement le résumé demandé.
"""
        elif context == "full_text":
            return f"""
Tu es un assistant qui doit produire uniquement un résumé.

Texte à résumer (issu d'une transcription audio) :
{text}

OBJECTIFS :
- Synthèse claire, concise et fidèle au contenu
- Mettre en avant les idées principales et les points clés
- Éliminer les détails superflus ou les répétitions
- Donner un titre thématique et descriptif (jamais générique) à toutes les parties
- Mettre en avant les actions attendues par les participants et les campus
- Identifier et hiérarchiser toutes les informations descendantes (directives, décisions, annonces)
- Distinguer clairement les informations descendantes des actions attendues
- Mentionner les responsables ou destinataires si précisés

CONTRAINTES DE SORTIE :
- Langue : français
- Style : rédigé en paragraphes clairs et professionnels
- Ton : neutre et informatif
- Longueur : environ 200 mots
- Pas de conclusion
- La sortie doit être uniquement le résumé demandé
- Le résumé doit être structuré en deux sections : 
  1. Informations descendantes
  2. Actions attendues
"""
        elif context == "multi":
            return f"""
Tu es un rédacteur professionnel. Ta mission est de créer une synthèse concise à partir des informations suivantes :
Sujet : {text['search']}
Sources : {text['content']}

OBJECTIF :
Produire un texte fluide et direct qui synthétise les informations clés des différentes sources sur le sujet demandé.

CONTRAINTES STRICTES :
- COMMENCE DIRECTEMENT par le contenu du sujet.
- Ton neutre et informatif.
- Langue : Français.

Le résultat doit ressembler à un article de presse ou une note de synthèse professionnelle.
"""
        return ""

    def _get_medium_prompt(self, context: str, text: str) -> str:
        if context == "chunk":
            return f"""
Tu es un assistant expert en synthèse de documents.

Texte à résumer :
{text}

OBJECTIFS :
- **Synthèse de longueur moyenne** : Équilibre parfait entre détails et concision.
- Produire un résumé équilibré et STRUCTURÉ.
- Capturer l'essentiel tout en conservant les nuances importantes.
- Développer les points clés avec des explications claires.

STRUCTURE OBLIGATOIRE :
- Utilise des **Titres H2 (##)** pour les grandes thématiques.
- Utilise des **Titres H3 (###)** pour les sous-sections.
- Le but est de générer un sommaire détaillé automatiquement.

CONTRAINTES :
- Langue : français
- Longueur : environ 500 mots (ou plus si nécessaire pour la clarté).
- Style : professionnel, fluide et agréable à lire.
- COMMENCER DIRECTEMENT par le contenu.
- Ton IMPERSONNEL et OBJECTIF. Pas de "Je", "Mon", "Nous".
- NE JAMAIS inventer de dates, de lieux ou de noms s'ils ne sont pas explicitement dans le texte.
"""
        elif context == "full_text":
            return f"""
Tu es un assistant expert en synthèse.

Texte à résumer :
{text}

OBJECTIFS :
- Fournir une vue d'ensemble complète et STRUCTURÉE.
- Détailler les informations descendantes et les actions attendues.
- Hiérarchiser l'information.

STRUCTURE OBLIGATOIRE :
- Utilise des **Titres H2 (##)** pour les sections principales.
- Utilise des **Titres H3 (###)** pour les détails spécifiques.
- Cela permettra de générer une table des matières claire.

CONTRAINTES :
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
"""
        elif context == "multi":
            return f"""
Rédige une synthèse thématique sur : {text['search']}.

Sources :
{text['content']}

OBJECTIFS :
- Croiser les informations des différentes sources.
- Identifier les tendances et les consensus.
- Produire un texte cohérent et fluide.

STRUCTURE OBLIGATOIRE :
- Utilise des **Titres H2 (##)** pour les axes d'analyse.
- Utilise des **Titres H3 (###)** pour les points de détail.

CONTRAINTES :
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
"""
        return ""

    def _get_long_prompt(self, context: str, text: str) -> str:
        if context == "chunk":
            return f"""
Texte à traiter :
{text}

Tu es un moteur d'extraction d'information haute fidélité. Ta tâche est de traiter une SECTION d'un document pour en extraire TOUTE la substance.

OBJECTIFS :
-   **Densité maximale** : Ne résume pas. Reformule de manière dense mais conserve 100% des informations factuelles (chiffres, noms, dates, arguments).
-   **Structure** : Utilise des sous-titres (H3) pour organiser les idées au sein de ce bloc.
-   **Style** : Académique, précis, exhaustif.

CONTRAINTES :
-   Ne supprime aucun détail technique.
-   Pas de "titre de document" (c'est juste un fragment).
"""
        elif context == "full_text":
            return f"""
Texte à traiter :
{text}

Tu es un Éditeur Senior dans un grand média d'analyse. Ta mission est de transformer ce contenu brut en un ARTICLE DE FOND de qualité "Premium", destiné à être publié.

OBJECTIFS EDITORIAUX :
1.  **Exhaustivité Narrée** : Tu dois tout dire, mais avec style. Ne fais pas une liste, RACONTE le contenu.
2.  **Longueur & Profondeur** : Nous visons un article "Long-Form" (minimum 1500-2000 mots). Prends le temps d'expliquer chaque concept.
3.  **Ton** : Sophistiqué, fluide, analytique mais accessible. Comme un excellent article du "Harvard Business Review" ou du "Monde Diplomatique".

CONSIGNES DE STRUCTURE :
-   **TITRE** : Trouve un titre accrocheur et élégant (Pas de "Résumé de...", sois créatif).
-   **INTRODUCTION** : Une vraie introduction journalistique qui pose le contexte, les enjeux et la problématique, sans dire "ce texte parle de...". Plonge le lecteur dedans.
-   **CORPS DU TEXTE** :
    -   Utilise des intertitres (H2) thématiques forts.
    -   Utilise des sous-titres (H3) pour aérer.
    -   Rédige des PARAGRAPHES CONSISTANTS. Pas de phrases isolées.
    -   Intègre les citations clés ou les chiffres marquants naturellement dans le récit.
-   **CONCLUSION** : Une ouverture vers l'avenir ou une synthèse des impacts majeurs.

INTERDITS :
-   PAS DE LISTES À PUCES (sauf si absolument nécessaire pour une énumération technique). Privilégie la rédaction.
-   PAS DE PHRASES ROBOTIQUES comme "Dans cette section...", "L'auteur nous dit que...". Écris directement les faits.
-   PAS DE "INTRODUCTION" ou "CONCLUSION" comme titres de section. Trouve des titres plus élégants.

RÉGLAGE DE LA LONGUEUR :
-   Il est CRITIQUE que tu fournisses le maximum de détails. Si le texte original est long, ton article DOIT être long. Ne synthétise pas pour raccourcir, mais reformule pour clarifier.

"""
        elif context == "multi":
            return f"""
Sources :
{text['content']}

Sujet : {text['search']}

Tu es un Journaliste d'Investigation Spécialisé. Tu dois rédiger un DOSSIER COMPLET sur le sujet, en croisant ces sources.

OBJECTIF : Créer le dossier de référence ultime sur ce thème.

LA FORME :
-   Un véritable ARTICLE DE PRESSE ou un CHAPITRE DE LIVRE.
-   Longueur : Vise 2000 mots ou plus. Sois intarissable sur les détails.

STRUCTURE NARRATIVE :
1.  **Titre Percutant** (H1).
2.  **Chapeau** : Résumé exécutif de 3-4 lignes en gras pour donner envie de lire.
3.  **Le Dossier** :
    -   Organise ton propos par thèmes logiques (H2), pas source par source.
    -   Développe chaque point avec précision (H3).
    -   Si les sources sont d'accord, fusionne l'info.
    -   Si elles divergent, mets en scène le débat ("Alors que X soutient ceci, Y nuance par cela...").
4.  **Des encadrés** : Tu peux utiliser des citations en italique pour donner de la vie.

TON ET STYLE :
-   Élégant, riche, vocabulaire précis.
-   Fluidité absolue : Les transitions entre paragraphes doivent être invisibles.
-   JAMAIS de "Dans la première vidéo...". Intègre les sources comme si tu avais fait les interviews toi-même.

ATTENTION :
-   Ceci n'est pas un résumé scolaire. C'est une œuvre de rédaction.
-   Prends de la hauteur. Analyse les implications.
"""
        return ""

    def _get_news_prompt(self, context: str, text: str) -> str:
        if context == "chunk":
            return f"""
Texte à analyser (fragment) :
{text}

Tu es un journaliste d'investigation chargé de repérer les ACTUALITÉS et NOUVEAUTÉS.
OBJECTIFS :
- Extraire UNIQUEMENT les faits récents, les annonces, les dates clés et les changements.
- Ignorer le "bruit" (intros, blabla, contexte général connu).
- Si une information est datée ou semble nouvelle, garde-la précieusement.

Sortie attendue :
- Liste de points concis et factuels.
"""
        elif context == "full_text":
            return f"""
Texte à traiter :
{text}

Tu es Rédacteur en Chef d'un site d'actualité technologique/scientifique.
OBJECTIF : Rédiger un ARTICLE D'ACTUALITÉ percutant.

STRUCTURE DE L'ARTICLE :
1. **TITRE ACCROCHEUR** (H1) : Doit donner l'info principale.
2. **LEAD / CHAPÔ** (en gras) : Résumé de 2 phrases qui répond aux questions : Quoi ? Quand ? Qui ?
3. **CORPS DE L'ARTICLE** (H2 pour les sections) :
    - Les nouveautés en détail.
    - Les implications concrètes.
    - Ce qui change par rapport à avant.

STYLE :
- Journalistique, phrase courtes, présent de l'indicatif.
- CITE TES SOURCES : "Selon la vidéo X...", "Comme annoncé le [Date]..."
- METS EN AVANT LA DATE.
"""
        elif context == "multi":
            return f"""
Sources (classées par ordre chronologique, les plus récentes en PREMIER) :
{text['content']}

Sujet : {text['search']}

Tu es un JOURNALISTE EXPERT. Tu dois rédiger un article de synthèse sur les **DERNIÈRES ACTUALITÉS** concernant ce sujet.
IMPORTANT : Les informations les plus récentes (en haut de la liste des sources) ont LA PRIORITÉ ABSOLUE.

OBJECTIFS :
1.  **NOUVEAUTÉ AVANT TOUT** : Commence par ce qui vient de se passer (cette semaine/ce mois).
2.  **CONFRONTATION** : "Alors que [Source Ancienne] prévoyait X, [Source Récente] confirme Y."
3.  **PRÉCISION** : Cite les dates et les acteurs.

STRUCTURE OBLIGATOIRE :
-   **TITRE JOURNALISTIQUE** (H1) : Doit contenir un verbe d'action et l'info clé.
-   **DATELINE** : "Synthèse actualisée au [Date du jour]" (en italique).
-   **LEAD (Chapô)** : L'essentiel en 3 lignes.
-   **LE CŒUR DE L'ACTU** (H2) : Les faits les plus récents et importants.
-   **ANALYSE & CONTEXTE** (H2) : Pour comprendre pourquoi c'est important.
-   **CE QU'IL FAUT SURVEILLER** (H2) : Prochaines étapes/dates.

RÈGLES D'OR :
-   Ton : Dynamique, informatif, "Breaking News".
-   Utilise le **gras** pour les infos cruciales.
-   Hésite pas à utiliser des encadrés markdown ( > Citation) pour les déclarations chocs.
-   Si les sources se contredisent, la source la plus RÉCENTE a raison (mais mentionne le changement).
"""
        return ""

    def _get_analysis_prompt(self, context: str, text: Union[str, dict]) -> str:
        if context == "global":
            # Handle both string (legacy) and dict (with instructions)
            content = text
            instructions = ""
            if isinstance(text, dict):
                content = text.get('content', '')
                instructions = text.get('instructions', '')

            instruction_block = ""
            if instructions:
                instruction_block = f"\n\nCONSIGNE SPÉCIFIQUE DU RÉDACTEUR EN CHEF :\n{instructions}\n(Tu DOIS respecter cette consigne priorité)\n"

            return f"""
Tu es un Rédacteur en Chef d'un grand média.
Voici un ensemble de notes détaillées provenant de plusieurs sources ou sections :
{content}

{instruction_block}
Ta mission est de RÉDIGER LE DOCUMENT FINAL COMPLET. Il s'agit d'une fusion intégrale de toutes les informations.

OBJECTIF SUPRÊME :
Produire un **ARTICLE DE FOND UNIQUE** (Type Long-Form) qui intègre TOUTES les informations des notes fournies.

CE N'EST PAS UNE INTRODUCTION. C'EST LE DOCUMENT ENTIER.

CONSIGNES DE RÉDACTION :
1.  **FUSION DES SOURCES** : Ne fais pas de sections "Source 1", "Source 2". Organise le texte par **THÈMES**.
    -   Exemple : Si la Source A et la Source B parlent de "Prix", fais une section "Analyse des Prix" qui combine les deux.
2.  **LONGUEUR MASSIVE** : Vise un texte très long et détaillé (minimum 1500-2000 mots). Ne synthétise pas pour réduire, mais pour organiser.
    -   Si tu as 3 pages de notes, produis 3 pages d'article.
    -   Garde TOUS les chiffres, TOUS les exemples, TOUTES les nuances.
3.  **STYLE** : Fluide, narratif, expert. Pas de listes à puces.
4.  **TITRES** : Utilise une hiérarchie claire (H1 Titre, H2 Parties, H3 Sous-parties).

INTERDIT :
-   Pas de section "Détails des sources" à la fin. Tout doit être intégré DANS le texte principal.
-   Pas de "Introduction" / "Conclusion" génériques.
-   Pas de répétitions.

STRUCTURE SUGGÉRÉE :
-   **TITRE PERCUTANT** (H1)
-   **CHAPEAU** (Résumé 3 lignes)
-   **LE CŒUR DU SUJET** (Organisé par thèmes H2/H3 - 90% du texte)
-   **SYNTHÈSE FINALE** (Ouverture)
"""
        return ""
