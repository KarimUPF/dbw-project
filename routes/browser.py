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


ptm_comparator = Blueprint('ptm_comparator', __name__)

import os
import subprocess

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
    """Perform multiple sequence alignment with Clustal Omega."""
    fasta_file = "sequences.fasta"
    
    # Make sure we're writing valid sequences to the file
    with open(fasta_file, "w") as f:
        for protein in proteins:
            if protein.sequence and protein.accession_id:
                f.write(f">{protein.accession_id}\n{protein.sequence}\n")
    
    # Check if the file has content
    import os
    if os.path.getsize(fasta_file) == 0:
        raise ValueError("No valid sequences were found in the proteins list")
    
    aligned_file = "aligned.fasta"
    
    # Use subprocess.run with a list of arguments (no shell=True)
    # This is safer and more reliable across platforms
    import subprocess
    result = subprocess.run(
        ["clustalo", "-i", fasta_file, "-o", aligned_file, "--force"], 
        capture_output=True,
        text=True,
        shell=False  # Don't use shell=True
    )
    
    # Check for errors
    if result.returncode != 0:
        print(f"Clustal Omega error: {result.stderr}")
        raise RuntimeError(f"Clustal Omega failed: {result.stderr}")
    
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
        # Get user inputs
        protein_ids = request.form.get('protein_id', '').split(',')
        protein_ids = [pid.strip() for pid in protein_ids]  # Strip whitespace
        selected_ptms = request.form.get('ptm_type', '').split(',')
        selected_organisms = request.form.get('organism', '').split(',')
        window_size = float(request.form.get('window', '0.05'))  # Default to 0.05
    else:  # Handle "Re-Run" (GET request)
        protein_ids = request.args.get('protein_id', '').split(',')
        selected_ptms = request.args.get('ptm_type', '').split(',')
        selected_organisms = request.args.get('organism', '').split(',')
        window_size = float(request.args.get('window', '0.05'))

    # If no PTM or organism is selected, consider all of them
    selected_ptms = None if selected_ptms == [''] else selected_ptms
    selected_organisms = None if selected_organisms == [''] else selected_organisms

    session_db = db.session  # SQLAlchemy session
    
    # Unified handling for single or multiple proteins
    if len(protein_ids) == 1:
        # Single protein case - do BLAST with organism filtering
        protein_id = protein_ids[0]
        
        # Use the updated BLAST function with organism filtering
        similar_proteins_ids = run_blast(protein_id, session_db, selected_organisms)
        
        # Get the proteins from BLAST results
        proteins_to_align = session_db.query(Protein).filter(
            Protein.accession_id.in_(similar_proteins_ids)
        ).all()
        
        # Always include the query protein
        query_protein = session_db.query(Protein).filter_by(accession_id=protein_id).first()
        if query_protein and query_protein not in proteins_to_align:
            proteins_to_align.append(query_protein)
    else:
        # Multiple proteins case - use the provided proteins
        # Apply organism filter if specified
        query = session_db.query(Protein).filter(Protein.accession_id.in_(protein_ids))
        if selected_organisms:
            query = query.join(Organism).filter(Organism.scientific_name.in_(selected_organisms))
        proteins_to_align = query.all()
    
    if not proteins_to_align:
        return jsonify({"error": "No proteins found matching the criteria"}), 400
        
    # Common code for both cases
    aligned_file = align_sequences(proteins_to_align)
    sequences = {record.id: str(record.seq) for record in SeqIO.parse(aligned_file, "fasta")}
    
    # Collect PTMs, filtering by selected PTM types
    ptm_dict = {}
    for p in proteins_to_align:
        ptms = session_db.query(ProteinHasPTM.position, PTM.type).join(PTM).filter(
            ProteinHasPTM.protein_accession_id == p.accession_id
        )
        
        if selected_ptms:
            ptms = ptms.filter(PTM.type.in_(selected_ptms))
            
        ptms = ptms.all()
        
        ptm_dict[p.accession_id] = {
            ptm.position: {"type": ptm.type} for ptm in ptms
        }
    
    ptm_data = adjust_ptm_positions(sequences, ptm_dict)
    jaccard_indices = calculate_ptm_jaccard_with_window(ptm_data, sequences, window_size)
    
    # Convert tuple keys to strings for JSON serialization
    formatted_jaccard_indices = {f"{k[0]}, {k[1]}": v for k, v in jaccard_indices.items()}

    parameters = {
        "protein_ids": protein_ids,
        "ptm_types": selected_ptms,
        "organism_filter": selected_organisms,
        "sequences": sequences,
        "ptm_data": ptm_data,
        "jaccard_indices": formatted_jaccard_indices,
        "window_size": window_size,
    }

    query = Query(parameters=parameters, summary_table=None, graph=None)

    history = session_db.query(History).filter_by(user_id=current_user.id).first()
    if not history:
        history = History(user_id=current_user.id)
        session_db.add(history)
        session_db.commit()
    
    session_db.add(query)
    history.queries.append(query)
    session_db.commit()    

    return render_template(
        "ptm_interactive.html", 
        sequences=sequences, 
        ptm_data=ptm_data,
        jaccard_indices=formatted_jaccard_indices,  # Use the formatted version
        window_size=window_size
    )



@ptm_comparator.route('/download_fasta', methods=['GET'])
def download_fasta():
    fasta_file_path = "aligned.fasta"  
    return send_file(fasta_file_path, as_attachment=True, download_name="aligned.fasta")