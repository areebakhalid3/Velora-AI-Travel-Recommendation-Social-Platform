from flask import Blueprint, request, jsonify, session
from db import get_pg, mongo_db
from datetime import datetime

budget = Blueprint("budget", __name__)

@budget.route("/budget", methods=["POST"])
def add_budget():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json()

    doc = {
        "user_id":     session["user_id"],
        "destination": data.get("destination"),
        "total":       data.get("total"),
        "currency":    data.get("currency", "PKR"),
        "items":       data.get("items", []),
        "created_at":  datetime.utcnow()
    }
    result   = mongo_db["budgets"].insert_one(doc)
    mongo_id = str(result.inserted_id)

    conn = get_pg()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO budgets (user_id, total_amount, currency, mongo_doc_id) VALUES (%s, %s, %s, %s)",
        (session["user_id"], data.get("total"), data.get("currency", "PKR"), mongo_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Budget saved", "id": mongo_id}), 201

@budget.route("/budget", methods=["GET"])
def get_budgets():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    docs = list(mongo_db["budgets"].find({"user_id": session["user_id"]}))
    for d in docs:
        d["_id"] = str(d["_id"])
    return jsonify(docs)