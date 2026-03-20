from neo4j import GraphDatabase
from app.core.config import settings

class VendorGraph:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def close(self):
        self.driver.close()

    def add_vendor(self, vendor_id: str, name: str, risk_score: float, tier: str, vendor_type: str = "vendor"):
        with self.driver.session() as session:
            session.run(
                "MERGE (v:Vendor {id: $id}) "
                "SET v.name = $name, v.risk_score = $risk_score, v.tier = $tier, v.vendor_type = $vendor_type",
                id=vendor_id, name=name, risk_score=risk_score, tier=tier, vendor_type=vendor_type
            )

    def add_dependency(self, vendor_id: str, depends_on_id: str, criticality: float = 1.0):
        with self.driver.session() as session:
            session.run(
                "MATCH (v:Vendor {id: $vid}) "
                "MATCH (d:Vendor {id: $did}) "
                "MERGE (v)-[:DEPENDS_ON {criticality: $crit}]->(d)",
                vid=vendor_id, did=depends_on_id, crit=criticality
            )

    def propagate_risk(self, vendor_id: str, new_risk: float):
        """Update vendor risk and propagate to dependents."""
        with self.driver.session() as session:
            # Update the vendor itself
            session.run(
                "MATCH (v:Vendor {id: $id}) SET v.risk_score = $risk",
                id=vendor_id, risk=new_risk
            )
            # Find all vendors that depend on this one
            result = session.run(
                "MATCH (dep:Vendor)-[:DEPENDS_ON]->(v:Vendor {id: $id}) "
                "RETURN dep.id AS dep_id, dep.risk_score AS old_score",
                id=vendor_id
            )
            for record in result:
                dep_id = record["dep_id"]
                old = record["old_score"]
                # Simple propagation: 20% of the delta passes through
                delta = (new_risk - 50) * 0.2
                new_dep = min(100, old + delta)
                session.run(
                    "MATCH (dep:Vendor {id: $did}) SET dep.risk_score = $score",
                    did=dep_id, score=new_dep
                )

    def get_all_vendors(self):
        with self.driver.session() as session:
            result = session.run("MATCH (v:Vendor) RETURN v.id AS id, v.name AS name, v.risk_score AS risk_score, v.tier AS tier")
            return [dict(record) for record in result]

    def get_vendor(self, vendor_id: str):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (v:Vendor {id: $id}) "
                "OPTIONAL MATCH (v)-[:DEPENDS_ON]->(dep:Vendor) "
                "RETURN v.id AS id, v.name AS name, v.risk_score AS risk_score, v.tier AS tier, "
                "collect({id: dep.id, name: dep.name, risk_score: dep.risk_score, tier: dep.tier}) AS subcontractors",
                id=vendor_id
            )
            record = result.single()
            if record and record["id"]:
                data = dict(record)
                # Filter out null subcontractors if collect returned [{id: null, ...}]
                data["subcontractors"] = [sub for sub in data["subcontractors"] if sub.get("id")]
                return data
            return None

    def get_graph_elements(self):
        with self.driver.session() as session:
            result = session.run("MATCH (n:Vendor) OPTIONAL MATCH (n)-[r:DEPENDS_ON]->(m:Vendor) RETURN n, r, m")
            nodes = {}
            edges = []
            for record in result:
                n = record["n"]
                if n and n["id"] not in nodes:
                    nodes[n["id"]] = {
                        "data": {
                            "id": n["id"],
                            "label": n["name"],
                            "risk_score": n["risk_score"],
                            "tier": n["tier"],
                            "type": n.get("vendor_type", "vendor")
                        }
                    }
                m = record["m"]
                if m and m["id"] not in nodes:
                    nodes[m["id"]] = {
                        "data": {
                            "id": m["id"],
                            "label": m["name"],
                            "risk_score": m["risk_score"],
                            "tier": m["tier"],
                            "type": m.get("vendor_type", "vendor")
                        }
                    }
                r = record["r"]
                if r and n and m:
                    edges.append({
                        "data": {
                            "source": n["id"],
                            "target": m["id"],
                            "criticality": r.get("criticality", 1.0)
                        }
                    })
            return {"nodes": list(nodes.values()), "edges": edges}