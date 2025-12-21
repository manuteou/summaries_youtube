"""
prompts.py - Refactored prompt management with Registry pattern (OCP)

Ce module utilise le pattern Registre pour permettre l'ajout de nouveaux
types de prompts sans modifier le code existant (Open/Closed Principle).

Optimisations v2.0:
- Système de citations numérotées [1], [2], etc.
- Anti-hallucination renforcé
- Structure standardisée: OBJECTIFS > STRUCTURE > CONTRAINTES > INTERDITS
- Titres flexibles et thématiques
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, Union, Any


# =============================================================================
# BLOCS RÉUTILISABLES
# =============================================================================

CITATION_INSTRUCTIONS = """
SYSTÈME DE CITATION OBLIGATOIRE :
1. Les sources sont DÉJÀ NUMÉROTÉES au début du texte : [1], [2], [3], etc.
2. Tu dois UNIQUEMENT utiliser ces numéros pour citer. Exemple : "L'IA progresse rapidement [1]."
3. INTERDIT ABSOLU : N'invente JAMAIS de nouvelles sources ou références.
4. INTERDIT : Ne cite pas des livres, articles, sites web, Wikipedia, ou toute source qui n'est pas dans la liste fournie.
5. À LA FIN du document, recopie UNIQUEMENT les sources fournies dans une section "### Sources" :
   [1] Titre exact de la vidéo 1
   [2] Titre exact de la vidéo 2
   ...
6. RÈGLE D'OR : Si une information n'est pas dans les sources fournies, NE L'INCLUS PAS.
"""

ANTI_HALLUCINATION = """
VÉRIFICATION ANTI-HALLUCINATION :
- Chaque date, nom, chiffre que tu écris DOIT être présent dans le texte source.
- En cas de doute sur une information, utilise "(non précisé dans la source)".
- N'INVENTE JAMAIS de données, même si elles semblent logiques.
- Si le texte est flou sur un point, reflète cette ambiguïté.

SOURCES - RÈGLE ABSOLUE :
- N'INVENTE JAMAIS de références bibliographiques (livres, articles, Wikipedia, etc.)
- Utilise UNIQUEMENT les sources numérotées [1], [2], [3] fournies au début du texte.
- Si tu cites [4] et qu'il n'y a que 3 sources, c'est une ERREUR.
"""

STYLE_IMPERSONNEL = """
STYLE :
- Ton IMPERSONNEL et OBJECTIF.
- INTERDIT : "Je", "Mon", "Nous", "Vous".
- COMMENCE DIRECTEMENT par le contenu (pas de "Voici...", "Je vais...").
"""


class PromptTemplate(ABC):
    """
    Classe de base abstraite pour tous les templates de prompts.
    Chaque type de résumé hérite de cette classe (OCP).
    """
    
    @abstractmethod
    def get_chunk_prompt(self, text: str) -> str:
        """Prompt pour traiter un chunk de texte."""
        ...
    
    @abstractmethod
    def get_full_text_prompt(self, text: str) -> str:
        """Prompt pour traiter un texte complet."""
        ...
    
    @abstractmethod
    def get_multi_prompt(self, search: str, content: str) -> str:
        """Prompt pour synthétiser plusieurs sources."""
        ...


class ShortPromptTemplate(PromptTemplate):
    """Template pour les résumés courts - Optimisé pour la densité et la concision."""
    
    def get_chunk_prompt(self, text: str) -> str:
        return f"""Tu es un assistant spécialisé dans la synthèse ultra-concise.

Texte à résumer (transcription audio) :
{text}

OBJECTIFS :
- Synthèse COURTE et PERCUTANTE (3-5 paragraphes maximum).
- Priorité aux données chiffrées, noms propres et faits concrets.
- Éliminer tout détail superflu, anecdotes et répétitions.
- Titres thématiques et descriptifs (JAMAIS génériques comme "Introduction").

STRUCTURE :
- Paragraphes courts et denses.
- Pas de listes à puces sauf si absolument nécessaire.

CONTRAINTES :
- Langue : français
- Longueur : MAXIMUM 200 mots (vérifie avant de terminer).
- Pas de conclusion.

{ANTI_HALLUCINATION}
{STYLE_IMPERSONNEL}
"""

    def get_full_text_prompt(self, text: str) -> str:
        return f"""Tu es un assistant expert en synthèse concise.

Texte à résumer (transcription audio) :
{text}

OBJECTIFS :
- Synthèse claire et fidèle au contenu.
- Mettre en avant : 1) Informations descendantes 2) Actions attendues.
- Identifier les responsables et destinataires si mentionnés.
- Priorité aux données chiffrées et décisions concrètes.

STRUCTURE OBLIGATOIRE :
## Informations Clés
(Directives, décisions, annonces importantes)

## Actions Attendues
(Qui doit faire quoi, avec échéances si mentionnées)

CONTRAINTES :
- Langue : français
- Longueur : MAXIMUM 200 mots.
- Pas de conclusion ni de résumé final.

{ANTI_HALLUCINATION}
{STYLE_IMPERSONNEL}
"""

    def get_multi_prompt(self, search: str, content: str) -> str:
        return f"""Tu es un rédacteur professionnel.

Sujet : {search}

LISTE DES SOURCES AUTORISÉES :
{content}

⚠️ RÈGLE CRITIQUE - SOURCES ⚠️
- Utilise UNIQUEMENT les sources numérotées [1], [2], [3] listées ci-dessus.
- N'INVENTE JAMAIS de références (Wikipedia, livres, articles, etc.).

{CITATION_INSTRUCTIONS}

OBJECTIFS :
- Créer une synthèse concise croisant les informations des sources.
- Chaque fait doit être sourcé avec [1], [2], etc.
- Produire un texte fluide, style note de synthèse professionnelle.

SECTION SOURCES FINALE :
À la fin, ajoute "### Sources" avec les titres exacts des vidéos.

CONTRAINTES :
- Langue : français
- Longueur : 200-300 mots maximum.
- Commence DIRECTEMENT par le contenu du sujet.
- Ton neutre et informatif.
- N'INVENTE AUCUNE source.

{ANTI_HALLUCINATION}
"""


class MediumPromptTemplate(PromptTemplate):
    """Template pour les résumés moyens - Équilibre détails/concision."""
    
    def get_chunk_prompt(self, text: str) -> str:
        return f"""Tu es un assistant expert en synthèse de documents.

Texte à résumer :
{text}

OBJECTIFS :
- Synthèse ÉQUILIBRÉE : ni trop courte, ni exhaustive.
- Capturer l'essentiel avec les nuances importantes.
- Développer les points clés avec des explications claires.

STRUCTURE OBLIGATOIRE :
- Utilise des **Titres H2 (##)** pour les grandes thématiques.
- Utilise des **Titres H3 (###)** pour les sous-sections.
- CHOISIS des titres ÉVOCATEURS et THÉMATIQUES (jamais "Introduction", "Conclusion", "Partie 1").

CONTRAINTES :
- Langue : français
- Longueur : environ 500 mots.
- Style : professionnel, fluide, agréable à lire.

{ANTI_HALLUCINATION}
{STYLE_IMPERSONNEL}
"""

    def get_full_text_prompt(self, text: str) -> str:
        return f"""Tu es un assistant expert en synthèse structurée.

Texte à résumer :
{text}

OBJECTIFS :
- Vue d'ensemble complète et STRUCTURÉE.
- Détailler informations descendantes et actions attendues.
- Hiérarchiser l'information par importance.

STRUCTURE OBLIGATOIRE :
- **Titres H2 (##)** pour les sections principales.
- **Titres H3 (###)** pour les détails spécifiques.
- CHOISIS des titres ÉVOCATEURS qui reflètent le CONTENU SPÉCIFIQUE.
- INTERDIT : "Introduction", "Conclusion", "Résumé", "Partie X".

FORMAT :
[Titre d'ouverture thématique] → Développement par thèmes → [Titre de clôture thématique]

CONTRAINTES :
- Langue : français
- Longueur : 500-800 mots.
- Style : Rédaction soignée, paragraphes bien construits.

{ANTI_HALLUCINATION}
{STYLE_IMPERSONNEL}
"""

    def get_multi_prompt(self, search: str, content: str) -> str:
        return f"""Tu es un rédacteur de synthèses thématiques.

Sujet : {search}

LISTE DES SOURCES AUTORISÉES (au début du texte ci-dessous) :
{content}

⚠️ RÈGLE CRITIQUE - SOURCES ⚠️
- Les SEULES sources que tu peux citer sont celles listées ci-dessus avec [1], [2], [3], etc.
- Tu NE PEUX PAS inventer de références à Wikipedia, Nature, Scientific American, livres, etc.
- Tu NE PEUX PAS créer de nouvelles sources [4], [5], [6] si elles n'existent pas dans la liste.
- Chaque [X] dans ton texte DOIT correspondre à une source de la liste ci-dessus.

{CITATION_INSTRUCTIONS}

OBJECTIFS :
- Croiser les informations des différentes sources.
- Identifier tendances et consensus.
- Chaque fait important doit être sourcé [1], [2], etc.
- Produire un texte cohérent et fluide.

STRUCTURE OBLIGATOIRE :
- **Titres H2 (##)** pour les axes d'analyse.
- **Titres H3 (###)** pour les points de détail.
- CHOISIR des titres ÉVOCATEURS (pas "Introduction", "Conclusion").

SECTION SOURCES FINALE :
À la fin, ajoute "### Sources" et recopie EXACTEMENT les titres des vidéos :
[1] (titre exact de la source 1)
[2] (titre exact de la source 2)
...

CONTRAINTES :
- Langue : français
- Longueur : environ 800-1000 mots.
- FUSIONNER les informations : NE PAS dire "La première vidéo...", "Les sources disent...".
- Rédiger un texte UNIQUE et cohérent.
- N'INVENTE JAMAIS de sources académiques ou journalistiques.

{ANTI_HALLUCINATION}
{STYLE_IMPERSONNEL}
"""


class LongPromptTemplate(PromptTemplate):
    """Template pour les résumés longs et exhaustifs - Documentation de référence."""
    
    def get_chunk_prompt(self, text: str) -> str:
        return f"""Tu es un moteur d'extraction d'information haute fidélité.

Texte à traiter (SECTION d'un document) :
{text}

OBJECTIFS :
- **Densité maximale** : Ne résume PAS. Reformule de manière dense mais conserve 100% des informations factuelles.
- Conserver : tous les chiffres, noms, dates, arguments, exemples.
- Structure : Utilise des sous-titres (H3) pour organiser les idées.

CONTRAINTES :
- Ne supprime aucun détail technique.
- Pas de "titre de document" (c'est juste un fragment).
- Style : Académique, précis, exhaustif.

{ANTI_HALLUCINATION}
"""

    def get_full_text_prompt(self, text: str) -> str:
        return f"""Tu es un rédacteur technique produisant une DOCUMENTATION DE RÉFÉRENCE.

Texte à traiter :
{text}

OBJECTIFS PRIORITAIRES :
1. **Exhaustivité Totale** : Le lecteur ne doit plus consulter l'original. Tout doit être là.
2. **Volume** : Minimum 1500 mots si le contenu le permet.
3. **Clarté Structurelle** : Titres (H2) et sous-titres (H3) abondants.

STRUCTURE :
[Titre d'ouverture ÉVOCATEUR] → Développement détaillé → [Titre de fin ÉVOCATEUR]
- INTERDIT : "Introduction", "Conclusion", "Résumé", "Abstract".
- EXEMPLES de bons titres : "Contexte et Enjeux", "Les Racines du Problème", "Perspectives d'Avenir".

CONSIGNES :
- Chaque argument dans sa propre sous-section.
- Conserver tous les chiffres, dates, noms propres, terminologies.
- UNIQUEMENT des paragraphes complets (pas de listes).

VÉRIFICATION FINALE (avant de terminer) :
- RELIS ton texte et SUPPRIME toute phrase qui répète une idée déjà exprimée.
- Chaque section H3 doit apporter une information NOUVELLE.

{ANTI_HALLUCINATION}
{STYLE_IMPERSONNEL}

INTERDITS ABSOLUS :
- Pas de texte d'introduction ("Voici...", "Je vais...").
- Pas de répétition entre sections.
"""

    def get_multi_prompt(self, search: str, content: str) -> str:
        return f"""Tu es un expert en rédaction de dossiers documentaires approfondis.

Sujet : {search}

LISTE DES SOURCES AUTORISÉES (au début du texte ci-dessous) :
{content}

⚠️ RÈGLE CRITIQUE - SOURCES ⚠️
- Les SEULES sources que tu peux citer sont celles listées ci-dessus avec [1], [2], [3], etc.
- Tu NE PEUX PAS inventer de références à Wikipedia, Nature, Scientific American, etc.
- Tu NE PEUX PAS créer de nouvelles sources [4], [5], [6] si elles n'existent pas dans la liste.
- Chaque [X] dans ton texte DOIT correspondre à une source de la liste ci-dessus.

{CITATION_INSTRUCTIONS}

OBJECTIFS PRIORITAIRES :
1. **Densité Informationnelle MAXIMALE** : Ne laisse AUCUN détail de côté.
2. **Volume** : 1500 à 2500 mots. Il est INTERDIT de faire court.
3. **Structure Granulaire** : H2 > H3 avec citations [1], [2], etc.

STRUCTURE :
[Titre d'ouverture ÉVOCATEUR] → Développement thématique → [Titre de fin ÉVOCATEUR]
- INTERDIT : "Introduction", "Conclusion", "Résumé".
- Pour chaque thème : plusieurs sous-parties H3 avec faits sourcés.

CONSIGNES :
- Intégrer chiffres et faits précis avec leurs sources [1], [2].
- Si les sources divergent, expliquer précisément les différences.
- UNIQUEMENT des paragraphes complets.

SECTION SOURCES FINALE :
À la fin, ajoute "### Sources" et recopie EXACTEMENT les titres des vidéos :
[1] (titre exact de la source 1)
[2] (titre exact de la source 2)
...

VÉRIFICATION FINALE :
- RELIS et SUPPRIME toute répétition.
- Vérifie que chaque [X] correspond à une vraie source.
- SUPPRIME toute référence à Wikipedia, livres, articles non fournis.

{ANTI_HALLUCINATION}
{STYLE_IMPERSONNEL}

INTERDITS :
- "Voici le code markdown", "J'espère que ceci vous aide".
- Résumer pour raccourcir (tu dois COMPILER, pas synthétiser).
- Inventer des sources académiques ou journalistiques.
"""


class NewsPromptTemplate(PromptTemplate):
    """Template pour les actualités - Style journalistique avec sources précises."""
    
    def get_chunk_prompt(self, text: str) -> str:
        return f"""Tu es un journaliste d'investigation.

Texte à analyser (fragment) :
{text}

OBJECTIFS :
- Extraire UNIQUEMENT les faits RÉCENTS : annonces, dates clés, changements.
- Ignorer le "bruit" : intros, contexte général connu, blabla.
- Si une information est datée ou semble nouvelle, GARDE-LA.

SORTIE : Liste de points concis et factuels avec dates si disponibles.

{ANTI_HALLUCINATION}
"""

    def get_full_text_prompt(self, text: str) -> str:
        return f"""Tu es Rédacteur en Chef d'un site d'actualité.

Texte à traiter :
{text}

OBJECTIF : Rédiger un ARTICLE D'ACTUALITÉ percutant.

STRUCTURE DE L'ARTICLE :
1. **TITRE ACCROCHEUR** (H1) : Contient l'info principale + verbe d'action.
2. **CHAPÔ** (en gras) : 2 phrases répondant à Quoi ? Quand ? Qui ?
3. **CORPS** (H2 pour les sections) :
   - Les nouveautés en détail
   - Les implications concrètes
   - Ce qui change par rapport à avant

CITATIONS OBLIGATOIRES :
- Pour chaque fait : "[Source : Titre de la vidéo, à MM:SS]"
- Si pas de timestamp disponible, mentionner juste la source.

STYLE :
- Journalistique, phrases courtes, présent de l'indicatif.
- Mettre en **gras** les infos cruciales.
- Mettre en avant les DATES.

{ANTI_HALLUCINATION}
"""

    def get_multi_prompt(self, search: str, content: str) -> str:
        return f"""Tu es un JOURNALISTE EXPERT en synthèse d'actualités.

Sujet : {search}

LISTE DES SOURCES AUTORISÉES (les plus récentes EN PREMIER) :
{content}

⚠️ RÈGLE CRITIQUE - SOURCES ⚠️
- Utilise UNIQUEMENT les sources numérotées [1], [2], [3] listées ci-dessus.
- N'INVENTE JAMAIS de références (Reuters, AFP, journaux, Wikipedia, etc.).
- Chaque [X] DOIT correspondre à une vraie source de la liste.

{CITATION_INSTRUCTIONS}

OBJECTIFS :
1. **NOUVEAUTÉ AVANT TOUT** : Commence par ce qui vient de se passer.
2. **CONFRONTATION** : "Alors que [Source ancienne] prévoyait X [1], [Source récente] confirme Y [2]."
3. **PRÉCISION** : Cite dates et acteurs avec sources [1], [2], etc.

STRUCTURE OBLIGATOIRE :
- **TITRE JOURNALISTIQUE** (H1) : Verbe d'action + info clé.
- **DATELINE** : "*Synthèse actualisée au [Date du jour]*"
- **CHAPÔ** : L'essentiel en 3 lignes.
- **LE CŒUR DE L'ACTU** (H2) : Faits récents et importants [1][2].
- **ANALYSE & CONTEXTE** (H2) : Pourquoi c'est important.
- **CE QU'IL FAUT SURVEILLER** (H2) : Prochaines étapes/dates.

SECTION SOURCES FINALE :
À la fin, ajoute "### Sources" avec les titres exacts des vidéos.

STYLE :
- Dynamique, "Breaking News".
- **Gras** pour les infos cruciales.
- Utiliser > Citation pour les déclarations importantes.
- Si sources contradictoires : la plus RÉCENTE a raison (mais mentionner le changement).
- N'INVENTE AUCUNE source journalistique ou agence de presse.

{ANTI_HALLUCINATION}
"""


class MeetingPromptTemplate(PromptTemplate):
    """Template pour les comptes-rendus de réunion - Exhaustif avec tableau d'actions."""
    
    def get_chunk_prompt(self, text: str) -> str:
        return f"""Tu es Secrétaire de Séance Expert.

Texte à traiter (segment de réunion) :
{text}

RÈGLES ANTI-HALLUCINATION :
1. **FIDÉLITÉ ABSOLUE** : N'ajoute RIEN qui n'est pas dans le texte.
2. **PAS DE RÉDACTION** : Fais des listes factuelles.
3. **CITATIONS** : Garde les phrases clés entre guillemets.

OBJECTIFS D'EXTRACTION :
1. **Décisions actées** : Ce qui a été validé.
2. **Points de blocage** : Désaccords ou problèmes soulevés.
3. **Actions futures** : Qui ? Quoi ? Pour quand ?
4. **Déroulé chronologique** : Sujets dans l'ordre.

FORMAT : Liste à puces factuelle.

{ANTI_HALLUCINATION}
"""

    def get_full_text_prompt(self, text: str) -> str:
        return f"""Tu es le Secrétaire Général rédigeant un COMPTE-RENDU officiel.

Texte à traiter :
{text}

STRUCTURE IMPÉRATIVE (UNIQUEMENT CES PARTIES) :

## Déroulé de la Séance
- Retrace chronologiquement les échanges.
- Sous-titres (H3) pour séparer les sujets.
- Précision sur les échanges (arguments, points de vue).

## Relevé de Décisions et Actions

### Décisions Actées
(Liste des décisions validées)

### Tableau des Actions
| Action | Responsable | Échéance | Priorité |
|--------|-------------|----------|----------|
| ... | ... | ... | Haute/Moyenne/Basse |

*Si l'échéance n'est pas mentionnée, indiquer "À définir".*

### Points en Suspens
(Ce qui reste à trancher)

CONTRAINTES :
- **PAS D'INTRODUCTION, PAS DE CONCLUSION, PAS DE RÉSUMÉ EXÉCUTIF.**
- Exhaustivité : Rapporte les faits, ne les compresse pas.
- Style : Factuel, précis, sans fioritures.

{ANTI_HALLUCINATION}
"""

    def get_multi_prompt(self, search: str, content: str) -> str:
        return f"""Tu rédiges le COMPTE-RENDU FINAL consolidé.

Titre de la réunion : {search}
Segments consolidés : {content}

{CITATION_INSTRUCTIONS}

STRUCTURE IMPÉRATIVE :

## Déroulé de la Séance
- Fusionne les notes pour reconstituer le fil de la réunion.
- Sous-titres (H3) pour les thématiques.
- Conserve la richesse des débats avec sources [1], [2].

## Relevé de Décisions et Actions

### Décisions Actées
(Liste consolidée des décisions avec source [X])

### Tableau des Actions
| Action | Responsable | Échéance | Priorité | Source |
|--------|-------------|----------|----------|--------|
| ... | ... | ... | Haute/Moyenne/Basse | [X] |

### Points en Suspens
(Ce qui reste à trancher)

CONTRAINTES :
- Utilise le titre "{search}" comme contexte.
- **PAS D'AUTRE SECTION** : Déroulé + Actions uniquement.
- Ne perds aucune info technique.

{ANTI_HALLUCINATION}
"""


# =============================================================================
# REGISTRE DES PROMPTS (OCP - Open/Closed Principle)
# =============================================================================

class PromptManager:
    """
    Gestionnaire de prompts utilisant le pattern Registre.
    
    Pour ajouter un nouveau type de résumé :
    1. Créer une classe héritant de PromptTemplate
    2. L'enregistrer avec PromptManager.register("nom", MaClasse)
    
    Le code existant n'a pas besoin d'être modifié (OCP).
    """
    
    _registry: Dict[str, Type[PromptTemplate]] = {
        "short": ShortPromptTemplate,
        "medium": MediumPromptTemplate,
        "long": LongPromptTemplate,
        "news": NewsPromptTemplate,
        "meeting": MeetingPromptTemplate,
    }
    
    @classmethod
    def register(cls, name: str, template_class: Type[PromptTemplate]) -> None:
        """
        Enregistre un nouveau type de prompt.
        
        Args:
            name: Identifiant du type de résumé
            template_class: Classe héritant de PromptTemplate
        """
        cls._registry[name] = template_class
    
    @classmethod
    def get_available_types(cls) -> list:
        """Retourne la liste des types de résumés disponibles."""
        return list(cls._registry.keys())
    
    def get_prompt(
        self, 
        summary_type: str, 
        context: str, 
        text: Union[str, Dict[str, str]]
    ) -> str:
        """
        Récupère le prompt approprié selon le type et le contexte.
        
        Args:
            summary_type: Type de résumé (short, medium, long, news, meeting)
            context: Contexte du prompt (chunk, full_text, multi)
            text: Texte à traiter ou dict avec 'search' et 'content'
        
        Returns:
            Le prompt formaté
        """
        template_class = self._registry.get(summary_type, ShortPromptTemplate)
        template = template_class()
        
        if context == "chunk":
            return template.get_chunk_prompt(str(text))
        elif context == "full_text":
            return template.get_full_text_prompt(str(text))
        elif context == "multi":
            if isinstance(text, dict):
                return template.get_multi_prompt(text.get("search", ""), text.get("content", ""))
            return template.get_multi_prompt("", str(text))
        
        # Fallback
        return template.get_chunk_prompt(str(text))
