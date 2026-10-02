# Prédiction de la qualité de soudures

## Contexte

Le but de ce projet est de prédire la qualité de soudures sur des aciers. Il s’agit d’une problématique d’intérêt pour de nombreux industriels dont le secteur pèse plusieurs milliards d’euros (exemple : soudure de tubes/pipes d’éoliennes). 

De nos jours, la connaissance liée à la qualité des soudures se transmet principalement d’expert à expert soudeur, créant une forte dépendance des industriels. Il y a un enjeu majeur à acquérir de la connaissance via les données pour :
- Extraire et homogénéiser la connaissance experte.
- Explorer de nouvelles connaissances via des motifs (*patterns*) découverts lors de l'exploration de la donnée.

---

## Obtenir les données

Les données publiques pour réaliser ce projet sont accessibles via le lien suivant :  
[https://www.phase-trans.msm.cam.ac.uk/map/data/materials/welddb-b.html](https://www.phase-trans.msm.cam.ac.uk/map/data/materials/welddb-b.html)

Vous pouvez manipuler ces données grâce à la bibliothèque Python **Pandas**. Vous êtes invités à utiliser toutes les librairies abordées lors des séances de travaux pratiques pour faciliter les étapes de prétraitement (*pre-processing*).

---

## Objectifs du projet

- **Analyse descriptive et prétraitement :**
  - Réaliser une analyse exploratoire de la base de données pour la maîtriser et identifier les étapes de *pre-processing* pertinentes.
  - Toute action de prétraitement doit être explicitée, décrite et justifiée.
  - Réfléchir aux unités de mesure des variables, à la pertinence d'une normalisation, et appliquer une ACP (Analyse en Composantes Principales) pour développer une intuition sur les données.

- **Compréhension des variables cibles :**
  - Identifier les variables représentatives de la qualité d'une soudure et en analyser la signification.
  - Définir une stratégie pour prédire la qualité à partir de ces variables, en justifiant la méthodologie adoptée.

- **Modélisation Machine Learning :**
  - Appliquer différentes approches de ML étudiées en cours et TD.
  - Mettre en place un protocole de validation croisée rigoureux.
  - Le jeu de données n'étant pas totalement labellisé, réaliser un travail bibliographique sur les méthodes d'apprentissage semi-supervisé et en appliquer au moins une, en justifiant le choix.

- **Évaluation comparative :**
  - Effectuer une analyse comparative des performances entre les différents modèles et approches testés.
  - Justifier le choix des métriques d'évaluation utilisées.

- **Conclusions et recommandations métier :**
  - Conclure sur l’approche la plus appropriée pour prédire la qualité de soudure.
  - Formuler des recommandations concrètes pour garantir une bonne qualité de soudure d'après les résultats obtenus.

---

## Consignes relatives au rapport

- **Format :** Environ 5 pages, paginé.
- **Première page :** Noms des étudiants, numéro d'équipe, date, adresses email et titre du projet.
- **Structure attendue :**
  1. **Introduction & Problématique :** Rappel du contexte industriel et formalisation en problème/tâche d'apprentissage automatique (*Machine Learning*).
  2. **Description des données :** Présentation du jeu de données, résultats de l'analyse exploratoire et de l'ACP, identification et interprétation des variables cibles.
  3. **Méthodologie ML :** Présentation synthétique des modèles retenus et justification des choix méthodologiques (notamment pour les méthodes semi-supervisées).
  4. **Résultats expérimentaux :** Étude comparative des performances, accompagnée des formules/descriptions des métriques et de figures/tableaux pertinents.
  5. **Discussion, recommandations et gestion de projet :** Analyse critique des résultats, recommandations pratiques, et diagramme de Gantt détaillant la répartition des tâches, le temps alloué et les responsabilités de chaque membre.
  6. **Bibliographie :** Références bibliographiques rigoureuses et citées dans le corps du texte.
- **Figures et tableaux :** Chaque figure et tableau doit comporter un titre et faire l'objet d'un renvoi explicite dans le texte.