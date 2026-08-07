"""Nạp danh sách serial mẫu vào device_catalog — mô phỏng dữ liệu nhà sản xuất cung cấp.
Chạy: python seed_catalog.py [đường dẫn db, mặc định billing_data.db]
"""
import sys

import models

SAMPLE_SERIALS = [
    "YE-DEMO-0001",
    "YE-DEMO-0002",
    "YE-DEMO-0003",
    "YE-DEMO-0004",
    "YE-DEMO-0005",
]


def seed(db_path):
    models.init_db(db_path)
    for serial in SAMPLE_SERIALS:
        models.add_catalog_serial(db_path, serial)
    return SAMPLE_SERIALS


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "billing_data.db"
    serials = seed(path)
    print(f"Đã nạp {len(serials)} serial vào {path}: {', '.join(serials)}")
