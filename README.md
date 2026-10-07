# Welding Model

## Data and Welding Process

The data come from MAP_DATA_WELD (University of Cambridge). The database collects all weld metal deposits from the literature.

The task is to predict the mechanical properties of a weld from three groups of inputs.

- **Composition:** C, Mn, Si, S, P, Ni, Cr, Mo, V, O, N, Al, Ti, Nb.
- **Welding parameters (set during welding):** current_A, voltage_V, heat_input_kJ_mm, weld_type, AC_DC, electrode_polarity, interpass_temp_C.
- **Post weld heat treatment (applied after welding):** pwht_temp_C, pwht_time_h.
- **Test condition:** charpy_temp_C.

The targets are the resulting mechanical properties:
- **Targets:** yield_strength_MPa, uts_MPa, elongation_pct, reduction_area_pct, charpy_toughness_J.

**Note on Charpy:** `charpy_toughness_J` depends on the test temperature, so `charpy_temp_C` is an input of the Charpy model. The model needs to learn this relation.

## Missingness Handling ([1_missingness_handling.ipynb](preprocessing/1_missingness_handling.ipynb))

We found missing data in four forms: `N` (not reported), `<x` (below detection limit), compound values (`67tot33res`) and ranges (`150-200`). We replaced `N` with NaN. We converted each numerical column to float and listed the values that failed.

| Subject | Rule |
|---|---|
| `<x` in wt% columns | Set to the column minimum (the mean was close to the limit). |
| `<x` in ppm columns | Set to half the limit (the limits are large, and the true value is between 0 and x). |
| N_ppm | Kept the total value (`67tot33res` became 67). |
| interpass_temp_C | Range became 175 (the middle value). |
| S, P | NaN became the median (few NaN, little variation). |
| O, N, Al | NaN became the median (each weld contains these elements). |
| Ni, Cr, Mo, V, Nb, Ti | NaN became 0 (added on purpose, so a paper that does not report them probably has none). |
| current_A, voltage_V | NaN became the median per weld type (the medians differ between weld types). |
| AC_DC, electrode_polarity | Polarity + set AC_DC to DC (+ exists only with DC). Other NaN became the mode. The flag `AC_DC_unknown` marked these rows. |
| Columns with more than 1000 NaN | Dropped (too little data to impute). |
| Sn, As, Sb, Co, W | Dropped (82% to 95% NaN, and NaN means "not measured"). |
| 13 rows without PWHT data | Dropped (less than 1% of the rows). |
| Targets, charpy_temp_C | Not imputed (an imputed value is a false label). |

## Units Handling ([2_units_handling.ipynb](preprocessing/2_units_handling.ipynb))

Essentially, we tried to plot a histogram of each numerical column, in order to spot outliers. This is why we plotted them on linear axis (same scale outliers) and log x-axis (different scale outliers). 
We then also compared each flagged value with the other welds of the same paper (using `weld_id`) to see whether the outliers were at least consistent within a paper (meaning it is probably not a wrong input from the author and that the value actually represents something (eg: different unit)).  

| Subject | Rule |
|---|---|
| Al_ppm, 10 EPRI-TR-101394s rows (0.004 to 0.014) | Multiplied by 10,000 (entered in wt%, not ppm). |
| Al_ppm, Ti_ppm, 16 PantK-1990 `bw` rows | Set to 50 (`<0.01` wt% is `<100` ppm, the same limit as the rest of the paper). |
| charpy_temp_C, charpy_toughness_J, Ditt-0.5rch2 | Set to NaN (188 does not fit the test temperatures of the paper, and the energy needs its temperature). |
| Mart-G (S, P), Wolst-1974-N (reduction_area_pct) | Unchanged (the data cannot show if the value is an error). |
| Other isolated values | Unchanged (they fit the trend of their own paper). |

## Train/Test Split ([3_train_test_split.ipynb](preprocessing/3_train_test_split.ipynb))

We split the data once, with 80% of the rows for training and 20% for testing. Rows with different `weld_id`s can have the same composition and welding parameters. In the database, each test is one row. For example, the row `Mart-A` has the tensile results (yield strength, UTS, elongation). The 11 rows `Mart-Aa` to `Mart-Ak` each have one Charpy test (`charpy_toughness_J`) at a different temperature (`charpy_temp_C`). These 12 rows have the same composition and welding parameters. They differ only by the test results and `charpy_temp_C`. We assume that rows with the same composition and welding parameters are essentially the same weld, and we kept them on the same side of the split. A split by `weld_id` would separate them.

We therefore grouped the rows by composition and welding parameters. We left out `charpy_temp_C` and the post weld heat treatment (PWHT: `pwht_temp_C` and `pwht_time_h`), because they differ between rows of the same weld.

This choice was an assumption. A weld with the same composition and parameters, before and after PWHT, is essentially the same weld. If we separated these rows, the model would only have to learn the effect of PWHT on a weld it already knows. We considered this less useful than the main task: predict the quality of a new weld. We did not know how much this choice changes the final models. But it keeps the test score from being inflated by the easier task.

| Subject | Rule |
|---|---|
| Group | Rows with the same value in the composition and welding parameter columns (620 groups). `charpy_temp_C`, `pwht_temp_C` and `pwht_time_h` are not used. |
| Split | `GroupShuffleSplit`, 80/20, `random_state=42`. One group is never in both sets. Result: 1332 train rows and 307 test rows. |
| Leakage check | 0 groups in both sets. 6 `weld_id`s are in both sets, but their compositions differ, so they are different welds with the same name. |
| Saved files | `data/train.csv` and `data/test.csv`, with the `input_group` column. The cross-validation folds later kept each group in one fold. |
| Missing values in train | The inputs are complete. The targets are missing in 46% to 58% of the rows and are not imputed. |

## EDA and PCA ([4_eda_pca.ipynb](preprocessing/4_eda_pca.ipynb))

We used only `train.csv`. The test set stayed closed. We plotted the correlations between inputs, between targets, and between inputs and targets. We standardised the 30 inputs and fitted a PCA. The targets were not part of the PCA. We projected them on it afterwards.

The EDA changed nothing in the data: we dropped no row and no column. Two results supported modelling choices:

- **No PCA reduction:** 12 components were needed for 80% of the variance, so the inputs do not compress. We did not use PCA as a preprocessing step.
- **Alloy families:** The PCA separated the families of `definition_bonne_soudure.md`. We stratified the cross-validation folds on the family, and we gave the metrics per family.

## Classification Approach

We want to predict whether a weld is good. More info in: [definition_bonne_soudure.md](docs/definition_bonne_soudure.md).

1. **Properties:** Whether a weld is good can be inferred from four of its properties: `yield_strength_MPa`, `uts_MPa`, `elongation_pct` and `charpy_toughness_J` (measured at `charpy_temp_C`). We used them as our targets.
2. **Thresholds:** We found a threshold for each property in the literature. A weld was good when it passed all four.
3. **Families:** We also found that the thresholds differ by family of weld. We therefore had two steps to define a good weld:
    - **Family:** We inferred the family of each weld from `Cr`, `Mo` and `V` (rule in the table below). A weld that matched no range was C-Mn.
    - **Qualification:** We qualified each weld with the thresholds of its family (table below).

| | CrMo2 | CrMo91 | CrMo9 | C-Mn |
|---|---|---|---|---|
| Rule | 1.9 ≤ `Cr` ≤ 2.7, 0.85 ≤ `Mo` ≤ 1.35 | 8 ≤ `Cr` ≤ 10.5, `V` ≥ 0.15 | 8 ≤ `Cr` ≤ 10.5, `V` < 0.15 | other rows |
| `yield_strength_MPa` | ≥ 400 | ≥ 415 | ≥ 435 | ≥ 420 |
| `uts_MPa` | ≥ 500 | ≥ 585 | ≥ 590 | 500 to 640 |
| `elongation_pct` | ≥ 18 | ≥ 17 | ≥ 18 | ≥ 20 |
| `charpy_toughness_J` | ≥ 47 at 20 °C | ≥ 47 at 20 °C | ≥ 34 at 20 °C | ≥ 47 at -40 °C |



**Main Methodology:** We predicted the four properties with regressions, then applied the family thresholds to get the good/bad label. Each property has 558 to 723 rows, while only 175 welds have all four and a label. We also tested a direct classifier of the label (see the Direct Classification section).

1. We trained one regression per property, on the rows where it is known (620, 596, 558 and 723 rows).
2. We used 5-fold cross-validation on `train.csv`, with the same grouping as the train/test split (`input_group`). We also stratified the folds on the family, so each fold contained Cr-Mo welds. The folds were the same for the four regressions and for every model.
3. The trees minimised the squared error. We tuned the hyperparameters per property by grid search on the MAE, on the same folds as the evaluation, so the cross-validation scores are a little optimistic. The test set gives the unbiased score.
4. We applied the family thresholds to the four predictions. For Charpy, we predicted at the threshold temperature of the family (see the example below). A weld was bad when one prediction failed.
5. **Metrics:** We measured each regression on the rows where its property was measured, and the good/bad label on the 175 welds with a label, out of fold.
   - **MAE:** The mean absolute error, in the unit of the property.
   - **RMSE:** The square root of the mean squared error. It gives more weight to the large errors.
   - For the label, a bad weld was the positive class. A missed bad weld goes into service, while a false alarm only costs an extra test.
   - **Recall on bad:** Bad welds predicted bad, divided by all bad welds. The share of bad welds that the model caught.
   - **Precision on good:** Good welds predicted good, divided by all welds predicted good. The share of accepted welds that were really good.
   - **F1 on bad:** 2 × precision on bad × recall on bad, divided by precision on bad + recall on bad. The precision on bad is the bad welds predicted bad, divided by all welds predicted bad. The F1 is high only when the model catches the bad welds without too many false alarms.

**Example for `charpy_toughness_J`:** Unlike the other three properties, one weld can have several Charpy rows. These rows have the same inputs except `charpy_temp_C`, because the toughness changes with the test temperature. The weld `Evans-StressRelief-1991-0.065C` (C-Mn) has six:

| `charpy_temp_C` | -70 | -60 | -50 | -40 | -20 | 20 |
|---|---|---|---|---|---|---|
| `charpy_toughness_J` | 30 | 72 | 119 | **165** | 201 | 206 |

The C-Mn threshold is 47 J at -40 °C. We therefore judged the weld on its toughness at -40 °C only: 165 J, pass. Many welds have no row at exactly -40 °C. We therefore set `charpy_temp_C` = -40 in the inputs of the Charpy model, and used its prediction.

## Baseline ([0_baseline.ipynb](modeling/0_baseline.ipynb))

The methodology above is coded once in [helpers/utils.py](modeling/helpers/utils.py), and every model used it. The baseline always predicted the mean of the train folds. Every model had to beat it.

- **Baseline result:** MAE of 73 MPa (yield), 73 MPa (UTS), 4.0% (elongation) and 40 J (Charpy). F1 and recall of 0: the means passed every threshold, so the baseline called every weld good.
- **Reference F1:** A rule that called every weld bad had an F1 of 0.64 (83 bad welds out of 175). A useful model had to be above it.
- **Reference precision on good:** The baseline accepted every weld, so its precision on good was the share of good welds, 0.53. A useful model had to be above it.

## Trees and Ensembles ([1B_trees_ensembles.ipynb](modeling/1B_trees_ensembles/1B_trees_ensembles.ipynb))

We tuned four tree models per target with a grid search on the same folds, one notebook each (`1B1` to `1B4`). The ensembles used 200 trees.

| Model | MAE yield (MPa) | MAE UTS (MPa) | MAE elongation (%) | MAE Charpy (J) | Label F1 | Label recall | Label precision on good |
|---|---|---|---|---|---|---|---|
| Baseline (mean) | 72.6 | 73.5 | 4.01 | 39.9 | 0.00 | 0.00 | 0.53 |
| Pruned CART | 48.2 | 41.8 | 2.60 | 18.9 | 0.77 | 0.81 | 0.81 |
| Bagging | 35.2 | 30.9 | 1.95 | 19.1 | 0.81 | 0.72 | 0.79 |
| Random forest | 34.0 | 29.6 | 1.94 | 19.1 | 0.76 | 0.64 | 0.75 |
| Extra-Trees | 29.1 | 25.2 | 1.78 | 17.4 | 0.84 | 0.72 | 0.80 |

- **Best model:** The Extra-Trees had the lowest MAE on every target (55% to 66% below the baseline) and the best label F1.
- **Averaging:** The largest gain came from the pruned tree to the bagging (-25% to -27% on the tensile targets). Averaging many trees removed most of the variance of a single tree.
- **Charpy:** The ensembles missed most non-conforming Charpy rows (recall of 0.10 to 0.17, against 0.62 for the pruned tree). The mean of 200 trees rarely fell below the 47 J threshold.
- **Cr-Mo welds:** Every model was much worse on Cr-Mo than on C-Mn (Extra-Trees yield MAE: 44.7 MPa on CrMo2, 27.1 MPa on C-Mn). The per-family label metrics rely on 8 and 6 rows, so we did not use them to compare the models.

## Direct Classification ([1D_direct_classification.ipynb](modeling/1D_direct_classification/1D_direct_classification.ipynb))

We trained five classifiers on the good/bad label directly, one notebook each (`1D1` to `1D5`). We compared them with the label of the `1B` regressions, to test whether the four regressions and the thresholds were necessary.

1. **One row per weld:** In `train.csv`, one weld can have several rows, for example one row for its tensile test and one row per Charpy test temperature. A classifier needs one row and one label per weld, so we merged the rows of each weld into one row, with the grouping of the Train/Test Split section. The rows of one weld can have different PWHT, so we kept the PWHT with the lowest and the highest temperature as inputs: `pwht_temp_C_low`, `pwht_time_h_low`, `pwht_temp_C_high`, `pwht_time_h_high`. A weld had a label only when all four properties were measured and could be compared with their thresholds. 175 welds had a label: 83 bad and 92 good.
2. We used the same folds as the regressions. We tuned each classifier by grid search on the F1 of the bad rows.
3. **Test of the tuning bias:** We chose the hyperparameters on the same 5 folds that gave the F1, so part of this F1 could be luck. To measure this part, we ran a nested cross-validation. For each fold k, we repeated the grid search on the 4 other folds only, and the selected model predicted fold k. Fold k had no part in the choice, so the nested F1 had no tuning bias. A nested F1 close to the F1 meant that the tuning did not inflate it. `results.csv` has the F1 without nesting.

**Example for the k-NN:** On the 5 folds, the grid search selected 1 neighbour (F1 of 0.80). In the nested cross-validation, it selected 1 neighbour for three folds, and 5 and 33 neighbours with distance-weighted votes for the two others. The nested F1 was 0.75: about 0.05 of the 0.80 came from the choice of the hyperparameters.

| Model | Selected hyperparameters | F1 | Recall | Precision on good | Nested F1 |
|---|---|---|---|---|---|
| Naive Bayes | PCA with 23 components first (the inputs are correlated) | 0.70 | 0.69 | 0.73 | 0.66 |
| k-NN | 1 neighbour, Euclidean distance | 0.80 | 0.82 | 0.83 | 0.75 |
| SVM | Polynomial kernel of degree 2, `C` = 100 | 0.84 | 0.83 | 0.85 | 0.85 |
| Classification tree | Pruned to 23 leaves | 0.72 | 0.71 | 0.75 | 0.70 |
| Random forest | 200 trees, `max_features` of 0.1, `min_samples_leaf` of 1 | 0.75 | 0.69 | 0.75 | 0.70 |
- **Best model:** The SVM had the same F1 as the Extra-Trees of `1B` (0.84) and a higher recall (0.83 against 0.72). Its nested F1 was 0.85, so the tuning did not inflate it.
- **Nested F1:** From 0.05 below (k-NN, random forest) to 0.01 above (SVM) the F1 without nesting. A change of 0.05 was as large as the gaps between several models, so the F1 without nesting could not rank models closer than this. The `1B` models had no nested test, so their F1 had the same risk.
- **Same model, two approaches:** The regressions were better or equal: 0.77 against 0.72 for the pruned trees, 0.76 against 0.75 for the random forests. Each regression learned from 558 to 723 rows of `train.csv`, a classifier from 175 rows only.
- **Different errors:** The Extra-Trees missed 23 bad rows with no false alarm. The SVM missed 14 with 12 false alarms. Their numbers of errors did not differ significantly (McNemar p = 0.73). A row flagged by either model gave a recall of 0.90 and an F1 of 0.88. We chose this rule after we saw the errors, so the test set must confirm it.
- **Cr-Mo welds:** 14 rows (8 CrMo2, 6 CrMo91), too few to compare the models.

## Semi-Supervised Learning

Many rows of the train set have no label or no target value. Semi-supervised learning uses these rows too, in addition to the labelled ones. We tested two methods from the literature review in [semi_supervised.md](docs/semi_supervised.md). Both used the same 5 folds as every other model.

### K-means Clustering ([2_1_kmeans.ipynb](modeling/2_semi_supervised/2_1_kmeans.ipynb))

**Data:** We used the one row per weld of the Direct Classification section, but we also kept the welds without a label. This gave 496 rows: the 175 labelled rows, and 321 rows without a label, most often because the weld had no Charpy test.

**Idea:** Semi-supervised methods assume that welds with similar inputs have the same label. Then the 321 unlabelled rows still show where the groups of similar welds are, and these groups help to label a new weld.

1. **Groups of similar welds:** K-means split the 496 rows into k groups, called clusters, of rows with similar standardised inputs. We tried k from 2 to 130.
2. **Do the clusters follow the label?** In each cluster, we took the most common label of its labelled rows. The purity was the share of all labelled rows that had the most common label of their cluster. A purity of 1 meant that each cluster held only good rows or only bad rows. Small clusters are pure by chance, so we compared with the purity of the same clusters after we shuffled the labels at random.
3. **Prediction:** For each fold, we ran K-means on the rows of the 4 other folds. Each cluster got the most common label of its labelled rows. Each labelled row of the held-out fold got the label of its nearest cluster, and we measured the F1 on the bad rows. We ran this twice: with the labelled rows only, then with the 321 unlabelled rows added. If the unlabelled rows helped, the second run had a higher F1.
4. **Are labelled and unlabelled rows alike?** A random forest learned to guess, from the inputs only, if a row had a label or not. An AUC near 0.5 meant that the two kinds of rows looked the same. An AUC near 1 meant that they were different welds, so the unlabelled rows could not tell much about the labelled ones.

| k | Purity | Purity with shuffled labels |
|---|---|---|
| 2 | 0.63 | 0.53 |
| 10 | 0.66 | 0.57 |
| 40 | 0.74 | 0.62 |
| 130 | 0.83 | 0.69 |

| k | Rows used | F1 | Recall | Precision on good |
|---|---|---|---|---|
| 2 | Labelled only | 0.43 | 0.28 | 0.61 |
| 2 | With the unlabelled rows | 0.28 | 0.17 | 0.56 |
| 10 | Labelled only | 0.63 | 0.66 | 0.67 |
| 10 | With the unlabelled rows | 0.48 | 0.35 | 0.60 |
| 40 | Labelled only | 0.69 | 0.70 | 0.72 |
| 40 | With the unlabelled rows | 0.60 | 0.59 | 0.64 |
| 130 | Labelled only | 0.81 | 0.83 | 0.84 |
| 130 | With the unlabelled rows | 0.69 | 0.73 | 0.73 |

- **Number of clusters:** The inertia, the total distance of the rows to the centre of their cluster, fell smoothly with k, with no clear elbow. The silhouette stayed between 0.23 and 0.40, so the clusters overlapped. The rows did not form a clear number of groups.
- **Do the clusters follow the label:** In part. The purity was above the purity with shuffled labels for every k, but far from 1. And 22 of the 40 clusters held no labelled row at all.
- **Unlabelled rows:** For every k except k = 5, they lowered the F1, the recall and the precision on good.
- **Two kinds of rows:** The random forest reached an AUC of 0.946. 220 of the 321 unlabelled rows had no Charpy value, and their inputs differed, P and voltage first. The unlabelled rows were mostly different welds, which most likely explained why they made K-means worse.
- **More clusters:** The F1 rose with k, but not because of the clusters. The 4 training folds held 138 to 143 labelled rows, so with 130 clusters each cluster held about one row. K-means then copied the label of the nearest labelled row: F1 of 0.81, against 0.80 for the k-NN of the Direct Classification section.
- **Conclusion:** K-means did not help to classify the label, and the unlabelled rows made it worse.

### Self-Training of the Regressions ([2_2_self_training.ipynb](modeling/2_semi_supervised/2_2_self_training.ipynb))

**Data:** Each regression learns one property on the rows of `train.csv` where this property was measured. About half of the rows have no value: for example, 712 of the 1332 rows have no `yield_strength_MPa`. We used `yield_strength_MPa`, `uts_MPa` and `elongation_pct`. We left out Charpy, because the model needs a test temperature, and the rows without a Charpy value had none.

**Idea:** In self-training, the model predicts the missing values and keeps the predictions it is most sure of. These predictions, called pseudo-labels, become extra training rows, and the model is trained again. This helps only if the pseudo-labels are close to the truth, and if the extra rows show the model welds it did not know.

1. **Rows to fill:** Many rows without a yield strength have the same inputs as a row with one, like the Charpy rows `Mart-Aa` to `Mart-Ak` of the Train/Test Split section. Such a row adds nothing new, so we removed it. We also kept one row per distinct input. The rows left were the pool.
2. **How sure is the model:** The model was the Extra-Trees of the Trees and Ensembles section, which average 200 trees. When the trees disagree on a row, the model is less sure. The spread was the standard deviation of the 200 tree predictions. Each tree learned from a random sample of the rows, called a bootstrap, so that the trees also disagreed near the training rows.
3. **Does the spread work:** On the labelled rows, out of fold, we sorted the predictions by spread into 5 groups of the same size and computed the MAE of each group. If the spread works, the MAE rises from the group with the lowest spread to the group with the highest.
4. **Self-training:** For each fold, we trained the model on the labelled rows of the 4 other folds. Then, 3 times: the model predicted the pool rows of these folds, the 25% of the pool with the lowest spread got their prediction as value, and we trained the model again with them. We fixed 25% and 3 rounds before we saw any result.
5. **Comparison:** The same model without the extra rows, on the same folds. A lower MAE with the extra rows meant that self-training helped. We also applied the thresholds to both, with the same Charpy model, to compare the good/bad label.
6. **Are the pool rows like the labelled rows:** The same random forest test as for K-means. We also measured the distance from each pool row to the nearest labelled row, on the standardised inputs.

| Target | Pool rows | AUC labelled against pool | MAE without pseudo-labels | MAE with pseudo-labels | Folds improved |
|---|---|---|---|---|---|
| `yield_strength_MPa` | 192 | 0.996 | 30.35 MPa | 31.09 MPa | 1 of 5 |
| `uts_MPa` | 217 | 0.995 | 26.92 MPa | 26.75 MPa | 3 of 5 |
| `elongation_pct` | 251 | 0.990 | 1.835% | 1.841% | 3 of 5 |

| Label | F1 | Recall | Precision on good |
|---|---|---|---|
| Without pseudo-labels | 0.80 | 0.66 | 0.77 |
| With pseudo-labels | 0.79 | 0.65 | 0.76 |

- **Does the spread work:** On the labelled rows, yes, but loosely. For the yield strength, the MAE was 18.9 MPa in the group with the lowest spread and 48.1 MPa in the group with the highest. The Spearman correlation between spread and error was only 0.23 to 0.36.
- **Pool rows:** They were different welds. The random forest told them from the labelled rows with an AUC of 0.990 to 0.996. A pool row was at a median distance of 1.41 to 3.97 from the nearest labelled row, while two labelled rows of different folds were at 0.89 to 0.91. So the model predicted the pool rows far from what it had learned, and the spread on them was not checked.
- **Results:** No change was larger than the noise. Per fold, the MAE changed by at most 1.9 MPa, while the MAE varies by about 3 MPa from one fold to another. On the label, only 3 of the 175 labelled rows changed, and the three metrics moved by about 0.01.
- **Bootstrap:** The bootstrap, needed for the spread, lowered the label F1 from 0.84, for the Extra-Trees without bootstrap, to 0.80.
- **Conclusion:** Self-training did not improve the regressions. The rows without a value were too far from the labelled rows for the pseudo-labels to add information.
