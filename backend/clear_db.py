from app.services.graph_db import VendorGraph

graph = VendorGraph()
with graph.driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")

print("Database completely cleared.")
graph.close()
