"""Small honest ML component: P(missed payment within 6 months) from forecast features.

The training data is SYNTHETIC: feature vectors are sampled from plausible ranges
and labeled with a noisy rule. This is a placeholder for training on real
repayment outcomes — the value here is the wiring (features in, probability out),
not the weights. The ML output never decides the verdict; it is a displayed
signal and a caution-rule input only (see verdict_rules.py).

Train and persist with:  python -m app.functions.risk_model
"""
import logging
import math

from app import config


logger = logging.getLogger("edraak.risk_model")

# Feature order is a contract between training, prediction, and the fallback.
FEATURE_NAMES = [
    "obligation_ratio_peak",      # % of salary at the worst month of the curve
    "min_buffer_over_income",     # worst monthly buffer / salary (can be negative)
    "salary_timing_variance_days",  # std dev of salary arrival day
    "bnpl_count",                 # active BNPL plans across all banks
    "savings_cover_months",       # months of savings cover at the worst month
    "banks_with_obligations",     # distinct banks where committed money leaves
]

_MODEL = None
_MODEL_LOADED = False


def predict_risk(features: dict) -> float:
    """Return P(missed payment within 6 months) for one feature dict."""
    vector = [float(features.get(name, 0) or 0) for name in FEATURE_NAMES]
    model = _load_model()
    if model is None:
        return _fallback_probability(vector)
    probability = float(model.predict_proba([vector])[0][1])
    return round(probability, 3)


def _load_model():
    """Load the joblib model once; None means we use the fallback formula."""
    global _MODEL, _MODEL_LOADED
    if _MODEL_LOADED:
        return _MODEL
    _MODEL_LOADED = True
    path = config.risk_model_path()
    if not path.exists():
        logger.warning("risk_model.missing path=%s message=Using documented fallback formula", path)
        return None
    import joblib

    _MODEL = joblib.load(path)
    logger.info("flow.risk_model.loaded path=%s", path)
    return _MODEL


def _fallback_probability(vector: list[float]) -> float:
    """Documented fallback when no model file exists: a fixed logistic formula
    over the same features, tuned to match the synthetic labeling rule."""
    ratio, buffer_ratio, variance, bnpl, cover, banks = vector
    z = (-2.2
         + 3.4 * (ratio / 100)
         - 2.8 * buffer_ratio
         + 0.12 * variance
         + 0.30 * bnpl
         - 0.22 * cover
         + 0.15 * banks)
    return round(1 / (1 + math.exp(-z)), 3)


def generate_training_data(n: int = 6000, seed: int = 7) -> tuple[list[list[float]], list[int]]:
    """Sample plausible feature vectors and label them with a noisy rule.

    SYNTHETIC DATA: the labeling rule encodes the same domain intuition as the
    fallback formula plus noise, so the trained model learns a smooth version
    of it. Replace with real repayment outcomes to make this model honest.
    """
    import random

    rng = random.Random(seed)
    features, labels = [], []
    for _ in range(n):
        vector = [
            rng.uniform(5, 95),        # obligation_ratio_peak
            rng.uniform(-0.5, 0.6),    # min_buffer_over_income
            rng.uniform(0, 8),         # salary_timing_variance_days
            rng.choice([0, 0, 0, 1, 1, 2, 2, 3, 4]),  # bnpl_count
            rng.uniform(0, 8),         # savings_cover_months
            rng.choice([1, 1, 2, 2, 3, 4]),           # banks_with_obligations
        ]
        probability = _fallback_probability(vector)
        noisy = min(max(probability + rng.gauss(0, 0.08), 0.0), 1.0)
        features.append(vector)
        labels.append(1 if rng.random() < noisy else 0)
    return features, labels


def train_and_save() -> None:
    """Train logistic regression on the synthetic set and persist with joblib."""
    import joblib
    from sklearn.linear_model import LogisticRegression

    features, labels = generate_training_data()
    model = LogisticRegression(max_iter=1000)
    model.fit(features, labels)
    path = config.risk_model_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    accuracy = model.score(features, labels)
    logger.info("flow.risk_model.trained path=%s train_accuracy=%.3f", path, accuracy)
    print(f"risk model saved to {path} (train accuracy {accuracy:.3f})")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_and_save()
