from app.services.graph_db import VendorGraph

graph = VendorGraph()

with graph.driver.session() as session:
    # Find Amazon and Microsoft
    # Set Microsoft to subvendor
    session.run("""
        MATCH (m:Vendor) WHERE toLower(m.name) CONTAINS 'microsoft'
        SET m.vendor_type = 'subvendor'
    """)
    # Set Amazon to vendor
    session.run("""
        MATCH (a:Vendor) WHERE toLower(a.name) CONTAINS 'amazon' AND NOT toLower(a.name) CONTAINS 'web services'
        SET a.vendor_type = 'vendor'
    """)
    # Link Amazon to Microsoft
    session.run("""
        MATCH (a:Vendor), (m:Vendor)
        WHERE toLower(a.name) CONTAINS 'amazon' AND NOT toLower(a.name) CONTAINS 'web services'
        AND toLower(m.name) CONTAINS 'microsoft'
        MERGE (a)-[:DEPENDS_ON {criticality: 1.0}]->(m)
    """)
    
    # Do similar for Apple and Intel just in case
    session.run("""
        MATCH (i:Vendor) WHERE toLower(i.name) CONTAINS 'intel'
        SET i.vendor_type = 'subvendor'
    """)
    session.run("""
        MATCH (a:Vendor) WHERE toLower(a.name) CONTAINS 'apple'
        SET a.vendor_type = 'vendor'
    """)
    session.run("""
        MATCH (app:Vendor), (i:Vendor)
        WHERE toLower(app.name) CONTAINS 'apple'
        AND toLower(i.name) CONTAINS 'intel'
        MERGE (app)-[:DEPENDS_ON {criticality: 0.8}]->(i)
    """)

print("Manual entries updated and linked successfully!")
graph.close()
