"""Shared evaluation protocol of the modelling notebooks.

Every model is evaluated the same way, so that the results of the whole team
can be compared in one table (results.csv):

- one regression per target, trained on the rows where that target is known;
- the inputs are standardised inside a Pipeline (StandardScaler + model);
- 5-fold cross-validation grouped on input_group and stratified on the alloy
  family, with the same folds for every target and every person;
- MAE and RMSE per target, then F1, recall and accuracy (non-conforming = positive class) once
  the thresholds of definition_bonne_soudure.md are applied to the predictions,
  optionally with a safety margin (nested_margin_predict_label chooses it by
  nested cross-validation).

The direct classifiers of the label (1D notebooks) are trained on the labelled
weld deposits, one row per deposit, with the same folds, and give the same
"label" rows of the results table (evaluate_label).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import PredefinedSplit, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TRAIN_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "train.csv"
RESULTS_PATH = Path(__file__).resolve().parent.parent / "results.csv"

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

# Inputs of the direct classifiers, one row per deposit. The PWHT can change between the rows
# of a deposit, it is replaced by the heat treatment with the lowest and the highest temperature.
PWHT_COLS = ["pwht_temp_C", "pwht_time_h"]
PWHT_DEPOSIT_COLS = ["pwht_temp_C_low", "pwht_time_h_low", "pwht_temp_C_high", "pwht_time_h_high"]
DEPOSIT_COLS = [c for c in INPUT_COLS if c not in PWHT_COLS] + PWHT_DEPOSIT_COLS

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

# CrMo9 (no row in train, 1 row in the whole data) only counts in the "all" rows of the results.
REPORT_FAMILIES = ["all", "C-Mn", "CrMo2", "CrMo91"]
RESULT_COLS = ["model", "target", "family", "n", "MAE", "RMSE", "MAE_std", "RMSE_std", "n_clf", "n_nc", "F1_nc", "recall_nc", "accuracy"]


def add_family(df):
    """Alloy family of each row, from Cr, Mo and V (rules of definition_bonne_soudure.md)."""
    family = pd.Series("C-Mn", index=df.index)
    family[df["Cr"].between(1.9, 2.7) & df["Mo"].between(0.85, 1.35)] = "CrMo2"
    family[df["Cr"].between(8, 10.5) & (df["V"] >= 0.15)] = "CrMo91"
    family[df["Cr"].between(8, 10.5) & (df["V"] < 0.15)] = "CrMo9"
    return family


def load_train(path=TRAIN_PATH):
    """train.csv with two more columns, `family` and `fold`.

    Each input_group gets one fold (0 to 4) once for all, so a deposit is in the
    same fold for every target. The folds are stratified on the family
    (CrMo9 merged with CrMo91, as it has at most a single group) so that every fold
    holds Cr-Mo welds.
    """
    df = pd.read_csv(path)
    df["family"] = add_family(df)

    strata = df["family"].replace({"CrMo9": "CrMo91"})
    splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    fold = np.full(len(df), -1)
    for k, (_, val_idx) in enumerate(splitter.split(df, strata, groups=df["input_group"])):
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


def _tensile_criterion(target, values, th, margin=0):
    if target == "yield_strength_MPa":
        passed = values >= th["yield_min"] + margin
    elif target == "uts_MPa":
        passed = (values >= th["uts_min"] + margin) & (values <= th["uts_max"] - margin)
    else:
        passed = values >= th["elongation_min"] + margin
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


def predicted_criteria(df, preds, margin=None):
    """Predicted conformity of each row, from {target: oof_predict(...)}: 1, 0 or NaN.

    `margin` is an optional dict {target: margin in the unit of the target}. A prediction
    then passes a minimum only if it is at least the minimum + the margin, and the UTS
    maximum of the C-Mn welds only if it is at most 640 - the margin. For Charpy the
    margin applies to `pred_ref`, the energy predicted at the reference temperature.
    """
    margin = margin or {}
    th = _thresholds(df)
    crit = pd.DataFrame(np.nan, index=df.index, columns=TARGETS)
    for target, pred in preds.items():
        values = pred["pred_ref"].reindex(df.index)
        m = margin.get(target, 0)
        if target == CHARPY:
            crit[target] = (values >= th["charpy_min_J"] + m).astype(float).where(values.notna())
        else:
            crit[target] = _tensile_criterion(target, values, th, m)
    return crit


def deposit_labels(df, true_crit, pred_crit):
    """True and predicted label of each weld deposit (input_group): 1 = non-conforming.

    A deposit is labelled when each of the 4 criteria is decided on at least
    one of its rows. It is non-conforming as soon as one criterion fails on
    one row. The predicted label applies the same rule to the predictions of
    the same rows, so both labels are built from the same information.
    """
    group = df["input_group"]
    true_g = true_crit.groupby(group).min()
    pred_g = pred_crit.where(true_crit.notna()).groupby(group).min()
    labelled = true_g.notna().all(axis=1)
    return pd.DataFrame({
        "family": df.groupby("input_group")["family"].first(),
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
        return {"n_clf": 0, "n_nc": 0, "F1_nc": np.nan, "recall_nc": np.nan, "accuracy": np.nan}
    return {
        "n_clf": len(true_nc),
        "n_nc": int(true_nc.sum()),
        "F1_nc": f1_score(true_nc, pred_nc, zero_division=0),
        "recall_nc": recall_score(true_nc, pred_nc, zero_division=0),
        "accuracy": accuracy_score(true_nc, pred_nc),
    }


def _family_mask(families, family):
    return families == family if family != "all" else pd.Series(True, index=families.index)


def evaluate(name, models, df, margin=None):
    """Cross-validate `models` and return the rows of the results table.

    `models` is one estimator used for the 4 targets, or a dict {target: estimator},
    for example the best estimator of a grid search for each target. `margin` is the
    optional safety margin of predicted_criteria, it only changes the classification columns.

    One row per target and family:
    - n, MAE, RMSE: out-of-fold predictions on the rows where the target is known,
      MAE_std and RMSE_std are the standard deviations over the 5 folds;
    - n_clf, n_nc, F1_nc, recall_nc, accuracy: the criterion of this target, on the rows
      where it is decided (n_clf rows, n_nc of them non-conforming), with
      "non-conforming" as the positive class for F1 and recall.
    When the 4 targets are given, the rows with target = "label" give the same
    classification metrics for the full label, on the labelled weld deposits.
    """
    if not isinstance(models, dict):
        models = {target: models for target in TARGETS}

    true_crit = true_criteria(df)
    preds = {target: oof_predict(model, df, target) for target, model in models.items()}
    pred_crit = predicted_criteria(df, preds, margin)

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


def nested_margin_predict_label(models, df, deltas):
    """Out-of-fold predicted label of the regressions when the safety margin is chosen without the validation fold.

    `models` is one estimator or a dict {target: estimator}, as in evaluate, and `deltas` the
    grid of δ. For each fold k, the 4 other folds are the inner folds: the out-of-fold
    predictions of the 4 targets on these folds give the inner MAE of each target, and δ_k is
    the δ of the grid with the best F1 of the label on the deposits of these folds (the
    smallest δ in case of a tie), with a margin of δ × inner MAE. The deposits of fold k are
    then predicted by the models trained on the 4 other folds, with a margin of δ_k × inner MAE.
    Returns the predicted label of each labelled deposit (1 = non-conforming) and, for each
    fold, δ_k and the inner MAE of each target.
    """
    if not isinstance(models, dict):
        models = {target: models for target in TARGETS}
    deltas = sorted(deltas)

    true_crit = true_criteria(df)
    preds = {target: oof_predict(model, df, target) for target, model in models.items()}
    pred_crit = pd.DataFrame(np.nan, index=df.index, columns=TARGETS)
    chosen = []
    for k in range(N_FOLDS):
        inner = df[df["fold"] != k]
        inner_preds = {target: oof_predict(model, inner, target) for target, model in models.items()}
        mae = {target: (pred["pred"] - inner.loc[pred.index, target]).abs().mean() for target, pred in inner_preds.items()}
        f1 = []
        for delta in deltas:
            margin = {target: delta * mae[target] for target in mae}
            labels = deposit_labels(inner, true_crit.loc[inner.index], predicted_criteria(inner, inner_preds, margin))
            f1.append(f1_score(labels["true_nc"], labels["pred_nc"], zero_division=0))
        delta = deltas[int(np.argmax(f1))]
        outer = df[df["fold"] == k]
        pred_crit.loc[outer.index] = predicted_criteria(outer, preds, {target: delta * mae[target] for target in mae})
        chosen.append({"delta": delta, **{f"MAE_{target}": value for target, value in mae.items()}})

    pred = deposit_labels(df, true_crit, pred_crit)["pred_nc"]
    return pred, pd.DataFrame(chosen).rename_axis("fold")


def deposit_data(df):
    """One row per labelled weld deposit: its inputs (DEPOSIT_COLS), `fold`, `family` and `true_nc`.

    `true_nc` is the label of deposit_labels (1 = non-conforming). The composition and
    the welding parameters are the same on every row of a deposit (input_group), only the
    PWHT can change, for example an as-welded and a heat treated state. The label holds
    for all of them, so the deposit is described by its heat treatment with the lowest
    temperature (`_low`) and its heat treatment with the highest one (`_high`), which are
    equal when the deposit has a single state.
    """
    crit = true_criteria(df)
    labels = deposit_labels(df, crit, crit)
    groups = df.groupby("input_group")
    pwht = df.sort_values(PWHT_COLS).groupby("input_group")[PWHT_COLS]
    data = pd.concat([
        groups[[c for c in INPUT_COLS if c not in PWHT_COLS]].first(),
        pwht.first().add_suffix("_low"),
        pwht.last().add_suffix("_high"),
        groups["fold"].first(),
    ], axis=1)
    return data.loc[labels.index, DEPOSIT_COLS + ["fold"]].join(labels[["family", "true_nc"]])


def get_deposit_xy(df):
    """X, y and the cross-validation splitter of the direct classification, on the labelled deposits.

    y is 1 for a non-conforming deposit. The splitter uses the fold of each deposit, the
    same as in evaluate, pass it as `cv` to GridSearchCV or cross_val_score.
    """
    data = deposit_data(df)
    return data[DEPOSIT_COLS], data["true_nc"], PredefinedSplit(data["fold"])


def oof_predict_label(model, df):
    """Out-of-fold predicted label of each labelled deposit (`pred_nc`, 1 = non-conforming).

    `score` is the out-of-fold score of the non-conforming class: the probability of
    predict_proba, or decision_function for a model without probabilities (SVM).
    """
    X, y, cv = get_deposit_xy(df)
    out = pd.DataFrame(np.nan, index=X.index, columns=["pred_nc", "score"])
    for train_idx, val_idx in cv.split():
        pipe = build_pipeline(model).fit(X.iloc[train_idx], y.iloc[train_idx])
        X_val = X.iloc[val_idx]
        out.iloc[val_idx, 0] = pipe.predict(X_val)
        out.iloc[val_idx, 1] = pipe.predict_proba(X_val)[:, 1] if hasattr(pipe, "predict_proba") else pipe.decision_function(X_val)
    return out.astype({"pred_nc": int})


def nested_oof_predict_label(search, df):
    """Out-of-fold predicted label when the grid search is redone without the validation fold.

    `search` is a GridSearchCV of a classifier of the label, its `cv` is replaced. For each
    fold, the search is fitted on the 4 other folds, with these 4 folds as inner folds, and
    its best model predicts the fold. evaluate_label scores the hyperparameters chosen on the
    same 5 folds, which is a little optimistic, this nested cross-validation is not.
    Returns the predicted labels and the hyperparameters chosen for each fold.
    """
    X, y, cv = get_deposit_xy(df)
    fold = cv.test_fold
    pred = pd.Series(0, index=X.index, name="pred_nc")
    params = []
    for k in range(N_FOLDS):
        inner = clone(search).set_params(cv=PredefinedSplit(fold[fold != k]))
        inner.fit(X[fold != k], y[fold != k])
        pred[fold == k] = inner.predict(X[fold == k])
        params.append({name.removeprefix("model__"): value for name, value in inner.best_params_.items()})
    return pred, pd.DataFrame(params).rename_axis("fold")


def evaluate_label(name, model, df):
    """Cross-validate a classifier of the label and return its rows of the results table.

    The same rows as the "label" rows of evaluate: F1, recall and accuracy on the non-conforming
    deposits, on all the labelled deposits and per family. The regression columns are empty.
    """
    data = deposit_data(df)
    pred = oof_predict_label(model, df)
    rows = []
    for family in REPORT_FAMILIES:
        mask = _family_mask(data["family"], family)
        rows.append({
            "model": name, "target": "label", "family": family,
            **_classification_metrics(data.loc[mask, "true_nc"], pred.loc[mask, "pred_nc"]),
        })
    return _format(pd.DataFrame(rows))


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
