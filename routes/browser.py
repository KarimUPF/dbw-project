from flask import Blueprint, request, jsonify, render_template, send_file, session
import subprocess
import csv
import io
import json  # Import for Flask session storage
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from Bio import SeqIO
from Bio.Align.Applications import ClustalOmegaCommandline
from models.all_models import db, Protein, PTM, ProteinHasPTM
from routes.jaccarddef import calculate_ptm_jaccard_with_window



ptm_comparator = Blueprint('ptm_comparator', __name__)

def run_blast(protein_id, session):
    """Run BLASTP to find the 10 most similar proteins from MySQL."""
    protein = session.query(Protein).filter_by(accession_id=protein_id).first()
    if not protein:
        return []

    query_file = "query.fasta"
    with open(query_file, "w") as f:
        f.write(f">{protein.accession_id}\n{protein.sequence}\n")

    blast_output = "blast_results.txt"
    subprocess.run([
        "blastp", "-query", query_file, "-db", "my_protein_db",
        "-outfmt", "6 sseqid pident length evalue",
        "-max_target_seqs", "10",
        "-out", blast_output
    ], check=True)

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

    hits.sort(key=lambda x: (-x["identity"], x["evalue"]))
    return [hit["id"] for hit in hits[:10]]

def align_sequences(proteins):
    """Perform multiple sequence alignment with Clustal Omega."""
    fasta_file = "sequences.fasta"
    
    with open(fasta_file, "w") as f:
        for protein in proteins:
            f.write(f">{protein.accession_id}\n{protein.sequence}\n")

    aligned_file = "aligned.fasta"
    clustal_cline = ClustalOmegaCommandline(infile=fasta_file, outfile=aligned_file, force=True, verbose=True, auto=True)
    subprocess.run(str(clustal_cline), shell=True)

    return aligned_file

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

def generate_jaccard_csv(jaccard_indices):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Protein 1", "Protein 2", "Jaccard Index"])
    
    for (prot1, prot2), score in jaccard_indices.items():
        writer.writerow([prot1, prot2, round(score, 3)])
        
    return output.getvalue()

def generate_heatmap_png(jaccard_indices, protein_ids):
    plt.figure(figsize=(10, 8))
    matrix = np.zeros((len(protein_ids), len(protein_ids)))
    
    for i, p1 in enumerate(protein_ids):
        for j, p2 in enumerate(protein_ids):
            if i == j:
                matrix[i,j] = 1.0
            else:
                key = (p1, p2) if (p1, p2) in jaccard_indices else (p2, p1)
                matrix[i,j] = jaccard_indices.get(key, 0)
    
    sns.heatmap(matrix, xticklabels=protein_ids, yticklabels=protein_ids, 
                cmap='YlOrRd', annot=True, fmt='.2f')
    plt.title('Jaccard Similarity Heatmap')
    
    img_data = io.BytesIO()
    plt.savefig(img_data, format='png', bbox_inches='tight')
    img_data.seek(0)
    plt.close()
    
    return img_data


@ptm_comparator.route('/compare_ptms', methods=['POST'])
def align_and_update_ptms():
    """Align proteins and return PTM positions for interactive visualization."""
    protein_ids = request.form.get('protein_id', '').split(',')
    protein_ids = [pid.strip() for pid in protein_ids]  # Strip whitespace
    print(f"🔍 Received Protein IDs: {protein_ids}")  # Debugging

    if not protein_ids:
        return jsonify({"error": "No protein IDs provided"}), 400

    session_db = db.session  # SQLAlchemy session

    # Check if only one protein ID is provided
    if len(protein_ids) == 1:
        protein_id = protein_ids[0]
        similar_proteins_ids = run_blast(protein_id, session_db)
        protein_ids += similar_proteins_ids
        print(f"📌 Running BLAST, IDs after BLAST: {protein_ids}")  # Debugging

    # Query the database for the provided protein IDs
    proteins_to_align = session_db.query(Protein).filter(
        Protein.accession_id.in_(list(protein_ids))
    ).all()

    # Debugging: Print the results of the query
    print(f"✅ Proteins Found in DB: {[p.accession_id for p in proteins_to_align]}")  # Debugging

    if not proteins_to_align:
        return jsonify({"error": "No proteins found"}), 400

    aligned_file = align_sequences(proteins_to_align)
    sequences = {record.id: str(record.seq) for record in SeqIO.parse(aligned_file, "fasta")}

    ptm_dict = {p.accession_id: {ptm.position: {"type": ptm.type} for ptm in session_db.query(ProteinHasPTM.position, PTM.type).join(PTM).filter(
        ProteinHasPTM.protein_accession_id == p.accession_id).all()} for p in proteins_to_align}

    ptm_data = adjust_ptm_positions(sequences, ptm_dict)
    
    jaccard_indices = calculate_ptm_jaccard_with_window(ptm_data, sequences)

    # Store data in Flask session (not SQLAlchemy session)
    session['jaccard_indices'] = json.dumps({f"{k[0]}-{k[1]}": v for k, v in jaccard_indices.items()})
    session['ptm_data'] = json.dumps(ptm_data)
    session['sequences'] = json.dumps(sequences)

    session_db.close()

    return render_template(
        "ptm_interactive.html", 
        sequences=sequences, 
        ptm_data=ptm_data,
        jaccard_indices=jaccard_indices  # Pass to template if needed
    )


@ptm_comparator.route('/download_csv')
def download_csv():
    jaccard_indices = json.loads(session.get('jaccard_indices', '{}'))
    jaccard_indices = {(k.split('-')[0], k.split('-')[1]): v for k, v in jaccard_indices.items()}  # Convert keys back to tuples
    csv_data = generate_jaccard_csv(jaccard_indices)
    return send_file(io.BytesIO(csv_data.encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='jaccard_indices.csv')

@ptm_comparator.route('/download_heatmap')
def download_heatmap():
    jaccard_indices = json.loads(session.get('jaccard_indices', '{}'))
    jaccard_indices = {(k.split('-')[0], k.split('-')[1]): v for k, v in jaccard_indices.items()}  # Convert keys back to tuples
    sequences = json.loads(session.get('sequences', '{}'))
    heatmap_data = generate_heatmap_png(jaccard_indices, list(sequences.keys()))
    return send_file(heatmap_data, mimetype='image/png', as_attachment=True, download_name='jaccard_heatmap.png')
