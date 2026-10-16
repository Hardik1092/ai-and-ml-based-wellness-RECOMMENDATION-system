from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    precision_recall_fscore_support, log_loss,
)


def evaluate_model(model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted", zero_division=0
    )
    labels = sorted(set(list(y_test) + list(y_pred)))
    macro = precision_recall_fscore_support(y_test, y_pred, average="macro", zero_division=0)
    calibration = {}
    if hasattr(model, "predict_proba"):
        import numpy as np
        probabilities = model.predict_proba(X_test)
        truth = np.array([[int(label == cls) for cls in model.classes_] for label in y_test])
        calibration = {"log_loss": float(log_loss(y_test, probabilities, labels=model.classes_)),
                       "multiclass_brier": float(np.mean(np.sum((probabilities - truth) ** 2, axis=1)))}
    return {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "macro_precision": float(macro[0]), "macro_recall": float(macro[1]),
        "macro_f1": float(macro[2]), "weighted_f1": float(f1),
        **calibration,
        "labels": labels,
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=labels).tolist(),
        "report": classification_report(y_test, y_pred, zero_division=0, output_dict=True),
    }
