import json
import os
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import neo4j, fall back to JSON if unavailable
try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False


class VendorGraph:
    """Singleton graph DB — uses Neo4j if available & connected, else falls back to JSON file."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
            cls._instance._use_neo4j = False
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # JSON fallback path
        self._db_path = os.path.join("app", "data", "fake_graph.json")
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._data = {"nodes": {}, "edges": []}
        self._load_json()

        # Try Neo4j
        if HAS_NEO4J:
            try:
                self._driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                self._driver.verify_connectivity()
                self._use_neo4j = True
                logger.info("Connected to Neo4j at %s", settings.neo4j_uri)
                self._ensure_constraints()
            except Exception as e:
                logger.warning("Neo4j unavailable (%s), using JSON fallback", e)
                self._driver = None
                self._use_neo4j = False

    # ── JSON helpers ──────────────────────────────────────────────────

    def _load_json(self):
        if os.path.exists(self._db_path):
            try:
                with open(self._db_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.error("Failed to load JSON graph: %s", e)

    def _save_json(self):
        try:
            with open(self._db_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save JSON graph: %s", e)

    # ── Neo4j helpers ─────────────────────────────────────────────────

    def _ensure_constraints(self):
        with self._driver.session() as s:
            s.run("CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vendor) REQUIRE v.id IS UNIQUE")

    def _run(self, query: str, **params):
        with self._driver.session() as s:
            return list(s.run(query, **params))

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    # ── WRITE: add_vendor ─────────────────────────────────────────────

    def add_vendor(self, vendor_id: str, name: str, risk_score: float, tier: str, vendor_type: str = "vendor"):
        risk_score = round(float(risk_score), 2)

        if self._use_neo4j:
            try:
                self._run(
                    """
                    MERGE (v:Vendor {id: $id})
                    SET v.name = $name, v.risk_score = $risk,
                        v.tier = $tier,  v.vendor_type = $vtype
                    """,
                    id=vendor_id, name=name, risk=risk_score,
                    tier=tier, vtype=vendor_type,
                )
            except Exception as e:
                logger.error("Neo4j add_vendor failed: %s", e)

        # Always update JSON too (keeps them in sync / as fallback)
        self._data["nodes"][vendor_id] = {
            "id": vendor_id, "name": name,
            "risk_score": risk_score, "tier": tier, "vendor_type": vendor_type,
        }
        self._save_json()

    # ── WRITE: add_dependency ─────────────────────────────────────────

    def add_dependency(self, vendor_id: str, depends_on_id: str, criticality: float = 1.0):
        if self._use_neo4j:
            try:
                self._run(
                    """
                    MATCH (a:Vendor {id: $src}), (b:Vendor {id: $tgt})
                    MERGE (a)-[r:DEPENDS_ON]->(b)
                    SET r.criticality = $crit
                    """,
                    src=vendor_id, tgt=depends_on_id, crit=criticality,
                )
            except Exception as e:
                logger.error("Neo4j add_dependency failed: %s", e)

        # JSON fallback
        for edge in self._data["edges"]:
            if edge["source"] == vendor_id and edge["target"] == depends_on_id:
                edge["criticality"] = criticality
                self._save_json()
                return
        self._data["edges"].append({
            "source": vendor_id, "target": depends_on_id, "criticality": criticality,
        })
        self._save_json()

    # ── WRITE: propagate_risk ─────────────────────────────────────────

    def propagate_risk(self, vendor_id: str, new_risk: float):
        if self._use_neo4j:
            try:
                self._run(
                    """
                    MATCH (v:Vendor {id: $id}) SET v.risk_score = $risk
                    WITH v
                    MATCH (dep:Vendor)-[:DEPENDS_ON]->(v)
                    SET dep.risk_score = toFloat(
                      CASE WHEN dep.risk_score + ($risk - 50)*0.2 > 100 THEN 100
                           WHEN dep.risk_score + ($risk - 50)*0.2 < 0   THEN 0
                           ELSE dep.risk_score + ($risk - 50)*0.2 END
                    )
                    """,
                    id=vendor_id, risk=new_risk,
                )
            except Exception as e:
                logger.error("Neo4j propagate_risk failed: %s", e)

        # JSON fallback
        if vendor_id in self._data["nodes"]:
            self._data["nodes"][vendor_id]["risk_score"] = new_risk
            for edge in self._data["edges"]:
                if edge["target"] == vendor_id:
                    dep_id = edge["source"]
                    if dep_id in self._data["nodes"]:
                        old = self._data["nodes"][dep_id]["risk_score"]
                        self._data["nodes"][dep_id]["risk_score"] = min(100, max(0, old + (new_risk - 50) * 0.2))
            self._save_json()

    # ── READ: get_all_vendors ─────────────────────────────────────────

    def get_all_vendors(self):
        if self._use_neo4j:
            try:
                rows = self._run("MATCH (v:Vendor) RETURN v")
                return [dict(r["v"]) for r in rows]
            except Exception as e:
                logger.error("Neo4j get_all_vendors failed: %s", e)
        return list(self._data["nodes"].values())

    # ── READ: get_vendor ──────────────────────────────────────────────

    def get_vendor(self, vendor_id: str):
        if self._use_neo4j:
            try:
                rows = self._run("MATCH (v:Vendor {id: $id}) RETURN v", id=vendor_id)
                if not rows:
                    return None
                vendor = dict(rows[0]["v"])
                subs = self._run(
                    "MATCH (v:Vendor {id: $id})-[:DEPENDS_ON]->(s:Vendor) RETURN s",
                    id=vendor_id,
                )
                vendor["subcontractors"] = [dict(r["s"]) for r in subs]
                return vendor
            except Exception as e:
                logger.error("Neo4j get_vendor failed: %s", e)

        # JSON fallback
        if vendor_id not in self._data["nodes"]:
            return None
        vendor = dict(self._data["nodes"][vendor_id])
        subs = []
        for edge in self._data["edges"]:
            if edge["source"] == vendor_id:
                dep_id = edge["target"]
                if dep_id in self._data["nodes"]:
                    subs.append(self._data["nodes"][dep_id])
        vendor["subcontractors"] = subs
        return vendor

    # ── READ: get_graph_elements ──────────────────────────────────────

    def get_graph_elements(self):
        if self._use_neo4j:
            try:
                nodes_raw = self._run("MATCH (v:Vendor) RETURN v")
                nodes = [
                    {"data": {
                        "id": dict(r["v"])["id"],
                        "label": dict(r["v"]).get("name", dict(r["v"])["id"]),
                        "risk_score": dict(r["v"]).get("risk_score", 0),
                        "tier": dict(r["v"]).get("tier", "low"),
                        "type": dict(r["v"]).get("vendor_type", "vendor"),
                    }}
                    for r in nodes_raw
                ]
                edges_raw = self._run(
                    "MATCH (a:Vendor)-[r:DEPENDS_ON]->(b:Vendor) "
                    "RETURN a.id AS src, b.id AS tgt, r.criticality AS crit"
                )
                edges = [
                    {"data": {"source": r["src"], "target": r["tgt"], "criticality": r["crit"] or 1.0}}
                    for r in edges_raw
                ]
                return {"nodes": nodes, "edges": edges}
            except Exception as e:
                logger.error("Neo4j get_graph_elements failed: %s", e)

        # JSON fallback
        nodes = []
        for n in self._data["nodes"].values():
            nodes.append({"data": {
                "id": n["id"], "label": n["name"],
                "risk_score": n["risk_score"], "tier": n["tier"],
                "type": n.get("vendor_type", "vendor"),
            }})
        edges = []
        for e in self._data["edges"]:
            if e["source"] in self._data["nodes"] and e["target"] in self._data["nodes"]:
                edges.append({"data": {
                    "source": e["source"], "target": e["target"],
                    "criticality": e["criticality"],
                }})
        return {"nodes": nodes, "edges": edges}