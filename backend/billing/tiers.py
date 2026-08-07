TIERS = {
    "free": {"allowed_intents": ["DOC_CHU"], "quota_limit": 20},
    "basic": {"allowed_intents": ["DOC_CHU", "MO_TA_CANH"], "quota_limit": 200},
    "pro": {"allowed_intents": ["DOC_CHU", "MO_TA_CANH"], "quota_limit": 2000},
}

DEFAULT_TIER = "free"

# Giá bán theo tháng (VNĐ) — khớp UI Analysis.md mục 4.11 (Free/Basic/Pro).
# Giá năm = giá tháng x 12 (đã chốt, không tính khuyến mãi tháng đầu ở tầng backend).
PRICING = {
    "free": {"monthly": 0},
    "basic": {"monthly": 99000},
    "pro": {"monthly": 199000},
}


def get_price(tier, billing_cycle):
    if tier not in PRICING:
        raise ValueError(f"Không có giá cho tier '{tier}'")
    monthly = PRICING[tier]["monthly"]
    if billing_cycle == "monthly":
        return monthly
    if billing_cycle == "yearly":
        return monthly * 12
    raise ValueError("billing_cycle phải là 'monthly' hoặc 'yearly'")