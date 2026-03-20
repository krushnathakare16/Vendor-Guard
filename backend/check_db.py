from app.services.graph_db import VendorGraph
import json

graph = VendorGraph()
data = graph.get_graph_elements()

for node in data["nodes"]:
    print(node["data"]["label"], "->", node["data"]["type"])
    
graph.close()
