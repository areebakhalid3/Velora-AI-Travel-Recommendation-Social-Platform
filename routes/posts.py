from flask import Blueprint, request, jsonify, session
from db import get_pg, mongo_db
from bson import ObjectId
from datetime import datetime
import os
from werkzeug.utils import secure_filename

posts = Blueprint("posts", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def get_upload_folder():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder = os.path.join(base, "static", "uploads")
    os.makedirs(folder, exist_ok=True)
    return folder

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Create post
@posts.route("/posts", methods=["POST"])
def create_post():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    photo_url = None

    # Check if request has a file 
    if "photo" in request.files:
        file = request.files["photo"]
        if file and file.filename != "" and allowed_file(file.filename):
            filename  = secure_filename(file.filename)
            timestamp = str(int(datetime.utcnow().timestamp()))
            filename  = timestamp + "_" + filename
            upload_folder = get_upload_folder()
            file.save(os.path.join(upload_folder, filename))
            photo_url = "/static/uploads/" + filename

        title       = request.form.get("title", "")
        destination = request.form.get("destination", "")
        country     = request.form.get("country", "")
        body        = request.form.get("body", "")
        budget      = request.form.get("budget", "")
        currency    = request.form.get("currency", "PKR")
        tags_raw    = request.form.get("tags", "")
        tags        = [t.strip() for t in tags_raw.split(",") if t.strip()]

    else:
        # ── No file — read as JSON 
        data        = request.get_json(force=True)
        title       = data.get("title", "")
        destination = data.get("destination", "")
        country     = data.get("country", "")
        body        = data.get("body", "")
        budget      = data.get("budget", "")
        currency    = data.get("currency", "PKR")
        tags        = data.get("tags", [])

    post_doc = {
        "author_id":       session["user_id"],
        "author_username": session["username"],
        "title":           title,
        "body":            body,
        "destination": {
            "name":    destination,
            "country": country
        },
        "budget_breakdown": {
            "total":    budget,
            "currency": currency
        },
        "photo_url":  photo_url,
        "tags":       tags,
        "comments":   [],
        "created_at": datetime.utcnow()
    }

    result  = mongo_db["posts"].insert_one(post_doc)
    post_id = str(result.inserted_id)

    conn = get_pg()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE user_stats SET posts_count = posts_count + 1 WHERE user_id = %s",
        (session["user_id"],)
    )
    conn.commit()
    cur.close()
    conn.close()

    # Auto-create Place node in Neo4j and VISITED relationship
    if destination and destination.strip():
        from db import run_cypher
        place_id = "place_" + destination.lower().replace(" ", "_")
        run_cypher("""
            MERGE (p:Place {id: $place_id})
            ON CREATE SET p.name    = $name,
                          p.country = $country
            WITH p
            MATCH (u:User {id: $user_id})
            MERGE (u)-[:VISITED {date: $date}]->(p)
        """, {
            "place_id": place_id,
            "name":     destination,
            "country":  country or "",
            "user_id":  session["user_id"],
            "date":     datetime.utcnow().strftime("%Y-%m")
        })

    return jsonify({"message": "Post created", "post_id": post_id}), 201

# Get all posts 
@posts.route("/posts", methods=["GET"])
def get_posts():
    all_posts = list(
        mongo_db["posts"].find().sort("created_at", -1).limit(20)
    )
    for p in all_posts:
        p["_id"] = str(p["_id"])
    return jsonify(all_posts)

#Get single post 
@posts.route("/posts/<post_id>", methods=["GET"])
def get_post(post_id):
    post = mongo_db["posts"].find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"error": "Post not found"}), 404
    post["_id"] = str(post["_id"])
    return jsonify(post)

#Edit post 
@posts.route("/posts/<post_id>", methods=["PUT"])
def edit_post(post_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    post = mongo_db["posts"].find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"error": "Post not found"}), 404
    if post["author_id"] != session["user_id"]:
        return jsonify({"error": "Not allowed"}), 403

    photo_url = post.get("photo_url")

    if "photo" in request.files:
        file = request.files["photo"]
        if file and file.filename != "" and allowed_file(file.filename):
            filename      = secure_filename(file.filename)
            timestamp     = str(int(datetime.utcnow().timestamp()))
            filename      = timestamp + "_" + filename
            upload_folder = get_upload_folder()
            file.save(os.path.join(upload_folder, filename))
            photo_url = "/static/uploads/" + filename

        title       = request.form.get("title", "")
        destination = request.form.get("destination", "")
        country     = request.form.get("country", "")
        body        = request.form.get("body", "")
        budget      = request.form.get("budget", "")
        currency    = request.form.get("currency", "PKR")
        tags_raw    = request.form.get("tags", "")
        tags        = [t.strip() for t in tags_raw.split(",") if t.strip()]
    else:
        data        = request.get_json(force=True)
        title       = data.get("title", "")
        destination = data.get("destination", "")
        country     = data.get("country", "")
        body        = data.get("body", "")
        budget      = data.get("budget", "")
        currency    = data.get("currency", "PKR")
        tags        = data.get("tags", [])

    mongo_db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {
            "title":            title,
            "body":             body,
            "destination":      {"name": destination, "country": country},
            "budget_breakdown": {"total": budget, "currency": currency},
            "photo_url":        photo_url,
            "tags":             tags,
            "updated_at":       datetime.utcnow()
        }}
    )
    return jsonify({"message": "Post updated"})

#Delete post
@posts.route("/posts/<post_id>", methods=["DELETE"])
def delete_post(post_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    post = mongo_db["posts"].find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"error": "Post not found"}), 404
    if post["author_id"] != session["user_id"]:
        return jsonify({"error": "Not allowed"}), 403

    # Delete photo file if exists
    if post.get("photo_url"):
        file_path = post["photo_url"].lstrip("/")
        if os.path.exists(file_path):
            os.remove(file_path)

    mongo_db["posts"].delete_one({"_id": ObjectId(post_id)})

    conn = get_pg()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE user_stats SET posts_count = posts_count - 1 WHERE user_id = %s",
        (session["user_id"],)
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Post deleted"})

#Like post
@posts.route("/posts/<post_id>/like", methods=["POST"])
def like_post(post_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    try:
        conn = get_pg()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO post_likes (post_id, user_id) VALUES (%s, %s)",
            (post_id, session["user_id"])
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Liked"})
    except Exception as e:
        return jsonify({"error": "Already liked"}), 400

#Add comment
@posts.route("/posts/<post_id>/comment", methods=["POST"])
def add_comment(post_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    data    = request.get_json()
    comment = {
        "_id":        str(ObjectId()),
        "user_id":    session["user_id"],
        "username":   session["username"],
        "text":       data.get("text"),
        "created_at": datetime.utcnow().isoformat(),
        "replies":    []
    }

    mongo_db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$push": {"comments": comment}}
    )
    return jsonify({"message": "Comment added"})

@posts.route("/posts/<post_id>/unlike", methods=["POST"])
def unlike_post(post_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    conn = get_pg()
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM post_likes WHERE post_id = %s AND user_id = %s",
        (post_id, session["user_id"])
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Unliked"})