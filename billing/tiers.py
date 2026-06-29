TIERS = {
    "free": {"allowed_intents": ["DOC_CHU"], "quota_limit": 20},
    "standard": {"allowed_intents": ["DOC_CHU", "MO_TA_CANH"], "quota_limit": 200},
    "premium": {"allowed_intents": ["DOC_CHU", "MO_TA_CANH"], "quota_limit": 2000},
}

DEFAULT_TIER = "free"