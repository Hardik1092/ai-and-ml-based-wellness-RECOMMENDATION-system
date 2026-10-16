def retrain(extra_rows=None, extra_labels=None, samples: int = 3000, force: bool = False) -> dict:
    return {
        'available': False, 'promoted': False,
        'reason': 'Feedback retraining requires independently reviewed labels and a frozen evaluation protocol. Use the explicit dataset experiment CLI; automatic promotion is disabled.',
        'feedback_rows': len(extra_rows or []),
    }
