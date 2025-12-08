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
- Hiérarchiser l'information par importance.

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

Tu es un rédacteur technique chargé de produire la DOCUMENTATION DE RÉFÉRENCE définitive de ce contenu.

OBJECTIFS PRIORITAIRES :
1.  **Exhaustivité Totale** : Le lecteur ne doit plus jamais avoir besoin de consulter l'original. Tout doit être là.
2.  **Volume** : Produis un texte long (minimum 1500 mots si le contenu le permet), dense et fouillé.
3.  **Clarté Structurelle** : Utilise abondamment les titres (H2) et sous-titres (H3).

CONSIGNES DE STRUCTURE ET TITRES :
-   **Structure** : [Titre d'ouverture Thématique] -> Développement -> [Titre de fin Thématique].
-   **TITRES ÉLÉGANTS OBLIGATOIRES** :
    -   Pour l'ouverture, CHOISIR UN TITRE ÉVOCATEUR (ex: "Contexte et Enjeux", "Les Racines du Problème", "Vue d'Ensemble").
    -   Pour la fin, CHOISIR UN TITRE ÉVOCATEUR (ex: "Perspectives d'Avenir", "Synthèse et Implications", "Le Mot de la Fin").
    -   INTERDIT : "Introduction", "Conclusion", "Résumé", "Abstract".

CONSIGNES DE RÉDACTION :
-   **Développement** : Suis le déroulé logique. Chaque argument doit être développé dans sa propre sous-section.
-   **Détails Techniques** : Conserve tous les chiffres, dates, noms propres et terminologies spécifiques.
-   **STYLE** : Rédige UNIQUEMENT des paragraphes complets.

INTERDITS ABSOLUS :
-   **PAS DE TEXTE D'INTRODUCTION** (ex: "Voici le code..."). Commence DIRECTEMENT par le Titre du document.
-   **PAS DE RÉPÉTITION** : Vérifie qu'aucune section ne duplique le contenu d'une autre.
-   Pas d'hallucinations.
"""
        elif context == "multi":
            return f"""
Sources :
{text['content']}

Sujet : {text['search']}

Tu es un expert en rédaction de dossiers documentaires approfondis. Ta mission est de produire un DOSSIER COMPLET et EXHAUSTIF sur le sujet.

OBJECTIFS PRIORITAIRES :
1.  **Densité Informationnelle MAXIMALE** : Ne laisse AUCUN détail de côté. Croise les sources mais conserve la richesse de chacune.
2.  **Longueur conséquente** : Vise un document de référence de 1500 à 2500 mots. Il est interdit de faire court.
3.  **Structure Granulaire** : Descends dans le détail (H2 > H3).

CONSIGNES DE STRUCTURE ET TITRES :
-   **Structure** : [Titre d'ouverture Thématique] -> Développement -> [Titre de fin Thématique].
-   **TITRES ÉLÉGANTS OBLIGATOIRES** :
    -   Pour l'ouverture, CHOISIR UN TITRE ÉVOCATEUR (ex: "Contexte et Enjeux", "Les Racines du Problème", "Vue d'Ensemble").
    -   Pour la fin, CHOISIR UN TITRE ÉVOCATEUR (ex: "Perspectives d'Avenir", "Synthèse et Implications", "Le Mot de la Fin").
    -   INTERDIT : "Introduction", "Conclusion", "Résumé", "Abstract".

CONSIGNES DE RÉDACTION :
-   **Développement Thématique** (Plusieurs sections H2) :
    -   Pour chaque thème, développe plusieurs sous-parties (H3).
    -   Intègre les chiffres et faits précis des vidéos.
-   **Analyse Comparative** : Si les sources divergent, explique précisément en quoi.
-   **STYLE** : Rédige UNIQUEMENT des paragraphes complets.

CONTRAINTES STRICTES :
-   **INTERDICTION DE TEXTE D'INTRODUCTION OU DE FIN** (ex: "J'espère que ceci vous aide", "Voici le code markdown").
-   **COMMENCE DIRECTEMENT** par le titre principal (H1).
-   **INTERDICTION DE RÉSUMER** : Tu ne dois pas "synthétiser" pour raccourcir, mais "compiler" pour tout garder.
-   **PAS DE RÉPÉTITION** : Ne répète pas les mêmes paragraphes.
-   Ton : Encyclopédique, neutre, précis.
-   NE JAMAIS INVENTER : Base-toi uniquement sur les sources fournies.
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
