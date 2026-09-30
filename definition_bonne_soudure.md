# Définition de la target : qu'est-ce qu'une bonne soudure ?

## En bref

- **Targets (4 colonnes)** : `yield_strength_MPa`, `uts_MPa`, `elongation_pct`, `charpy_toughness_J`.
- **`charpy_temp_C` est une entrée**, pas une target : c'est la température de l'essai Charpy.
- **Bonne soudure** = soudure conforme à la classe **E 42 4** de la norme **EN ISO 2560-A**.
- **Stratégie** : une régression par target, puis on applique les seuils de la norme aux prédictions pour dire si la soudure est bonne.

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

### Pourquoi la norme EN ISO 2560-A

- **Même type d'essais que la base.** La base contient des « all weld metal deposits » ([MAP_DATA_WELD](https://www.phase-trans.msm.cam.ac.uk/map/data/materials/welddb-b.html)), c'est-à-dire du métal fondu pur. C'est sur ce type d'éprouvette que les normes de produits d'apport classent les électrodes.
- **Les critères de la norme sont nos colonnes.** EN ISO 2560 (électrodes enrobées, procédé MMA) fixe des minimums de limite d'élasticité, UTS, allongement et Charpy. Le système A utilise la limite d'élasticité et 47 J ([TWI](https://www.twi-global.com/technical-knowledge/job-knowledge/welding-consumables-part-3-084)).
- **C'est le procédé majoritaire de la base.** MMA représente environ 72 % des lignes.

### Seuils retenus : classe E 42 4

Source des valeurs : [guide ELGA EN ISO 2560-A](https://elgawelding.com/wp-content/uploads/2021/07/ELGA-Classification_EN-ISO-2560-A-1.pdf). Norme officielle : [EN ISO 2560:2020 (BSI)](https://knowledge.bsigroup.com/products/welding-consumables-covered-electrodes-for-manual-metal-arc-welding-of-non-alloy-and-fine-grain-steels-classification-3).

| Critère | Seuil | Part des lignes conformes (train) |
|---|---|---|
| `yield_strength_MPa` | ≥ 420 MPa | 83 % |
| `uts_MPa` | entre 500 et 640 MPa | 61 % (13 % en dessous, 26 % au-dessus) |
| `elongation_pct` | ≥ 20 % | 89 % |
| `charpy_toughness_J` | ≥ 47 J à −40 °C | voir plus bas |

**Une bonne soudure respecte tous les critères à la fois.** Sur les dépôts du train qui ont les trois essais de traction, 57 % respectent les trois critères de traction. Les deux classes sont donc assez équilibrées.

**Pourquoi un maximum sur l'UTS.** Une soudure trop résistante perd en ductilité et en ténacité : dans la base, la corrélation entre UTS et allongement est de −0,74, et entre UTS et Charpy de −0,70. On ne peut donc pas définir la qualité comme « maximiser toutes les propriétés » : on cherche un compromis dans une plage.

**Choix de la classe (à valider ensemble).**
- « 42 » correspond à la limite d'élasticité médiane de la base (494 MPa).
- « 4 » (−40 °C) est un choix exigeant, cohérent avec des structures exposées au froid comme l'éolien cité dans le sujet.
- Changer de classe revient à changer les seuils, sans réentraîner les modèles.

### Le piège de la colonne Charpy

Sur 704 lignes Charpy du train, **379 ont une énergie de exactement 100 J ou 28 J**. Dans les papiers Evans, on fixe l'énergie et on mesure **la température à laquelle la soudure atteint 28 J ou 100 J** (T28J, T100J), comme le décrit [Sampath, 2024](https://crimsonpublishers.com/amms/fulltext/AMMS.000795.php).

On traite donc chaque ligne comme un point (T, E) de la courbe de transition ductile-fragile : **T en entrée, E en sortie**. C'est aussi ce que fait [Bhadeshia, MacKay & Svensson, 1995](https://www.phase-trans.msm.cam.ac.uk/abstracts/toughness.pdf) sur ce type de données (température en entrée, énergie Charpy en sortie).

Pour dire si une ligne mesurée respecte le critère « ≥ 47 J à −40 °C » (l'énergie augmente avec la température) :
- si T ≤ −40 °C et E ≥ 47 J : **conforme** (238 lignes) ;
- si T ≥ −40 °C et E < 47 J : **non conforme** (62 lignes) ;
- sinon : **on ne peut pas conclure** (404 lignes).

Le modèle, lui, prédit directement E à T = −40 °C.

---

## 3. Stratégie

1. **Quatre régressions supervisées**, une par target. Chaque modèle est entraîné sur toutes les lignes où sa target existe.
   - Entrées : composition, paramètres de soudage, PWHT, et `charpy_temp_C` pour le modèle Charpy.
   - Ce découpage évite de ne garder que les lignes complètes (très peu nombreuses).
2. **Règle de conformité** appliquée aux quatre prédictions (la soudure est bonne si les quatre critères E 42 4 sont respectés). Le résultat est explicable : on sait quel critère fait échouer une soudure.
3. **Évaluation.**
   - Chaque régression : MAE et RMSE en `GroupKFold` sur `weld_group`, pour que les lignes d'un même dépôt ne soient jamais à la fois en train et en validation.
   - Le label « bonne soudure » : F1 et rappel sur les non-conformes, mesurés sur les dépôts où le label réel est connu. Dans le train, 245 dépôts ont traction et Charpy, dont 172 avec un critère Charpy décidable.
4. **Semi-supervisé (demandé par le sujet).** La plupart des lignes n'ont qu'une partie des targets. On peut faire du self-training : pseudo-labelliser les targets manquantes avec les prédictions les plus sûres, puis réentraîner. On compare avec la version supervisée seule.

### Limites à mentionner dans le rapport

- **La norme ne couvre que le MMA sur aciers non alliés.** Les autres procédés ont leur propre norme, avec la même logique de seuils :
  - arc submergé (SA/TSA) : EN ISO 14171 ;
  - fil fourré (FCA) : EN ISO 17632 ;
  - aciers Cr-Mo : EN ISO 3580.

  On applique les seuils E 42 4 partout en le signalant, ou on restreint l'étude aux aciers C-Mn.
- **La qualité se limite ici aux propriétés mécaniques.** Les défauts (porosités, fissures) ne sont pas dans la base.

---

## Sources

- Base de données : [MAP_DATA_WELD, University of Cambridge](https://www.phase-trans.msm.cam.ac.uk/map/data/materials/welddb-b.html)
- Seuils EN ISO 2560-A : [guide ELGA](https://elgawelding.com/wp-content/uploads/2021/07/ELGA-Classification_EN-ISO-2560-A-1.pdf), [norme BSI](https://knowledge.bsigroup.com/products/welding-consumables-covered-electrodes-for-manual-metal-arc-welding-of-non-alloy-and-fine-grain-steels-classification-3)
- Systèmes A et B de la norme : [TWI, Welding Consumables Part 3](https://www.twi-global.com/technical-knowledge/job-knowledge/welding-consumables-part-3-084)
- Charpy (T, E) : [Bhadeshia, MacKay & Svensson, *Materials Science and Technology* 11 (1995) 1046–1051](https://www.phase-trans.msm.cam.ac.uk/abstracts/toughness.pdf)
- T28J / T100J dans les données Evans : [Sampath, « Selective Analysis of a High-Strength Steel Shielded Metal Arc Weld Metal Database », Crimson Publishers, 2024](https://crimsonpublishers.com/amms/fulltext/AMMS.000795.php)
- Modèles de référence sur cette base : [Cool, Bhadeshia & MacKay, *Materials Science and Engineering A* 223 (1997)](https://www.sciencedirect.com/science/article/abs/pii/S092150939610513X)
