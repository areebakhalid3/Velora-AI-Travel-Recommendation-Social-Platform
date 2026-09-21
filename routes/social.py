#libraries

from flask import Blueprint, request, jsonify, session
from db import get_pg, run_cypher
import psycopg2.extras

social = Blueprint("social", __name__)

# Follow function
@social.route("/follow/<target_id>", methods=["POST"])
def follow(target_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    my_id = session["user_id"]
    if my_id == target_id:
        return jsonify({"error": "Cannot follow yourself"}), 400

    already = run_cypher(
        "MATCH (a:User {id:$me})-[r:FOLLOWS]->(b:User {id:$them}) RETURN r",
        {"me": my_id, "them": target_id}
    )

    if already:
        return jsonify({"message": "Already following"}), 200

    run_cypher(
        "MATCH (a:User {id:$me}), (b:User {id:$them}) MERGE (a)-[:FOLLOWS]->(b)",
        {"me": my_id, "them": target_id}
    )

    conn = get_pg()
    cur  = conn.cursor()
    cur.execute("UPDATE user_stats SET following_count = following_count+1 WHERE user_id=%s", (my_id,))
    cur.execute("UPDATE user_stats SET followers_count = followers_count+1 WHERE user_id=%s", (target_id,))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Followed successfully"})

# Unfollow function
@social.route("/unfollow/<target_id>", methods=["POST"])
def unfollow(target_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    my_id = session["user_id"]
    run_cypher(
        "MATCH (a:User {id:$me})-[r:FOLLOWS]->(b:User {id:$them}) DELETE r",
        {"me": my_id, "them": target_id}
    )

    conn = get_pg()
    cur  = conn.cursor()
    cur.execute("UPDATE user_stats SET following_count = following_count-1 WHERE user_id=%s", (my_id,))
    cur.execute("UPDATE user_stats SET followers_count = followers_count-1 WHERE user_id=%s", (target_id,))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Unfollowed"})

#following list
@social.route("/following", methods=["GET"])
def get_following():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    results = run_cypher("""
        MATCH (me:User {id:$id})-[:FOLLOWS]->(other:User)
        RETURN other.id AS id, other.username AS username
    """, {"id": session["user_id"]})

    return jsonify(results)

#followers list
@social.route("/followers", methods=["GET"])
def get_followers():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    results = run_cypher("""
        MATCH (other:User)-[:FOLLOWS]->(me:User {id:$id})
        RETURN other.id AS id, other.username AS username
    """, {"id": session["user_id"]})

    return jsonify(results)

#Friend suggestions
@social.route("/suggestions", methods=["GET"])
def suggestions():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    results = run_cypher("""
        MATCH (me:User {id:$id})-[:FOLLOWS]->(friend)-[:FOLLOWS]->(suggested:User)
        WHERE NOT (me)-[:FOLLOWS]->(suggested) AND suggested.id <> $id
        RETURN suggested.id AS id, suggested.username AS username,
               COUNT(friend) AS mutual
        ORDER BY mutual DESC LIMIT 10
    """, {"id": session["user_id"]})

    return jsonify(results)

#Get all users
@social.route("/users", methods=["GET"])
def get_users():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    conn = get_pg()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, username FROM users WHERE id != %s",
        (session["user_id"],)
    )
    users = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([{"id": str(u["id"]), "username": u["username"]} for u in users])

#BFS User Search
@social.route("/search/graph/users", methods=["GET"])
def bfs_user_search():
    if "user_id" not in session:
        return jsonify([])

    q     = request.args.get("q", "").strip().lower()
    my_id = session["user_id"]

    if not q:
        return jsonify([])

    graph_results = run_cypher("""
        MATCH (me:User {id: $id})
        MATCH (u:User)
        WHERE toLower(u.username) CONTAINS $q
        AND u.id <> $id
        WITH me, u,
             CASE
                 WHEN (me)-[:FOLLOWS]->(u) THEN 1
                 WHEN (me)-[:FOLLOWS]->()-[:FOLLOWS]->(u) THEN 2
                 WHEN (me)-[:FOLLOWS]->()-[:FOLLOWS]->()-[:FOLLOWS]->(u) THEN 3
                 ELSE 99
             END AS social_distance
        RETURN u.id       AS id,
               u.username AS username,
               social_distance
        ORDER BY social_distance ASC
        LIMIT 20
    """, {"id": my_id, "q": q})

    return jsonify(graph_results)

#DFS Destination Search
@social.route("/search/graph/destinations", methods=["GET"])
def dfs_destination_search():
    if "user_id" not in session:
        return jsonify([])

    q     = request.args.get("q", "").strip().lower()
    my_id = session["user_id"]

    if not q:
        return jsonify([])

    results = run_cypher("""
        MATCH (me:User {id: $id})
        OPTIONAL MATCH (u1:User)-[:VISITED]->(p1:Place)
        WHERE toLower(p1.name) CONTAINS $q
        WITH me, COLLECT(DISTINCT {
            name: p1.name,
            country: p1.country,
            depth: 1,
            via: u1.username
        }) AS level1
        OPTIONAL MATCH (u2:User)-[:VISITED]->(p2:Place)
        WHERE toLower(p2.name) CONTAINS $q
        OPTIONAL MATCH (u2)-[:VISITED]->(related:Place)
        WHERE related.name <> p2.name
        WITH level1, COLLECT(DISTINCT {
            name: related.name,
            country: related.country,
            depth: 2,
            via: u2.username
        }) AS level2
        WITH level1 + level2 AS all_results
        UNWIND all_results AS r
        WITH r WHERE r.name IS NOT NULL
        RETURN DISTINCT r.name    AS name,
                        r.country AS country,
                        r.depth   AS depth,
                        r.via     AS discovered_via
        ORDER BY depth ASC, name ASC
        LIMIT 20
    """, {"id": my_id, "q": q})

    return jsonify(results)

#BFS Connection Search 
@social.route("/search/graph/connections", methods=["GET"])
def bfs_connection_search():
    if "user_id" not in session:
        return jsonify({"following": [], "followers": []})

    q     = request.args.get("q", "").strip().lower()
    my_id = session["user_id"]

    following = run_cypher("""
        MATCH (me:User {id:$id})-[:FOLLOWS]->(u:User)
        WHERE $q = '' OR toLower(u.username) CONTAINS $q
        RETURN u.id AS id, u.username AS username, 1 AS level
        ORDER BY u.username ASC
    """, {"id": my_id, "q": q})

    followers = run_cypher("""
        MATCH (u:User)-[:FOLLOWS]->(me:User {id:$id})
        WHERE $q = '' OR toLower(u.username) CONTAINS $q
        RETURN u.id AS id, u.username AS username, 1 AS level
        ORDER BY u.username ASC
    """, {"id": my_id, "q": q})

    mutual = run_cypher("""
        MATCH (me:User {id:$id})-[:FOLLOWS]->(u:User)-[:FOLLOWS]->(me)
        WHERE $q = '' OR toLower(u.username) CONTAINS $q
        RETURN u.id AS id, u.username AS username, 2 AS level
        ORDER BY u.username ASC
    """, {"id": my_id, "q": q})

    return jsonify({
        "following": following,
        "followers": followers,
        "mutual":    mutual
    })

#A* Suggestions 
@social.route("/search/graph/suggestions", methods=["GET"])
def astar_suggestions():
    if "user_id" not in session:
        return jsonify([])

    q     = request.args.get("q", "").strip().lower()
    my_id = session["user_id"]

    results = run_cypher("""
        MATCH (me:User {id:$id})
        MATCH (me)-[:FOLLOWS]->(friend:User)-[:FOLLOWS]->(candidate:User)
        WHERE NOT (me)-[:FOLLOWS]->(candidate)
        AND candidate.id <> $id
        AND ($q = '' OR toLower(candidate.username) CONTAINS $q)
        WITH me, candidate, COUNT(DISTINCT friend) AS mutual_follows
        OPTIONAL MATCH (me)-[:VISITED]->(place:Place)<-[:VISITED]-(candidate)
        WITH candidate, mutual_follows,
             COUNT(DISTINCT place) AS shared_places,
             (mutual_follows * 2 + COUNT(DISTINCT place) * 3) AS score
        RETURN candidate.id       AS id,
               candidate.username AS username,
               mutual_follows,
               shared_places,
               score
        ORDER BY score DESC
        LIMIT 15
    """, {"id": my_id, "q": q})

    return jsonify(results)

#Place Recommendations
@social.route("/suggestions/places", methods=["GET"])
def place_suggestions():
    if "user_id" not in session:
        return jsonify([])

    my_id = session["user_id"]

    results = run_cypher("""
        MATCH (me:User {id:$id})-[:VISITED]->(myPlace:Place)
              <-[:VISITED]-(similar:User)-[:VISITED]->(rec:Place)
        WHERE NOT (me)-[:VISITED]->(rec)
        AND rec.name <> myPlace.name
        RETURN rec.name    AS name,
               rec.country AS country,
               COUNT(DISTINCT similar) AS score
        ORDER BY score DESC
        LIMIT 10
    """, {"id": my_id})

    if not results:
        results = run_cypher("""
            MATCH (p:Place)
            WHERE NOT (:User {id:$id})-[:VISITED]->(p)
            RETURN p.name    AS name,
                   p.country AS country,
                   0         AS score
            LIMIT 10
        """, {"id": my_id})

    return jsonify(results)