# Qu'est-ce qu'une bonne soudure ?

## Targets

- **Prédites :** `yield_strength_MPa`, `uts_MPa`, `elongation_pct`, `charpy_toughness_J`. Ce sont les quatre propriétés vérifiées par les normes de soudage.
- **Non prédite :** `reduction_area_pct` ne figure pas dans les normes et répète surtout l'allongement et le Charpy.
- **`charpy_temp_C` est une entrée.** C'est la température à laquelle l'essai Charpy a été fait, choisie par le laboratoire, pas un résultat.

## Définition

Une bonne soudure respecte tous les seuils de la norme de sa famille d'alliage. Les normes utilisées sont celles qui classent les produits d'apport, car elles testent le même type d'éprouvette que la base (métal fondu pur, « all weld metal deposits »).

La famille se calcule à partir de la composition :

| Famille | Règle | Norme |
|---|---|---|
| CrMo2 | 1,9 ≤ Cr ≤ 2,7 et 0,85 ≤ Mo ≤ 1,35 | EN ISO 3580-A, nuance CrMo2 |
| CrMo91 | 8 ≤ Cr ≤ 10,5 et V ≥ 0,15 | EN ISO 3580-A, nuance CrMo91 |
| CrMo9 | 8 ≤ Cr ≤ 10,5 et V < 0,15 | EN ISO 3580-A, nuance CrMo9 |
| C-Mn | toutes les autres soudures | EN ISO 2560-A, classe 42 4 |

Seuils :

| | C-Mn | CrMo2 | CrMo91 | CrMo9 |
|---|---|---|---|---|
| Limite d'élasticité (MPa) | ≥ 420 | ≥ 400 | ≥ 415 | ≥ 435 |
| UTS (MPa) | 500 à 640 | ≥ 500 | ≥ 585 | ≥ 590 |
| Allongement (%) | ≥ 20 | ≥ 18 | ≥ 17 | ≥ 18 |
| Charpy | ≥ 47 J à −40 °C | ≥ 47 J à +20 °C | ≥ 47 J à +20 °C | ≥ 34 J à +20 °C |

- **Pourquoi par famille :** Les soudures Cr-Mo sont faites pour être plus résistantes. Jugées avec les seuils C-Mn, la plupart dépassent le maximum d'UTS de 640 MPa, et le modèle apprendrait « Cr-Mo = mauvaise soudure ».
- **Pourquoi le procédé ne compte pas :** Pour les aciers C-Mn, les normes de chaque procédé (MMA, arc submergé, fil fourré) utilisent les mêmes tableaux de seuils. Le procédé reste une entrée des modèles.
- **Pourquoi un maximum d'UTS en C-Mn :** Une soudure trop résistante perd en ductilité et en ténacité. Une bonne soudure est donc un compromis, pas le maximum de chaque propriété.
- **La classe 42 4 est un choix :** « 42 » est proche de la limite d'élasticité médiane de la base, et « 4 » (−40 °C) est un niveau de ténacité exigeant. Une autre classe change seulement les seuils, pas les modèles.

## La colonne Charpy

Dans beaucoup de lignes, l'énergie vaut exactement 28 J ou 100 J : les papiers fixent l'énergie et mesurent la température à laquelle la soudure l'atteint. Chaque ligne est donc traitée comme un point de la courbe énergie-température, avec la température en entrée et l'énergie en sortie.

L'énergie augmente avec la température, donc une ligne mesurée ne peut être jugée que dans certains cas :

- **Conforme :** testée à la température de référence ou en dessous, et au-dessus de l'énergie minimum.
- **Non conforme :** testée à la température de référence ou au-dessus, et en dessous de l'énergie minimum.
- **Indécidable :** tous les autres cas.

Le modèle prédit directement l'énergie à la température de référence de la famille.

## Stratégie

1. Une régression par target, entraînée sur les lignes où cette target est connue.
2. Les seuils de la famille de la soudure sont appliqués aux quatre prédictions. Une soudure est bonne si elle les passe tous, et on sait quel critère échoue.
3. Évaluation : MAE et RMSE par target, puis F1 et rappel sur les soudures non conformes, au global et par famille.
4. Semi-supervisé : les lignes où une target manque servent de données non étiquetées pour cette target, et le résultat est comparé à la version supervisée.

## Sources

- [Seuils C-Mn (EN ISO 2560-A)](https://elgawelding.com/wp-content/uploads/2021/07/ELGA-Classification_EN-ISO-2560-A-1.pdf)
- [Seuils Cr-Mo (ISO 3580, Table 2)](https://cdn.standards.iteh.ai/samples/51630/51a896dcccf74be7b354c5f12d8fd32c/ISO-3580-2010.pdf)
