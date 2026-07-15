from dotenv import load_dotenv; load_dotenv()
from neo4j import GraphDatabase
import os
uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USERNAME')
pwd = os.getenv('NEO4J_PASSWORD')
driver = GraphDatabase.driver(uri, auth=(user, pwd))
with driver.session(database='neo4j') as s:
    r = s.run('MATCH (n) RETURN count(n) as total_nodes')
    print(f'Total nodes in Neo4j: {r.single()["total_nodes"]}')
    r = s.run('MATCH ()-[r]->() RETURN count(r) as total_rels')
    print(f'Total relationships: {r.single()["total_rels"]}')
    r = s.run('MATCH (d:Document) RETURN d.fileName as name, d.status as status')
    for rec in r:
        print(f'Document: {rec["name"]} | {rec["status"]}')
driver.close()
