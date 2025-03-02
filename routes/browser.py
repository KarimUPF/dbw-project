from flask import Blueprint, request, jsonify, render_template
from models.all_models import db, Protein, PTM, ProteinHasPTM
import subprocess
from Bio import SeqIO
from Bio.Align.Applications import ClustalOmegaCommandline



ptm_comparator = Blueprint('ptm_comparator', __name__)  # Ensure Blueprint name matches

def run_blast(protein_id, session):
    """Run BLASTP to find the 20 most similar proteins from MySQL."""
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
    "-max_target_seqs", "50",  # Increase max targets
    "-out", blast_output
    ])


    hits = []
    with open(blast_output, "r") as f:
        for line in f:
            hits.append(line.strip().split("\t")[0])  # Collect protein IDs
    return hits


def align_sequences(proteins):
    """Perform multiple sequence alignment with Clustal Omega."""
    fasta_file = "sequences.fasta"
    
    with open(fasta_file, "w") as f:
        for protein in proteins:
            f.write(f">{protein.accession_id}\n{protein.sequence}\n")

    aligned_file = "aligned.fasta"
    
    # Use --force to allow overwriting
    clustal_cline = ClustalOmegaCommandline(infile=fasta_file, outfile=aligned_file, force=True, verbose=True, auto=True)
    subprocess.run(str(clustal_cline), shell=True)

    return aligned_file


def adjust_ptm_positions(sequences, ptm_dict):
    """
    Adjust PTM positions based on alignment gaps for all proteins.
    :param sequences: Dict of {Protein ID: Aligned Sequence}
    :param ptm_dict: Dict of {Protein ID: {Original Position: PTM Type}}
    :return: Adjusted PTM positions
    """
    adjusted_positions = {}

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
                    new_positions[i] = {
                        "original_position": original_pos,
                        "new_position": i,
                        "type": ptm_positions[original_pos]  # Keep type
                    }

        adjusted_positions[prot_id] = new_positions  # Store adjusted PTM data

    return adjusted_positions



@ptm_comparator.route('/compare_ptms', methods=['POST'])
def align_and_update_ptms():
    """Align proteins and return PTM positions as JSON for an interactive HTML page."""
    protein_id = request.form.get('protein_id')
    if not protein_id:
        return jsonify({"error": "No protein_id provided"}), 400

    session = db.session

    # Run BLAST
    similar_proteins_ids = run_blast(protein_id, session)
    similar_proteins = session.query(Protein).filter(Protein.accession_id.in_(similar_proteins_ids)).all()

    if not similar_proteins:
        return jsonify({"error": f"No similar proteins found for {protein_id}"}), 400

    # Include the query protein itself
    query_protein = session.query(Protein).filter_by(accession_id=protein_id).first()
    if not query_protein:
        return jsonify({"error": f"Protein {protein_id} not found"}), 400

    proteins_to_align = [query_protein] + similar_proteins

    # Run Clustal Omega
    aligned_file = align_sequences(proteins_to_align)

    # Load aligned sequences
    sequences = {record.id: str(record.seq) for record in SeqIO.parse(aligned_file, "fasta")}

    # Collect PTMs
    ptm_dict = {}
    for p in proteins_to_align:
        ptms = session.query(ProteinHasPTM.position, PTM.type).join(PTM).filter(
            ProteinHasPTM.protein_accession_id == p.accession_id
        ).all()
        ptm_dict[p.accession_id] = {ptm.position: {"type": ptm.type, "new_position": None} for ptm in ptms}

    # Adjust PTM positions with gaps
    for protein_id, aligned_seq in sequences.items():
        if protein_id not in ptm_dict:
            continue

        ptms = ptm_dict[protein_id]
        gap_count = 0
        adjusted_ptms = {}

        for i, char in enumerate(aligned_seq):
            if char == "-":
                gap_count += 1
            else:
                original_pos = i - gap_count
                if original_pos in ptms:
                    adjusted_ptms[i] = {
                        "original_position": original_pos,
                        "new_position": i,
                        "type": ptms[original_pos]["type"]
                    }

        ptm_dict[protein_id] = adjusted_ptms  # Update with adjusted positions

    session.close()

    return render_template("ptm_interactive.html", sequences=sequences, ptm_data=ptm_dict)