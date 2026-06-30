import os

from flask import Flask, jsonify, request

import models

app = Flask(__name__)


def get_db_path():
    path = os.environ.get("BILLING_DB_PATH", "billing_data.db")
    if not os.path.exists(path):
        models.init_db(path)
    return path


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/accounts/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "Thiếu email."}), 400
    db_path = get_db_path()
    try:
        account_id = models.create_account(db_path, email)
    except ValueError:
        return jsonify({"error": "Email đã được đăng ký."}), 409
    return jsonify({"account_id": account_id, "token": account_id}), 201


@app.route("/accounts/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "Thiếu email."}), 400
    db_path = get_db_path()
    account = models.get_account_by_email(db_path, email)
    if not account:
        return jsonify({"error": "Không tìm thấy tài khoản."}), 404
    return jsonify({"account_id": account["id"], "token": account["id"]}), 200


@app.route("/accounts/<account_id>/devices", methods=["POST"])
def pair_device(account_id):
    db_path = get_db_path()
    device_id = models.create_device(db_path, account_id)
    if device_id is None:
        return jsonify({"error": "Không tìm thấy tài khoản."}), 404
    return jsonify({"device_id": device_id}), 201


if __name__ == "__main__":
    get_db_path()
    port = int(os.environ.get("PORT", 5005))
    app.run(host="0.0.0.0", port=port)
