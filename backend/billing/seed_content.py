"""Nạp nội dung tĩnh do admin quản lý: nhóm cộng đồng, sự kiện, bài viết hướng dẫn/FAQ.
Khớp dữ liệu mẫu trong UI Analysis.md (Community §4.9, Support §4.16) để backend
và demo UI thống nhất. Chạy: python seed_content.py [đường dẫn db, mặc định billing_data.db]
"""
import sys

import models

GROUPS = [
    ("Người mới dùng kính", "Hỏi đáp và mẹo dùng kính Your Eyes cho người mới bắt đầu."),
    ("Mẹo sử dụng hàng ngày", "Chia sẻ kinh nghiệm dùng kính trong sinh hoạt hằng ngày."),
    ("Dành cho người thân", "Không gian cho người thân của người dùng kính Your Eyes."),
]

EVENTS = [
    ("Hướng dẫn sử dụng kính Your Eyes", "2026-08-01T09:00:00", "Trực tuyến qua Zoom"),
    ("Gặp mặt cộng đồng TP.HCM", "2026-08-03T14:00:00", "Q.1, TP.HCM"),
]

ARTICLES = [
    ("guide", "Hướng dẫn sử dụng", "Tìm hiểu cách sử dụng kính Your Eyes hiệu quả."),
    ("faq", "Câu hỏi thường gặp (FAQ)", "Giải đáp các thắc mắc phổ biến."),
]


def seed(db_path):
    models.init_db(db_path)
    for name, description in GROUPS:
        models.add_community_group(db_path, name, description)
    for title, event_time, location in EVENTS:
        models.add_community_event(db_path, title, event_time, location)
    for kind, title, body in ARTICLES:
        models.add_support_article(db_path, kind, title, body)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "billing_data.db"
    seed(path)
    print(f"Đã nạp {len(GROUPS)} nhóm, {len(EVENTS)} sự kiện, {len(ARTICLES)} bài viết vào {path}")
