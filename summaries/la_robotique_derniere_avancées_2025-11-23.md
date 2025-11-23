# Résumé des avancées en robotique intelligente – **Progrès**

## Points essentiels
- **Rapidité d'initiation** : la plupart des robots peuvent être maîtrisés en moins d’une heure, souvent via des tutoriels vidéo et une interface simple.
- **Temps de fonctionnement** : la durée d’usage varie de 1 à 4 h en fonction du modèle (batterie Li‑Po, Li‑Fe, Li‑S, etc.).
- **Capacités de perception** : combinaison vision‑tactile‑auditive dans la majorité des humanoïdes, avec un nombre de capteurs tactile allant de 20 à 2 000.
- **Applications ciblées** : industrie (assemblage, soudure, inspection), sécurité (pompiers, anti‑déflagrantes), commerce (kiosques autonomes), services domestiques (nettoyage, assistance aux aînés).
- **Approche pédagogique** : utilisation de l’apprentissage par imitation ou de l’IA pour copier des gestes humains, réduisant les temps de formation.
- **Diffusion mondiale** : plusieurs startups chinoises, notamment Galaxy, ZeroTech, et Tura‑Wann, cherchent à se produire en masse d’ici 2025.

---

## 1. Robots industriels – Progrès

| Modèle | Taille / Poids | Points forts | Applications |
|--------|----------------|--------------|--------------|
| **G1** | 1 m × 1 m, 60 kg | 70 degrés de liberté, IA prédictive | Assemblage, soudure, contrôle qualité |
| **GR1** | 1,70 m, 120 kg | Vision, audition, toucher | Inspection, contrôle de qualité, réparation |
| **GR1** (second) | 1,70 m, 120 kg | IA générative | Fabrication de pièces complexes |
| **GR3** | 1,65 m, 71 kg | Vision, audition, 55 degrés de liberté | Maintenance, retouches en usine |
| **Sparky** | 2 m, 50 kg | Vision, audition, 40 degrés de liberté | Assistance de fabrication |
| **Sparky** (second) | 1,8 m, 120 kg | 40 degrés de liberté | Surveillance de sites industriels |

### Points communs
- Utilisation du **Lidar**, du **caméras**, et de **capteurs tactile**.
- Mise en œuvre d’algorithmes **SLAM** et **navigation autonome**.
- Intégration de grands modèles de langage (LLM) pour l’interaction.

### Divergences
- Certains modèles (GR1, GR3) se concentrent sur la **recyclabilité** et l’**éco‑efficacité**, tandis que d’autres (Sparky) mettent l’accent sur la **performance en environnement hostile**.

---

## 2. Robots domestiques – Progrès

| Modèle | Charge utile | Fonctionnalités clés | Temps d’utilisation |
|--------|--------------|----------------------|----------------------|
| **ZeroTech H1** | 200 kg | Nettoyage complet, autonomisation | 3 h |
| **ZeroTech H1** (second) | 200 kg | Nettoyage + re‑approvisionnement | 3 h |
| **ZeroTech H2** | 200 kg | Nettoyage et transport | 3 h |
| **ZeroTech H3** | 200 kg | Nettoyage de zones restreintes | 3 h |

### Points communs
- Tous utilisent **IA** pour la reconnaissance d’objets et la planification de tâches.
- Equipés de **roues omnidirectionnelles** ou de **pieds multi‑déformants** pour l’adaptation aux environnements domestiques.

### Divergences
- La **ZeroTech H1** se concentre sur le **nettoyage**, tandis que la **H2/H3** élargissent à la **logistique interne**.
- Certains modèles sont conçus pour les **centres de rééducation**, d’autres pour la **retour à domicile**.

---

## 3. Robots d’assistance à domicile – Progrès

| Modèle | Taille / Poids | Système de perception | Applications |
|--------|----------------|-----------------------|--------------|
| **Galaxy Generale Robotics G1** | 1 m | Vision, audition, toucher | Réapprovisionnement, service client |
| **Galaxy Generale Robotics G1** (second) | 1 m | Vision, audition, toucher | Distribution de médicaments |
| **Galaxy Generale Robotics G2** | 1 m | Vision, audition, toucher | Réapprovisionnement, assistance |
| **Galaxy Generale Robotics G3** | 1,5 m | Vision, audition, toucher | Réapprovisionnement, assistance |
| **Galaxy Generale Robotics G4** | 1,5 m | Vision, audition, toucher | Réapprovisionnement, assistance |

### Points communs
- Intégration de la **navigation autonome** (SLAM).
- Usage de **capteurs tactile** (20 à 2000).
- Conception axée sur la **sécurité** et l’**ergonomie**.

### Divergences
- Le **G1** cible le **commerce de détail** et la **logistique**, tandis que le **G2** se concentre sur la **logistique interne**.
- Le **G4** introduit une **capacité de montée en escalier** qui n’est pas présente dans les modèles précédents.

---

## 4. Robots de sécurité et d’intervention – Progrès

| Modèle | Application | Points forts |
|--------|-------------|--------------|
| **ZeroTech H2** | Nettoyage de zones restreintes | IA générative, Lidar |
| **ZeroTech H3** | Nettoyage de zones restreintes | IA générative, Lidar |
| **ZeroTech H2** (second) | Inspection de zones restreintes | Lidar, caméra |
| **ZeroTech H3** (second) | Inspection de zones restreintes | Lidar, caméra |
| **ZeroTech H4** | Inspection de zones restreintes | Lidar, caméra, IA |
| **ZeroTech H5** | Inspection de zones restreintes | Lidar, caméra, IA |

### Points communs
- Tous intègrent **capteurs Lidar** pour la détection d’obstacles.
- Application dans des environnements **hostiles** (incendie, explosion, inspection post‑accident).

### Divergences
- Certains modèles se concentrent sur le **nettoyage**, d’autres sur la **logistique interne**.
- La **ZeroTech H5** intègre une **IA prédictive** supplémentaire, offrant une meilleure prise de décision en temps réel.

---

## 5. Robots d’assistance à l’aéronautique et à la santé – Progrès

| Modèle | Taille / Poids | Capacité |
|--------|----------------|----------|
| **ZeroTech H1** | 200 kg | Nettoyage complet |
| **ZeroTech H2** | 200 kg | Nettoyage + re‑approvisionnement |
| **ZeroTech H3** | 200 kg | Nettoyage de zones restreintes |

### Points communs
- Mise en œuvre d’une **IA générative** pour l’apprentissage rapide.
- Charge utile jusqu’à **200 kg** pour les tâches de **nettoyage** et de **logistique**.

### Divergences
- La **ZeroTech H1** se concentre sur le **nettoyage** des surfaces intérieures.
- Les modèles **H2** et **H3** étendent la capacité de **transport** et de **logistique**.

---

## 5. Perspectives d’avenir – Progrès

| Secteur | Tendances | Entreprises en tête |
|---------|-----------|---------------------|
| Industrie | IA générative, apprentissage par imitation | Galaxy, ZeroTech, Tura‑Wann |
| Domestique | Réapprovisionnement, service à la personne | Galaxy, ZeroTech, Tura‑Wann |
| Assistance à domicile | Logistique interne, service client | Galaxy Generale Robotics, ZeroTech |
| Sécurité | Nettoyage autonome, intervention | ZeroTech, Galaxy |

---

## Conclusion

Les roboticiens décrits par *Progrès* soulignent une convergence autour de l’intégration de **capteurs multi‑modalité** (vision, audition, toucher) et de **batteries avancées** (Li‑Fe, Li‑S, Li‑Po) afin de garantir des **temps de fonctionnement élevés** et une **autonomie suffisante**. Que ce soit pour la **fabrication**, la **logistique**, la **sécurité** ou le **service domestique**, ces technologies se rapprochent de solutions « plug‑and‑play » grâce à l’apprentissage par imitation et à l’intelligence artificielle, ouvrant la voie à une robotique **intelligente** et **efficace** d’ici 2025.