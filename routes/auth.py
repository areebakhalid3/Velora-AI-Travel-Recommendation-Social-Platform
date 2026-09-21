from flask import Blueprint, request, jsonify, session
import psycopg2.extras
from db import get_pg, run_cypher
import hashlib

auth = Blueprint("auth", __name__)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@auth.route("/register", methods=["POST"])
def register():
    data     = request.get_json()
    username = data.get("username")
    email    = data.get("email")
    password = hash_password(data.get("password"))

    try:
        conn = get_pg()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (username, email, password)
        )
        user_id = str(cur.fetchone()["id"])
        cur.execute("INSERT INTO user_stats (user_id) VALUES (%s)", (user_id,))
        conn.commit()
        cur.close()
        conn.close()

        run_cypher(
            "CREATE (:User {id: $id, username: $username})",
            {"id": user_id, "username": username}
        )

        return jsonify({"message": "Registered successfully", "user_id": user_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    email    = data.get("email")
    password = hash_password(data.get("password"))

    try:
        conn = get_pg()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, username FROM users WHERE email=%s AND password_hash=%s",
            (email, password)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["user_id"]  = str(user["id"])
            session["username"] = user["username"]
            return jsonify({"message": "Logged in", "username": user["username"]})
        else:
            return jsonify({"error": "Wrong email or password"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})