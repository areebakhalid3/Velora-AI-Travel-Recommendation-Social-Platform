import os
from flask import Flask, render_template, request, jsonify, session
from db import get_pg, mongo_db, run_cypher
from routes.social import social
from routes.auth   import auth
from routes.posts  import posts
from routes.budget import budget
from routes.ai import ai_bp
import psycopg2.extras

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

app.register_blueprint(auth)
app.register_blueprint(posts)
app.register_blueprint(social)
app.register_blueprint(budget)
app.register_blueprint(ai_bp)

#Session Login
@app.route("/me")
def me():
    if "user_id" in session:
        return jsonify({
            "user_id":  session["user_id"],
            "username": session["username"]
        })
    return jsonify({"error": "Not logged in"}), 401

#DB Test Routes
@app.route("/test/pg")
def test_pg():
    try:
        conn = get_pg()
        cur  = conn.cursor()
        cur.execute("SELECT version();")
        v = cur.fetchone()[0]
        cur.close(); conn.close()
        return {"status": "PostgreSQL OK", "version": v}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/test/mongo")
def test_mongo():
    try:
        mongo_db["test"].insert_one({"ping": 1})
        return {"status": "MongoDB OK"}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/test/neo4j")
def test_neo4j():
    try:
        r = run_cypher("RETURN 'OK' AS msg")
        return {"status": "Neo4j " + r[0]["msg"]}
    except Exception as e:
        return {"error": str(e)}, 500

#HTML Page Routes
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login.html")
def login_page():
    return render_template("login.html")

@app.route("/register.html")
def register_page():
    return render_template("register.html")

@app.route("/home.html")
def home_page():
    return render_template("home.html")

@app.route("/index.html")
def index_page():
    return render_template("index.html")

@app.route("/create_post.html")
def create_post_page():
    return render_template("create_post.html")

@app.route("/budget.html")
def budget_page():
    return render_template("budget.html")

@app.route("/profile.html")
def profile_page():
    return render_template("profile.html")

@app.route("/trip-planner.html")
def trip_planner_page():
    return render_template("trip-planner.html")

@app.route("/map.html")
def map_page():
    return render_template("map.html")

#Profile Routes
@app.route("/profile/stats")
def profile_stats():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    conn  = get_pg()
    cur   = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM user_stats WHERE user_id = %s", (session["user_id"],))
    stats = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(dict(stats) if stats else {})

@app.route("/profile/posts")
def profile_posts():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    my_posts = list(mongo_db["posts"].find(
        {"author_id": session["user_id"]}
    ).sort("created_at", -1))
    for p in my_posts:
        p["_id"] = str(p["_id"])
    return jsonify(my_posts)

@app.route("/my-likes")
def my_likes():
    if "user_id" not in session:
        return jsonify([])
    conn = get_pg()
    cur  = conn.cursor()
    cur.execute("SELECT post_id FROM post_likes WHERE user_id = %s", (session["user_id"],))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([row[0] for row in rows])

#Search Routes
@app.route("/search/posts")
def search_posts():
    if "user_id" not in session:
        return jsonify([])
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    results = list(mongo_db["posts"].find({
        "$or": [
            {"title":            {"$regex": q, "$options": "i"}},
            {"body":             {"$regex": q, "$options": "i"}},
            {"tags":             {"$regex": q, "$options": "i"}},
            {"author_username":  {"$regex": q, "$options": "i"}}
        ]
    }).limit(20))
    for p in results:
        p["_id"] = str(p["_id"])
    return jsonify(results)

@app.route("/search/users")
def search_users():
    if "user_id" not in session:
        return jsonify([])
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    conn = get_pg()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT u.id, u.username, us.posts_count
        FROM users u
        LEFT JOIN user_stats us ON u.id = us.user_id
        WHERE u.username ILIKE %s AND u.id != %s
        LIMIT 20
    """, (f"%{q}%", session["user_id"]))
    users = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{
        "id":          str(u["id"]),
        "username":    u["username"],
        "posts_count": u["posts_count"] or 0
    } for u in users])

@app.route("/search/destinations")
def search_destinations():
    if "user_id" not in session:
        return jsonify([])
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    results = list(mongo_db["posts"].find({
        "$or": [
            {"destination.name":    {"$regex": q, "$options": "i"}},
            {"destination.country": {"$regex": q, "$options": "i"}}
        ]
    }).limit(20))
    for p in results:
        p["_id"] = str(p["_id"])
    return jsonify(results)

@app.route("/search.html")
def search_page():
    return render_template("search.html")

#main
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)