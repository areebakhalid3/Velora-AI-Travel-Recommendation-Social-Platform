import os
import psycopg2
from pymongo import MongoClient
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def get_pg():
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASS"),
        sslmode=os.getenv("PG_SSLMODE", "require")   #new line, required by Neon
    )
    return conn

mongo_client = MongoClient(os.getenv("MONGO_URI"))
mongo_db     = mongo_client[os.getenv("MONGO_DB")]

neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASS"))
)

def run_cypher(query, params=None):
    with neo4j_driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]