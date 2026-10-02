# Définition de la target : qu'est-ce qu'une bonne soudure ?

## En bref

- **Targets (4 colonnes)** : `yield_strength_MPa`, `uts_MPa`, `elongation_pct`, `charpy_toughness_J`.
- **`charpy_temp_C` est une entrée**, pas une target : c'est la température de l'essai Charpy.
- **Bonne soudure** = soudure conforme à la norme de **sa famille d'alliage** :
  - aciers C-Mn (non alliés et à grains fins) : classe **42 4** du système A (EN ISO 2560-A pour le MMA, mêmes seuils pour les autres procédés) ;
  - aciers Cr-Mo résistant au fluage : nuance **CrMo2** ou **CrMo91** de **EN ISO 3580-A** (et de son équivalent arc submergé, EN ISO 24598-A).
- **Les seuils dépendent de l'alliage, pas du procédé.** Pour les aciers C-Mn, toutes les normes du système A ont exactement les mêmes seuils, quel que soit le procédé.
- **Stratégie** : une régression par target, puis on applique aux prédictions les seuils de la famille de la soudure pour dire si elle est bonne.

Les chiffres ci-dessous sont calculés sur `data/train.csv` (1229 lignes).

---

## 1. Colonnes retenues

| Colonne | Rôle | Lignes dispo (train) | Pourquoi |
|---|---|---|---|
| `yield_strength_MPa` | target | 612 | critère de résistance de la norme (symbole « 42 ») |
| `uts_MPa` | target | 591 | critère de résistance de la norme |
| `elongation_pct` | target | 549 | critère de ductilité de la norme |
| `charpy_toughness_J` | target | 704 | critère de ténacité de la norme (symbole « 4 ») |
| `charpy_temp_C` | **entrée** | 704 | condition de l'essai Charpy, pas un résultat |
| `reduction_area_pct` | non retenue | 552 | pas dans la norme, redondante avec `elongation_pct` et Charpy (corr. 0,54 et 0,83) |
| `hardness_kg_mm2`, `fatt50_C` | non retenues | < 140 | déjà supprimées (plus de 1000 valeurs manquantes) |

**Aucune propriété mesurée ne sert d'entrée pour en prédire une autre.** Par exemple, `uts_MPa` est corrélée à 0,92 avec `yield_strength_MPa` : l'utiliser comme entrée serait du leakage, car on ne la connaît pas avant d'avoir soudé.

---

## 2. Qu'est-ce qu'une bonne soudure ?

### Pourquoi les normes de produits d'apport

- **Même type d'essais que la base.** La base contient des « all weld metal deposits » ([MAP_DATA_WELD](https://www.phase-trans.msm.cam.ac.uk/map/data/materials/welddb-b.html)), c'est-à-dire du métal fondu pur. C'est sur ce type d'éprouvette que les normes de produits d'apport classent les électrodes et les fils.
- **Les critères de la norme sont nos colonnes.** Ces normes fixent des minimums de limite d'élasticité, UTS, allongement et Charpy. Le système A utilise la limite d'élasticité et 47 J ([TWI](https://www.twi-global.com/technical-knowledge/job-knowledge/welding-consumables-part-3-084)).

### Les seuils dépendent-ils du procédé ?

**Non, pour les aciers C-Mn.** Chaque procédé a sa propre norme, mais elles partagent le même tableau de traction (« Table 1A ») et le même tableau Charpy :

| Procédé (base) | Norme (système A) | Désignation | Seuils pour « 42 4 » |
|---|---|---|---|
| MMA | EN ISO 2560-A | E 42 4 | identiques |
| arc submergé (SA, TSA) | EN ISO 14171-A | S 42 4 | identiques |
| fil fourré (FCA) | EN ISO 17632-A | T 42 4 | identiques |
| fil plein sous gaz (GMAA) | EN ISO 14341-A | G 42 4 | même logique |
| TIG (GTAA) | EN ISO 636-A | W 42 4 | même logique |

On a vérifié les tableaux de [ISO 14171:2016](https://cdn.standards.iteh.ai/samples/68753/1cbe8001a5db48139641e3386ad6e99e/ISO-14171-2016.pdf) (Table 1A et Table 3) et de [EN ISO 17632:2015](https://uscc.ua/uploads/page/images/normativnye%20dokumenty/dstu/vigotovlennya-mk-mizhnarodna-gilka-standarty/51-dstu-en-iso-17632-2015-mater-ali-zvaryuvaln.pdf) (Table 1A) : ils donnent exactement les mêmes valeurs que EN ISO 2560-A. Découper l'étude par procédé ne changerait donc pas les seuils. Le procédé reste une **variable d'entrée** des modèles.

**Oui, selon l'alliage.** Les aciers Cr-Mo résistant au fluage ont leurs propres normes (EN ISO 3580 en MMA, EN ISO 24598 en arc submergé, EN ISO 17634 en fil fourré, EN ISO 21952 sous gaz), avec des seuils différents. Ces soudures représentent 16 % du train (192 lignes), surtout en FCA (70), SA (55) et MMA (47).

### Familles d'alliage dans la base

La famille se déduit de la composition (des entrées connues avant le soudage, donc sans leakage). Les plages viennent du Table 1 de [ISO 3580:2017](https://cdn.standards.iteh.ai/samples/68752/36b85dee9196457d93316dcde7d4c8ba/ISO-3580-2017.pdf), élargies d'environ 0,1 % pour tolérer l'incertitude de mesure.

| Famille | Règle sur la composition | Lignes (train) | Dépôts (`weld_group`) | Remarque |
|---|---|---|---|---|
| C-Mn | tout le reste | 1037 | 420 | MMA à 78 % |
| CrMo2 (2,25Cr-1Mo) | 1,9 ≤ Cr ≤ 2,7 et 0,85 ≤ Mo ≤ 1,35 | 135 | 32 | PWHT à 690 °C pour presque toutes les lignes |
| CrMo91 (9Cr-1Mo modifié) | 8 ≤ Cr ≤ 10,5 et V ≥ 0,15 | 56 | 30 | contient V (≈ 0,2 %) et Nb, PWHT à 746-760 °C |
| CrMo9 (9Cr-1Mo) | 8 ≤ Cr ≤ 10,5 et V < 0,15 | 1 | 1 | négligeable |

Les PWHT de la base correspondent à ceux exigés par la norme (690-750 °C pour CrMo2, 745-775 °C pour CrMo91), ce qui confirme qu'il s'agit bien de produits d'apport Cr-Mo.

Les autres lignes alliées (Cr seul jusqu'à 2,4 %, Mo seul autour de 0,5 %, Ni jusqu'à 3,5 %) sont surtout des séries expérimentales d'Evans : on ajoute un élément à une base C-Mn et on teste à l'état brut de soudage. Elles restent dans la famille C-Mn.

### Seuils retenus par famille

**Aciers C-Mn : classe 42 4.** Source : [guide ELGA EN ISO 2560-A](https://elgawelding.com/wp-content/uploads/2021/07/ELGA-Classification_EN-ISO-2560-A-1.pdf), norme officielle [EN ISO 2560:2020 (BSI)](https://knowledge.bsigroup.com/products/welding-consumables-covered-electrodes-for-manual-metal-arc-welding-of-non-alloy-and-fine-grain-steels-classification-3).

**Aciers Cr-Mo : nuance de EN ISO 3580-A.** Pas de symbole de résistance à choisir : chaque nuance a ses propres minimums, mesurés après PWHT. Source : Table 2 de [ISO 3580:2010](https://cdn.standards.iteh.ai/samples/51630/51a896dcccf74be7b354c5f12d8fd32c/ISO-3580-2010.pdf), mêmes valeurs dans le Table 1A de [ISO 24598:2007](https://cdn.standards.iteh.ai/samples/42326/0da54846076f47879296ee0dc7554ab3/ISO-24598-2007.pdf) (arc submergé).

| Critère | C-Mn (42 4) | CrMo2 | CrMo91 | CrMo9 |
|---|---|---|---|---|
| `yield_strength_MPa` | ≥ 420 | ≥ 400 | ≥ 415 | ≥ 435 |
| `uts_MPa` | 500 à 640 | ≥ 500 | ≥ 585 | ≥ 590 |
| `elongation_pct` | ≥ 20 | ≥ 18 | ≥ 17 | ≥ 18 |
| `charpy_toughness_J` | ≥ 47 J à −40 °C | ≥ 47 J à +20 °C | ≥ 47 J à +20 °C | ≥ 34 J à +20 °C |
| État testé | brut de soudage | après PWHT | après PWHT | après PWHT |

**Part des lignes conformes (train) :**

| Critère | C-Mn | CrMo2 | CrMo91 |
|---|---|---|---|
| `yield_strength_MPa` | 82 % (n = 550) | 93 % (n = 29) | 100 % (n = 32) |
| `uts_MPa` | 65 % (n = 533 ; 14 % en dessous, 21 % au-dessus) | 100 % (n = 33) | 100 % (n = 25) |
| `elongation_pct` | 92 % (n = 490) | 76 % (n = 34) | 80 % (n = 25) |
| les 3 critères de traction | 57 % (n = 480) | 70 % (n = 27) | 80 % (n = 25) |

**Une bonne soudure respecte tous les critères de sa famille à la fois.**

**Pourquoi ne pas garder 42 4 pour tout le monde.** Avec les seuils C-Mn, seules 19 % des soudures Cr-Mo passent les trois critères de traction (n = 52), et 76 % dépassent l'UTS maximum de 640 MPa. Ce n'est pas un défaut : une soudure Cr-Mo est faite pour être plus résistante et pour travailler à chaud. Le modèle apprendrait alors « Cr-Mo = mauvaise soudure », ce qui est faux et inutilisable pour les recommandations.

**Pourquoi un maximum sur l'UTS en C-Mn.** Une soudure trop résistante perd en ductilité et en ténacité : dans la base, la corrélation entre UTS et allongement est de −0,74, et entre UTS et Charpy de −0,70. On ne peut donc pas définir la qualité comme « maximiser toutes les propriétés » : on cherche un compromis dans une plage. Les normes Cr-Mo, elles, ne fixent qu'un minimum.

**Choix de la classe C-Mn (à valider ensemble).**
- « 42 » correspond à la limite d'élasticité médiane de la base (494 MPa).
- « 4 » (−40 °C) est un choix exigeant, cohérent avec des structures exposées au froid comme l'éolien cité dans le sujet.
- Changer de classe revient à changer les seuils, sans réentraîner les modèles.

Pour les Cr-Mo, il n'y a pas de choix à faire : la nuance est fixée par la composition.

### Le piège de la colonne Charpy

Sur 704 lignes Charpy du train, **379 ont une énergie de exactement 100 J ou 28 J**. Dans les papiers Evans, on fixe l'énergie et on mesure **la température à laquelle la soudure atteint 28 J ou 100 J** (T28J, T100J), comme le décrit [Sampath, 2024](https://crimsonpublishers.com/amms/fulltext/AMMS.000795.php).

On traite donc chaque ligne comme un point (T, E) de la courbe de transition ductile-fragile : **T en entrée, E en sortie**. C'est aussi ce que fait [Bhadeshia, MacKay & Svensson, 1995](https://www.phase-trans.msm.cam.ac.uk/abstracts/toughness.pdf) sur ce type de données (température en entrée, énergie Charpy en sortie).

Pour dire si une ligne mesurée respecte le critère « ≥ E_min à T_ref » (T_ref = −40 °C en C-Mn, +20 °C en Cr-Mo ; l'énergie augmente avec la température) :
- si T ≤ T_ref et E ≥ E_min : **conforme** ;
- si T ≥ T_ref et E < E_min : **non conforme** ;
- sinon : **on ne peut pas conclure**.

| Famille | Conforme | Non conforme | Indécidable |
|---|---|---|---|
| C-Mn (−40 °C) | 231 | 26 | 328 |
| CrMo2 (+20 °C) | 30 | 0 | 65 |
| CrMo91 (+20 °C) | 5 | 4 | 15 |

Le modèle, lui, prédit directement E à T = T_ref de la famille. Comme T est une entrée, cela ne demande aucun réentraînement.

---

## 3. Stratégie

1. **Quatre régressions supervisées**, une par target, sur toutes les familles à la fois. Chaque modèle est entraîné sur toutes les lignes où sa target existe.
   - Entrées : composition, paramètres de soudage, procédé, PWHT, et `charpy_temp_C` pour le modèle Charpy.
   - Ce découpage évite de ne garder que les lignes complètes (très peu nombreuses).
   - On n'entraîne pas un modèle par famille : les Cr-Mo n'ont que 25 à 35 lignes par target de traction.
2. **Règle de conformité** appliquée aux quatre prédictions avec les seuils de la famille de la ligne (colonne `famille` calculée à partir de Cr, Mo et V). Le résultat est explicable : on sait quel critère fait échouer une soudure.
3. **Évaluation.**
   - Chaque régression : MAE et RMSE en `StratifiedGroupKFold` sur `weld_group`, stratifié par famille. Les lignes d'un même dépôt ne sont jamais à la fois en train et en validation, et chaque fold contient des soudures Cr-Mo.
   - Le label « bonne soudure » : F1 et rappel sur les non-conformes, mesurés sur les dépôts où le label réel est connu. Dans le train, 245 dépôts ont traction et Charpy, dont 172 avec un critère Charpy décidable (16 d'entre eux sont Cr-Mo).
   - On donne les métriques **globales et par famille** : un bon score global peut cacher un modèle mauvais sur les Cr-Mo, qui sont peu nombreux.
   - Le classifieur direct (personne D) doit recevoir la famille en entrée, puisque la définition du label en dépend.
4. **Semi-supervisé (demandé par le sujet).** La plupart des lignes n'ont qu'une partie des targets. On peut faire du self-training : pseudo-labelliser les targets manquantes avec les prédictions les plus sûres, puis réentraîner. On compare avec la version supervisée seule.

### Ce que change le choix de seuils par famille

- **Pour les modèles de régression : rien.** Les targets restent les mêmes, seule la règle appliquée après change.
- **Le label devient plus juste** pour 16 % des lignes (les Cr-Mo ne sont plus déclarées mauvaises à cause de leur composition).
- **Le label n'a pas le même sens partout** : « bonne » veut dire « conforme à la norme de sa famille ». Il faut l'écrire dans le rapport.
- **Les métriques Cr-Mo sont fragiles** : dans le train, seuls 17 dépôts Cr-Mo ont traction et Charpy, dont 16 avec un critère Charpy décidable. On les donne à titre indicatif, avec leur effectif.
- **Les recommandations métier se font par famille** (par exemple : quelle plage de Mn ou de PWHT pour un dépôt C-Mn conforme, quel allongement viser pour un dépôt CrMo2).

### Limites à mentionner dans le rapport

- **Les normes Cr-Mo exigent un état après PWHT.** Une ligne Cr-Mo sans PWHT (1 ligne dans le train) n'est pas dans les conditions de la norme : on la signale ou on l'exclut du calcul du label.
- **Les séries Evans à un seul élément d'alliage** (Cr seul, Mo seul) sont jugées avec les seuils C-Mn. C'est un choix : elles ne correspondent à aucune nuance Cr-Mo de la norme.
- **La qualité se limite ici aux propriétés mécaniques.** Les défauts (porosités, fissures) ne sont pas dans la base.

---

## Sources

- Base de données : [MAP_DATA_WELD, University of Cambridge](https://www.phase-trans.msm.cam.ac.uk/map/data/materials/welddb-b.html)
- Seuils EN ISO 2560-A (MMA, C-Mn) : [guide ELGA](https://elgawelding.com/wp-content/uploads/2021/07/ELGA-Classification_EN-ISO-2560-A-1.pdf), [norme BSI](https://knowledge.bsigroup.com/products/welding-consumables-covered-electrodes-for-manual-metal-arc-welding-of-non-alloy-and-fine-grain-steels-classification-3)
- Seuils EN ISO 14171-A (arc submergé, C-Mn) : [ISO 14171:2016, extrait iTeh, Tables 1A et 3](https://cdn.standards.iteh.ai/samples/68753/1cbe8001a5db48139641e3386ad6e99e/ISO-14171-2016.pdf)
- Seuils EN ISO 17632-A (fil fourré, C-Mn) : [EN ISO 17632:2015, Table 1A](https://uscc.ua/uploads/page/images/normativnye%20dokumenty/dstu/vigotovlennya-mk-mizhnarodna-gilka-standarty/51-dstu-en-iso-17632-2015-mater-ali-zvaryuvaln.pdf)
- Seuils EN ISO 3580-A (MMA, Cr-Mo) : [ISO 3580:2010, extrait iTeh, Table 2](https://cdn.standards.iteh.ai/samples/51630/51a896dcccf74be7b354c5f12d8fd32c/ISO-3580-2010.pdf) ; compositions des nuances : [ISO 3580:2017, extrait iTeh, Table 1](https://cdn.standards.iteh.ai/samples/68752/36b85dee9196457d93316dcde7d4c8ba/ISO-3580-2017.pdf)
- Seuils EN ISO 24598-A (arc submergé, Cr-Mo) : [ISO 24598:2007, extrait iTeh, Table 1A](https://cdn.standards.iteh.ai/samples/42326/0da54846076f47879296ee0dc7554ab3/ISO-24598-2007.pdf)
- Systèmes A et B des normes : [TWI, Welding Consumables Part 3](https://www.twi-global.com/technical-knowledge/job-knowledge/welding-consumables-part-3-084)
- Charpy (T, E) : [Bhadeshia, MacKay & Svensson, *Materials Science and Technology* 11 (1995) 1046–1051](https://www.phase-trans.msm.cam.ac.uk/abstracts/toughness.pdf)
- T28J / T100J dans les données Evans : [Sampath, « Selective Analysis of a High-Strength Steel Shielded Metal Arc Weld Metal Database », Crimson Publishers, 2024](https://crimsonpublishers.com/amms/fulltext/AMMS.000795.php)
- Modèles de référence sur cette base : [Cool, Bhadeshia & MacKay, *Materials Science and Engineering A* 223 (1997)](https://www.sciencedirect.com/science/article/abs/pii/S092150939610513X)
