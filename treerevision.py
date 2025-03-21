def check_tree():
    from models.all_models import db, Query  # ✅ Importar aquí evita ciclos

    query = db.session.query(Query).filter_by(id=13).first()
    print("Graph Path:", query.graph.decode() if isinstance(query.graph, bytes) else query.graph)

check_tree()
