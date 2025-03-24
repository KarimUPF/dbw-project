from flask import Blueprint, request, jsonify, render_template, send_file, session
from flask_login import current_user
import subprocess
import csv
import io
import json  # Import for Flask session storage
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from Bio import SeqIO
from models.all_models import db, Protein, PTM, ProteinHasPTM, Organism, Query, History
from routes.jaccarddef import calculate_ptm_jaccard_with_window
import os
from flask import send_file
from Bio import AlignIO
from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor
from Bio import Phylo
from flask import jsonify
import json
from flask import current_app
from flask_login import login_required

ptm_comparator = Blueprint('ptm_comparator', __name__)

def run_blast(protein_id, session, selected_organisms=None):
    """
    Runs BLASTP to find the most similar proteins from MySQL.
    Filters results by organism if specified.
    """
    # ✅ Get the query protein
    protein = session.query(Protein).filter_by(accession_id=protein_id).first()
    if not protein:
        return []

    # ✅ Save query sequence to a file
    query_file = "query.fasta"
    with open(query_file, "w") as f:
        f.write(f">{protein.accession_id}\n{protein.sequence}\n")

    # ✅ Fetch organism IDs using Organism.id (instead of accession_id)
    organism_ids = []
    if selected_organisms:
        organism_ids = session.query(Organism.id).filter(
            Organism.scientific_name.in_(selected_organisms)
        ).all()
        organism_ids = [oid[0] for oid in organism_ids]  # Unpack tuples

        # 🔍 Debugging: Show selected organism names and IDs
        print(f"🔍 DEBUG: Selected organisms: {selected_organisms}")
        print(f"🔍 DEBUG: Resolved organism IDs: {organism_ids}")

    # ✅ Fetch proteins where `Protein.organism_id` matches `Organism.id`
    target_query = session.query(Protein)
    if organism_ids:
        target_query = target_query.filter(Protein.organism_id.in_(organism_ids))

    target_proteins = target_query.all()

    # 🔍 Debugging: Show the number of proteins found
    print(f"🔍 DEBUG: Number of proteins found: {len(target_proteins)}")

    # If no proteins were found, print a warning
    if not target_proteins:
        print("⚠️ WARNING: No proteins found for the selected organisms!")


    # ✅ Write proteins to a FASTA file
    blast_db_file = "temp_blast_db.fasta"
    with open(blast_db_file, "w") as f:
        for target_protein in target_proteins:
            if target_protein.sequence:
                f.write(f">{target_protein.accession_id}\n{target_protein.sequence}\n")

    # 🚨 Final safety check: Ensure the BLAST DB file is not empty
    if os.path.getsize(blast_db_file) == 0:
        raise RuntimeError("BLAST database file is empty. No valid protein sequences were written.")

    # ✅ Create the BLAST database
    subprocess.run(["makeblastdb", "-in", blast_db_file, "-dbtype", "prot"], check=True)

    # ✅ Run BLASTP against the temporary database
    blast_output = "blast_results.txt"
    subprocess.run([
        "blastp", "-query", query_file, "-db", blast_db_file,
        "-outfmt", "6 sseqid pident length evalue",
        "-max_target_seqs", "10",
        "-out", blast_output
    ], check=True)

    # ✅ Parse BLAST results
    hits = []
    with open(blast_output, "r") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            hits.append({
                "id": parts[0],
                "identity": float(parts[1]),
                "length": int(parts[2]),
                "evalue": float(parts[3])
            })

    # ✅ Sort by identity (descending) and e-value (ascending)
    hits.sort(key=lambda x: (-x["identity"], x["evalue"]))

    # ✅ Return the top 10 protein IDs
    return [hit["id"] for hit in hits[:10]]


def align_sequences(proteins):
    """Align proteins with Clustal Omega and generate distance-based tree."""
    fasta_file = "sequences.fasta"
    
    with open(fasta_file, "w") as f:
        for protein in proteins:
            if protein.sequence and protein.accession_id:
                f.write(f">{protein.accession_id}\n{protein.sequence}\n")
    
    if os.path.getsize(fasta_file) == 0:
        raise ValueError("No valid sequences were found in the proteins list")
    
    aligned_file = "aligned.fasta"
    
    result = subprocess.run(
        ["clustalo", "-i", fasta_file, "-o", aligned_file, "--force"], 
        capture_output=True,
        text=True,
        shell=False
    )
    
    if result.returncode != 0:
        print(f"Clustal Omega error: {result.stderr}")
        raise RuntimeError(f"Clustal Omega failed: {result.stderr}")
    
    # ✅ Generar árbol de distancias
    alignment = AlignIO.read(aligned_file, "fasta")
    calculator = DistanceCalculator('identity')
    distance_matrix = calculator.get_distance(alignment)
    # Construcción del árbol
    constructor = DistanceTreeConstructor()
    tree = constructor.nj(distance_matrix)

    # Crear carpeta si no existe
    os.makedirs("results/trees", exist_ok=True)
    tree_ids = "_".join(record.id for record in alignment)
    safe_ids = tree_ids[:50].replace(" ", "_")
    tree_file = f"results/trees/tree_{safe_ids}.nwk"

    # ✅ GUARDAR EL ÁRBOL EN FORMATO NEWICK COMPLETO Y CORRECTO
    from io import StringIO
    from Bio import Phylo

    handle = StringIO()
    Phylo.write(tree, handle, "newick")
    handle.seek(0)
    newick_str = handle.read().strip()

    # Asegurar que termina en punto y coma
    if not newick_str.endswith(";"):
        newick_str += ";"

    # Sobrescribir tree_file con el contenido correcto
    with open(tree_file, "w") as f:
        f.write(newick_str)

    # ✅ Ahora generar el HTML
    html_file = tree_file.replace(".nwk", ".html")
    generate_tree_html(tree_file, html_file)

    return aligned_file, tree_file


def convert_newick_to_json(nwk_path):
    """Convierte un árbol en formato Newick a JSON para D3.js, eliminando nodos internos sin nombre."""
    if not os.path.exists(nwk_path):
        print(f"⚠️ Archivo {nwk_path} no encontrado.")
        return None

    tree = Phylo.read(nwk_path, "newick")

    def parse_clade(clade):
        if not clade.name:  
            return {"children": [parse_clade(child) for child in clade.clades] if clade.clades else []}
        return {
            "name": clade.name,
            "children": [parse_clade(child) for child in clade.clades] if clade.clades else []
        }

    tree_json = parse_clade(tree.root)
    return json.dumps(tree_json)


def adjust_ptm_positions(sequences, ptm_dict):
    """Adjust PTM positions based on alignment gaps for all proteins."""
    adjusted_positions = {}
    alignment_length = len(next(iter(sequences.values())))

    for prot_id, aligned_seq in sequences.items():
        ptm_positions = ptm_dict.get(prot_id, {})
        new_positions = {}
        gap_count = 0

        for i, char in enumerate(aligned_seq):
            if char == "-":
                gap_count += 1
            else:
                original_pos = i - gap_count
                if original_pos in ptm_positions:
                    normalized_pos = i / alignment_length
                    new_positions[i] = {
                        "original_position": original_pos,
                        "new_position": i,
                        "normalized_position": round(normalized_pos, 3),
                        "type": ptm_positions[original_pos]["type"]
                    }

        adjusted_positions[prot_id] = new_positions

    return adjusted_positions


@ptm_comparator.route('/get_ptm_types')
def get_ptm_types():
    """Fetch all distinct PTM types from the database."""
    session_db = db.session
    ptm_types = session_db.query(PTM.type).distinct().all()
    session_db.close()
    return jsonify([ptm[0] for ptm in ptm_types])  # Convert to list

@ptm_comparator.route('/get_organisms')
def get_organisms():
    """Fetch all distinct scientific names from the database."""
    session_db = db.session
    organisms = session_db.query(Organism.scientific_name).distinct().all()
    session_db.close()
    return jsonify([org[0] for org in organisms])  # Convert to list

@ptm_comparator.route('/compare_ptms', methods=['GET', 'POST'])
def align_and_update_ptms():
    if request.method == 'POST':
        protein_ids = request.form.get('protein_id', '').split(',')
        protein_ids = [pid.strip() for pid in protein_ids]  
        selected_ptms = request.form.get('ptm_type', '').split(',')
        selected_organisms = request.form.get('organism', '').split(',')
        window_size = float(request.form.get('window', '0.05'))  

    else:  
        protein_ids = request.args.get('protein_id', '').split(',')
        selected_ptms = request.args.get('ptm_type', '').split(',')
        selected_organisms = request.args.get('organism', '').split(',')
        window_size = float(request.args.get('window', '0.05'))

    selected_ptms = None if selected_ptms == [''] else selected_ptms
    selected_organisms = None if selected_organisms == [''] else selected_organisms

    session_db = db.session  

    if len(protein_ids) == 1:
        protein_id = protein_ids[0]
        similar_proteins_ids = run_blast(protein_id, session_db, selected_organisms)

        proteins_to_align = session_db.query(Protein).filter(
            Protein.accession_id.in_(similar_proteins_ids)
        ).all()

        query_protein = session_db.query(Protein).filter_by(accession_id=protein_id).first()
        if query_protein and query_protein not in proteins_to_align:
            proteins_to_align.append(query_protein)
    else:
        query = session_db.query(Protein).filter(Protein.accession_id.in_(protein_ids))
        if selected_organisms:
            query = query.join(Organism).filter(Organism.scientific_name.in_(selected_organisms))
        proteins_to_align = query.all()

    if not proteins_to_align:
        return jsonify({"error": "No proteins found matching the criteria"}), 400

    # Alinear secuencias y generar árbol
    aligned_file, tree_file = align_sequences(proteins_to_align)
    sequences = {record.id: str(record.seq) for record in SeqIO.parse(aligned_file, "fasta")}

    ptm_dict = {}
    for p in proteins_to_align:
        ptms = session_db.query(ProteinHasPTM.position, PTM.type).join(PTM).filter(
            ProteinHasPTM.protein_accession_id == p.accession_id
        )

        if selected_ptms:
            ptms = ptms.filter(PTM.type.in_(selected_ptms))

        ptm_dict[p.accession_id] = {ptm.position: {"type": ptm.type} for ptm in ptms.all()}

    ptm_data = adjust_ptm_positions(sequences, ptm_dict)
    jaccard_indices = calculate_ptm_jaccard_with_window(ptm_data, sequences, window_size)

    formatted_jaccard_indices = {f"{k[0]}, {k[1]}": v for k, v in jaccard_indices.items()}

    # 🧹 Limpiar datos vacíos
    cleaned_proteins = [pid for pid in protein_ids if pid]
    cleaned_ptms = [ptm for ptm in selected_ptms] if selected_ptms else None
    cleaned_organisms = [org for org in selected_organisms] if selected_organisms else None

    parameters = {
        "protein_ids": cleaned_proteins if cleaned_proteins else None,
        "ptm_types": cleaned_ptms,
        "organism_filter": cleaned_organisms,
        "sequences": sequences,
        "ptm_data": ptm_data,
        "jaccard_indices": formatted_jaccard_indices,
        "window_size": window_size,
    }

    query = Query(parameters=parameters, summary_table=None, graph=tree_file)

    history = session_db.query(History).filter_by(user_id=current_user.id).first()
    if not history:
        history = History(user_id=current_user.id)
        session_db.add(history)
        session_db.commit()

    session_db.add(query)
    history.queries.append(query)
    session_db.commit()

    # ✅ Obtener JSON del árbol de forma correcta
    tree_json = get_tree_json(query.id).get_json()

    return render_template(
        "ptm_interactive.html", 
        sequences=sequences, 
        ptm_data=ptm_data,
        jaccard_indices=formatted_jaccard_indices,
        window_size=window_size,
        query=query,
        tree_json=json.dumps(tree_json)  
    )



@ptm_comparator.route('/download_fasta', methods=['GET'])
def download_fasta():
    fasta_file_path = "aligned.fasta"  
    return send_file(fasta_file_path, as_attachment=True, download_name="aligned.fasta")


def generate_tree(nwk_path):
    """Genera un archivo .html desde un .nwk y lo guarda en `results/trees/`."""
    if not os.path.exists(nwk_path):
        print(f"⚠️ Archivo {nwk_path} no encontrado.")
        return None

    print(f"📂 Cargando árbol desde {nwk_path}...")
    
    # ✅ Asegurar que el HTML se guarda en la carpeta correcta
    html_path = os.path.join("results/trees/", os.path.basename(nwk_path).replace(".nwk", ".html"))
    return generate_tree_html(nwk_path, html_path)


def generate_tree_html(tree_file, html_output=None):
    """Convierte un archivo .nwk en un .html visualizable y lo guarda en `results/trees/`."""
    if not os.path.exists(tree_file):
        print(f"⚠️ Archivo {tree_file} no encontrado.")
        return None

    # ✅ Crear carpeta `results/trees/` si no existe
    os.makedirs("results/trees/", exist_ok=True)

    # ✅ Asegurar que el HTML se guarda en la carpeta correcta
    if html_output is None:
        html_output = os.path.join("results/trees/", os.path.basename(tree_file).replace(".nwk", ".html"))

    try:
        tree = Tree(tree_file, format=1)  # Forzar lectura con nombres internos
        ts = TreeStyle()
        ts.show_leaf_name = True
        ts.scale = 20
        ts.title.add_face(TextFace("Árbol filogenético basado en distancias de alineamiento", fsize=12), column=0)

        tree.render(html_output, tree_style=ts)
        print(f"✅ Árbol convertido a HTML: {html_output}")
    except Exception as e:
        print(f"❌ Error al generar HTML: {e}")
        return None

    return html_output


@ptm_comparator.route('/get_tree_json/<query_id>')
def get_tree_json(query_id):
    """Convierte un archivo Newick en JSON para D3.js"""
    query = db.session.query(Query).filter_by(id=query_id).first()
    
    if not query or not query.graph:
        return jsonify({"error": "Árbol no encontrado"}), 404

    nwk_path = query.graph

    # Leer el árbol en formato Newick
    try:
        tree = Phylo.read(nwk_path, "newick")
    except Exception as e:
        return jsonify({"error": f"Error leyendo el archivo Newick: {str(e)}"}), 500

    # Convertir a JSON de forma recursiva
    def tree_to_dict(clade):
        return {
            "name": str(clade.name) if clade.name else "Internal",
            "children": [tree_to_dict(c) for c in clade.clades] if clade.clades else []
        }

    tree_json = tree_to_dict(tree.root)
    return jsonify(tree_json)


@ptm_comparator.route('/tree_view/<int:query_id>')
def tree_view(query_id):
    query = db.session.query(Query).filter_by(id=query_id).first()

    if not query or not query.graph:
        return "Árbol no disponible", 404

    nwk_path = query.graph

    # Ruta donde guardaremos el .nwk dentro de /static/trees/
    trees_dir = os.path.join("static", "trees")
    os.makedirs(trees_dir, exist_ok=True)

    nwk_filename = os.path.basename(nwk_path)
    static_tree_path = os.path.join(trees_dir, nwk_filename)

    # Si el archivo aún no está en /static/trees, lo copiamos allí
    if not os.path.exists(static_tree_path):
        from shutil import copyfile
        copyfile(nwk_path, static_tree_path)

    return render_template("tree_viewer.html", nwk_file=nwk_filename)

@ptm_comparator.route('/loading', methods=['POST'])
def show_loading_screen():
    form_data = request.form.to_dict()
    session['compare_form_data'] = form_data

    # Extraer info básica para validar
    protein_id = form_data.get("protein_id", "").strip()
    selected_organisms = form_data.get("organism", "").split(',')
    selected_organisms = [org for org in selected_organisms if org]

    session_db = db.session

    # Verificar si hay proteínas válidas
    if protein_id:
        protein = session_db.query(Protein).filter_by(accession_id=protein_id).first()
        if not protein:
            return render_template("no_results.html", message="Protein not found.")

        organism_ids = []
        if selected_organisms:
            organism_ids = session_db.query(Organism.id).filter(
                Organism.scientific_name.in_(selected_organisms)
            ).all()
            organism_ids = [oid[0] for oid in organism_ids]

        query = session_db.query(Protein)
        if organism_ids:
            query = query.filter(Protein.organism_id.in_(organism_ids))

        total_proteins = query.count()
        if total_proteins == 0:
            return render_template("no_results.html", message="No proteins found for selected organism(s).")

    return render_template('loading.html')



@ptm_comparator.route('/compare_async', methods=['POST'])
@login_required
def compare_async():
    form_data = session.get('compare_form_data')
    if not form_data:
        return jsonify({'error': 'No form data found'}), 400

    from flask import current_app
    with current_app.test_request_context(method='POST', data=form_data):
        return align_and_update_ptms()
