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

We want to predict whether a weld is good. More info in: [definition_bonne_soudure.md](definition_bonne_soudure.md).

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



**Final Methodology:** We predicted the four properties with regressions, then applied the family thresholds to get the good/bad label. A direct classifier would have had only 175 labelled welds. Each property alone has 558 to 723 rows.

1. We trained one regression per property, on the rows where it is known (620, 596, 558 and 723 rows).
2. We used 5-fold cross-validation on `train.csv`, with the same grouping as the train/test split (`input_group`). We also stratified the folds on the family, so each fold contained Cr-Mo welds. The folds were the same for the four regressions and for every model.
3. The trees minimised the squared error. We tuned the hyperparameters per property by grid search on the MAE.
4. We applied the family thresholds to the four predictions. For Charpy, we predicted at the threshold temperature of the family (see the example below). A weld was bad when one prediction failed.
5. We measured each regression with MAE and RMSE, and the good/bad label with F1 and recall on the bad welds, against the measured labels.

**Example for `charpy_toughness_J`:** Unlike the other three properties, one weld can have several Charpy rows. These rows have the same inputs except `charpy_temp_C`, because the toughness changes with the test temperature. The weld `Evans-StressRelief-1991-0.065C` (C-Mn) has six:

| `charpy_temp_C` | -70 | -60 | -50 | -40 | -20 | 20 |
|---|---|---|---|---|---|---|
| `charpy_toughness_J` | 30 | 72 | 119 | **165** | 201 | 206 |

The C-Mn threshold is 47 J at -40 °C. We therefore judged the weld on its toughness at -40 °C only: 165 J, pass. Many welds have no row at exactly -40 °C. We therefore set `charpy_temp_C` = -40 in the inputs of the Charpy model, and used its prediction.

## Baseline ([0_baseline.ipynb](modeling/0_baseline.ipynb))

The methodology above is coded once in [helpers/utils.py](modeling/helpers/utils.py), and every model used it. The baseline always predicted the mean of the train folds. Every model had to beat it.

- **Baseline result:** MAE of 73 MPa (yield), 73 MPa (UTS), 4.0% (elongation) and 40 J (Charpy). F1 and recall of 0: the means passed every threshold, so the baseline called every weld good.
- **Reference F1:** A rule that called every weld bad had an F1 of 0.64 (83 bad welds out of 175). A useful model had to be above it.

## Trees and Ensembles ([1B_trees_ensembles.ipynb](modeling/1B_trees_ensembles.ipynb))

We tuned four tree models per target with a grid search on the same folds, one notebook each (`1B1` to `1B4`). The ensembles used 200 trees.

| Model | MAE yield (MPa) | MAE UTS (MPa) | MAE elongation (%) | MAE Charpy (J) | Label F1 | Label recall |
|---|---|---|---|---|---|---|
| Baseline (mean) | 72.6 | 73.5 | 4.01 | 39.9 | 0.00 | 0.00 |
| Pruned CART | 48.2 | 41.8 | 2.60 | 18.9 | 0.77 | 0.81 |
| Bagging | 35.2 | 30.9 | 1.95 | 19.1 | 0.81 | 0.72 |
| Random forest | 34.0 | 29.6 | 1.94 | 19.1 | 0.76 | 0.64 |
| Extra-Trees | 29.1 | 25.2 | 1.78 | 17.4 | 0.84 | 0.72 |

- **Best model:** The Extra-Trees had the lowest MAE on every target (55% to 66% below the baseline) and the best label F1.
- **Averaging:** The largest gain came from the pruned tree to the bagging (-25% to -27% on the tensile targets). Averaging many trees removed most of the variance of a single tree.
- **Charpy:** The ensembles missed most non-conforming Charpy rows (recall of 0.10 to 0.17, against 0.62 for the pruned tree). The mean of 200 trees rarely fell below the 47 J threshold.
- **Cr-Mo welds:** Every model was much worse on Cr-Mo than on C-Mn (Extra-Trees yield MAE: 44.7 MPa on CrMo2, 27.1 MPa on C-Mn). The per-family label metrics rely on 8 and 6 deposits, so we did not use them to compare the models.
