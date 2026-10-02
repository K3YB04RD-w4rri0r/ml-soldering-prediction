"""Shared evaluation protocol of the modelling notebooks.

Every model is evaluated the same way, so that the results of the whole team
can be compared in one table (results.csv):

- one regression per target, trained on the rows where that target is known;
- the inputs are standardised inside a Pipeline (StandardScaler + model);
- 5-fold cross-validation grouped on weld_group and stratified on the alloy
  family, with the same folds for every target and every person;
- MAE and RMSE per target, then F1 and recall on the non-conforming welds once
  the thresholds of definition_bonne_soudure.md are applied to the predictions.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import f1_score, recall_score
from sklearn.model_selection import PredefinedSplit, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TRAIN_PATH = Path(__file__).resolve().parent.parent / "data" / "train.csv"
RESULTS_PATH = Path(__file__).resolve().parent / "results.csv"

SEED = 42
N_FOLDS = 5

CHEM_COLS = ["C", "Si", "Mn", "S", "P", "Ni", "Cr", "Mo", "V", "O_ppm", "Ti_ppm", "N_ppm", "Al_ppm", "Nb_ppm"]
PROCESS_COLS = [
    "current_A", "voltage_V", "AC_DC", "electrode_polarity", "AC_DC_unknown",
    "heat_input_kJ_mm", "interpass_temp_C", "pwht_temp_C", "pwht_time_h",
    "weld_type_FCA", "weld_type_GMAA", "weld_type_GTAA", "weld_type_MMA",
    "weld_type_SA", "weld_type_SAA", "weld_type_TSA",
]
INPUT_COLS = CHEM_COLS + PROCESS_COLS

TARGETS = ["yield_strength_MPa", "uts_MPa", "elongation_pct", "charpy_toughness_J"]
CHARPY = "charpy_toughness_J"

# Minimums (and UTS maximum) of each alloy family, from definition_bonne_soudure.md.
# The Charpy criterion is "at least charpy_min_J at charpy_temp_ref_C".
THRESHOLDS = pd.DataFrame(
    {
        "yield_min": [420, 400, 415, 435],
        "uts_min": [500, 500, 585, 590],
        "uts_max": [640, np.inf, np.inf, np.inf],
        "elongation_min": [20, 18, 17, 18],
        "charpy_min_J": [47, 47, 47, 34],
        "charpy_temp_ref_C": [-40, 20, 20, 20],
    },
    index=["C-Mn", "CrMo2", "CrMo91", "CrMo9"],
)

# CrMo9 (1 row in train) only counts in the "all" rows of the results.
REPORT_FAMILIES = ["all", "C-Mn", "CrMo2", "CrMo91"]
RESULT_COLS = ["model", "target", "family", "n", "MAE", "RMSE", "MAE_std", "RMSE_std", "n_clf", "n_nc", "F1_nc", "recall_nc"]


def add_family(df):
    """Alloy family of each row, from Cr, Mo and V (rules of definition_bonne_soudure.md)."""
    family = pd.Series("C-Mn", index=df.index)
    family[df["Cr"].between(1.9, 2.7) & df["Mo"].between(0.85, 1.35)] = "CrMo2"
    family[df["Cr"].between(8, 10.5) & (df["V"] >= 0.15)] = "CrMo91"
    family[df["Cr"].between(8, 10.5) & (df["V"] < 0.15)] = "CrMo9"
    return family


def load_train(path=TRAIN_PATH):
    """train.csv with two more columns, `family` and `fold`.

    Each weld_group gets one fold (0 to 4) once for all, so a deposit is in the
    same fold for every target. The folds are stratified on the family
    (CrMo9 merged with CrMo91, as it has a single group) so that every fold
    holds Cr-Mo welds.
    """
    df = pd.read_csv(path)
    df["family"] = add_family(df)

    strata = df["family"].replace({"CrMo9": "CrMo91"})
    splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    fold = np.full(len(df), -1)
    for k, (_, val_idx) in enumerate(splitter.split(df, strata, groups=df["weld_group"])):
        fold[val_idx] = k
    df["fold"] = fold
    return df


def input_cols(target):
    """Inputs of the model of `target`: `charpy_temp_C` is only an input of the Charpy model."""
    return INPUT_COLS + ["charpy_temp_C"] if target == CHARPY else INPUT_COLS


def get_xy(df, target):
    """X, y and the cross-validation splitter of `target`, on the rows where it is known.

    The splitter uses the `fold` column, pass it as `cv` to GridSearchCV or
    cross_val_score to get the same folds as everyone else.
    """
    cols = input_cols(target)
    data = df[df[target].notna() & df[cols].notna().all(axis=1)]
    return data[cols], data[target], PredefinedSplit(data["fold"])


def build_pipeline(model):
    """StandardScaler + model. A model that is already a Pipeline is used as it is."""
    if isinstance(model, Pipeline):
        return clone(model)
    return Pipeline([("scaler", StandardScaler()), ("model", model)])


def oof_predict(model, df, target):
    """Out-of-fold predictions of `target`, on the rows where it is known.

    Returns a DataFrame with `pred`, the prediction for the row, and `pred_ref`,
    the prediction the criterion is applied to. For Charpy, `pred_ref` is the
    energy predicted at the reference temperature of the family (-40 C for
    C-Mn, +20 C for Cr-Mo). For the other targets it is equal to `pred`.
    """
    X, y, cv = get_xy(df, target)
    X_ref = X.copy()
    if target == CHARPY:
        X_ref["charpy_temp_C"] = df.loc[X.index, "family"].map(THRESHOLDS["charpy_temp_ref_C"]).astype(float)

    out = pd.DataFrame(np.nan, index=X.index, columns=["pred", "pred_ref"])
    for train_idx, val_idx in cv.split():
        pipe = build_pipeline(model).fit(X.iloc[train_idx], y.iloc[train_idx])
        pred = pipe.predict(X.iloc[val_idx])
        out.iloc[val_idx, 0] = pred
        out.iloc[val_idx, 1] = pipe.predict(X_ref.iloc[val_idx]) if target == CHARPY else pred
    return out


def _thresholds(df):
    return THRESHOLDS.loc[df["family"]].set_index(df.index)


def _tensile_criterion(target, values, th):
    if target == "yield_strength_MPa":
        passed = values >= th["yield_min"]
    elif target == "uts_MPa":
        passed = (values >= th["uts_min"]) & (values <= th["uts_max"])
    else:
        passed = values >= th["elongation_min"]
    return passed.astype(float).where(values.notna())


def true_criteria(df):
    """Measured conformity of each row and criterion: 1 = conforming, 0 = not, NaN = unknown.

    Charpy is only decided when the measure allows it (definition_bonne_soudure.md):
    conforming if T <= T_ref and E >= E_min, not conforming if T >= T_ref and
    E < E_min, unknown otherwise. Cr-Mo rows without PWHT are outside the
    conditions of their standard and are left unknown.
    """
    th = _thresholds(df)
    crit = pd.DataFrame(np.nan, index=df.index, columns=TARGETS)
    for target in TARGETS[:3]:
        crit[target] = _tensile_criterion(target, df[target], th)

    energy, temp = df[CHARPY], df["charpy_temp_C"]
    passed = (temp <= th["charpy_temp_ref_C"]) & (energy >= th["charpy_min_J"])
    failed = (temp >= th["charpy_temp_ref_C"]) & (energy < th["charpy_min_J"])
    crit[CHARPY] = np.select([passed, failed], [1.0, 0.0], np.nan)

    crit.loc[(df["family"] != "C-Mn") & (df["pwht_temp_C"] == 0)] = np.nan
    return crit


def predicted_criteria(df, preds):
    """Predicted conformity of each row, from {target: oof_predict(...)}: 1, 0 or NaN."""
    th = _thresholds(df)
    crit = pd.DataFrame(np.nan, index=df.index, columns=TARGETS)
    for target, pred in preds.items():
        values = pred["pred_ref"].reindex(df.index)
        if target == CHARPY:
            crit[target] = (values >= th["charpy_min_J"]).astype(float).where(values.notna())
        else:
            crit[target] = _tensile_criterion(target, values, th)
    return crit


def deposit_labels(df, true_crit, pred_crit):
    """True and predicted label of each weld deposit (weld_group): 1 = non-conforming.

    A deposit is labelled when each of the 4 criteria is decided on at least
    one of its rows. It is non-conforming as soon as one criterion fails on
    one row. The predicted label applies the same rule to the predictions of
    the same rows, so both labels are built from the same information.
    """
    group = df["weld_group"]
    true_g = true_crit.groupby(group).min()
    pred_g = pred_crit.where(true_crit.notna()).groupby(group).min()
    labelled = true_g.notna().all(axis=1)
    return pd.DataFrame({
        "family": df.groupby("weld_group")["family"].first(),
        "true_nc": (true_g.min(axis=1) == 0).astype(int),
        "pred_nc": (pred_g.min(axis=1) == 0).astype(int),
    })[labelled]


def _regression_metrics(y, pred, fold):
    error = pred - y
    per_fold = pd.DataFrame({"abs": error.abs(), "sq": error ** 2, "fold": fold}).groupby("fold").mean()
    return {
        "n": len(y),
        "MAE": error.abs().mean(),
        "RMSE": np.sqrt((error ** 2).mean()),
        "MAE_std": per_fold["abs"].std(),
        "RMSE_std": np.sqrt(per_fold["sq"]).std(),
    }


def _classification_metrics(true_nc, pred_nc):
    if len(true_nc) == 0:
        return {"n_clf": 0, "n_nc": 0, "F1_nc": np.nan, "recall_nc": np.nan}
    return {
        "n_clf": len(true_nc),
        "n_nc": int(true_nc.sum()),
        "F1_nc": f1_score(true_nc, pred_nc, zero_division=0),
        "recall_nc": recall_score(true_nc, pred_nc, zero_division=0),
    }


def _family_mask(families, family):
    return families == family if family != "all" else pd.Series(True, index=families.index)


def evaluate(name, models, df):
    """Cross-validate `models` and return the rows of the results table.

    `models` is one estimator used for the 4 targets, or a dict {target: estimator},
    for example the best estimator of a grid search for each target.

    One row per target and family:
    - n, MAE, RMSE: out-of-fold predictions on the rows where the target is known,
      MAE_std and RMSE_std are the standard deviations over the 5 folds;
    - n_clf, n_nc, F1_nc, recall_nc: the criterion of this target, on the rows
      where it is decided (n_clf rows, n_nc of them non-conforming), with
      "non-conforming" as the positive class.
    When the 4 targets are given, the rows with target = "label" give the same
    classification metrics for the full label, on the labelled weld deposits.
    """
    if not isinstance(models, dict):
        models = {target: models for target in TARGETS}

    true_crit = true_criteria(df)
    preds = {target: oof_predict(model, df, target) for target, model in models.items()}
    pred_crit = predicted_criteria(df, preds)

    rows = []
    for target, pred in preds.items():
        families = df.loc[pred.index, "family"]
        decided = true_crit.loc[pred.index, target].notna()
        for family in REPORT_FAMILIES:
            mask = _family_mask(families, family)
            idx = pred.index[mask]
            clf_idx = pred.index[mask & decided]
            rows.append({
                "model": name, "target": target, "family": family,
                **_regression_metrics(df.loc[idx, target], pred.loc[idx, "pred"], df.loc[idx, "fold"]),
                **_classification_metrics(true_crit.loc[clf_idx, target] == 0, pred_crit.loc[clf_idx, target] == 0),
            })

    if set(TARGETS) <= set(preds):
        labels = deposit_labels(df, true_crit, pred_crit)
        for family in REPORT_FAMILIES:
            mask = _family_mask(labels["family"], family)
            rows.append({
                "model": name, "target": "label", "family": family,
                **_classification_metrics(labels.loc[mask, "true_nc"], labels.loc[mask, "pred_nc"]),
            })

    return _format(pd.DataFrame(rows))


def _format(results):
    return results.reindex(columns=RESULT_COLS).astype({"n": "Int64", "n_clf": "Int64", "n_nc": "Int64"})


def save_results(results, path=RESULTS_PATH):
    """Add `results` to the shared table, replacing the previous rows of the same model."""
    path = Path(path)
    if path.exists():
        previous = pd.read_csv(path)
        results = pd.concat([previous[~previous["model"].isin(results["model"])], results])

    order = {value: i for i, value in enumerate(TARGETS + ["label"] + REPORT_FAMILIES)}
    results = results.sort_values(["model", "target", "family"], key=lambda col: col.map(order) if col.name != "model" else col)
    results = _format(results).reset_index(drop=True)
    results.to_csv(path, index=False, float_format="%.4f")
    return results


def load_results(path=RESULTS_PATH):
    """The shared results table."""
    return _format(pd.read_csv(path))
