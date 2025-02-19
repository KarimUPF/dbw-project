from flask import Blueprint, request, jsonify, render_template
from sqlalchemy.orm import sessionmaker
from models.all_models import db, Protein, PTM, ProteinHasPTM
import numpy as np

ptm_comparator = Blueprint('ptm_comparator', __name__)

# Function to normalize PTM positions
def normalize_ptm_positions(protein, protein_has_ptm):
    """ Calculate relative positions of PTMs by dividing PTM position by protein length. """
    return [(ptm.position / protein.length, ptm.residue, ptm.ptm_id) for ptm in protein_has_ptm]


# Function to calculate Jaccard Index with window tolerance
def calculate_jaccard_index(set1, set2, window):
    if not set1 and not set2:
        return 1.0  # Both are empty
    elif not set1 or not set2:
        return 0.0  # One is empty

    expanded_set1 = set()
    expanded_set2 = set()

    for pos, residue, ptm_type in set1:
        expanded_set1.update((round(x, 5), residue, ptm_type) for x in np.arange(pos - window, pos + window, 0.01))
    for pos, residue, ptm_type in set2:
        expanded_set2.update((round(x, 5), residue, ptm_type) for x in np.arange(pos - window, pos + window, 0.01))

    intersection = expanded_set1.intersection(expanded_set2)
    union = expanded_set1.union(expanded_set2)
    return len(intersection) / len(union)

# PTM Comparison Route
@ptm_comparator.route('/compare_ptms', methods=['GET', 'POST'])
def compare_ptms():
    try:
        if request.method == 'POST':
            protein_ids = request.form.get('protein_id')
            if not protein_ids:
                return jsonify({"error": "No protein ID provided"}), 400

            protein_ids = protein_ids.split(',')
            print(f"Protein IDs: {protein_ids}")

            organism = request.form.get('organism')
            ptm_type = request.form.get('ptm_type')
            window = request.form.get('window')

            if not window:
                return jsonify({"error": "Window parameter missing"}), 400
            window = float(window)

            session = db.session
            query_proteins = session.query(Protein).filter(Protein.accession_id.in_(protein_ids)).all()
            if not query_proteins:
                return jsonify({"error": "No matching proteins found in the database"}), 404
            print(f"Query Proteins Found: {len(query_proteins)}")

            all_proteins = session.query(Protein).all()
            print(f"Total Proteins in Database: {len(all_proteins)}")

            results = []
            for query_protein in query_proteins:
                query_ptms = session.query(ProteinHasPTM).filter_by(protein_accession_id=query_protein.accession_id).all()
                query_normalized = normalize_ptm_positions(query_protein, query_ptms)
                print(f"Query Protein: {query_protein.accession_id}, PTMs: {query_normalized}")

                for match_protein in all_proteins:
                    if query_protein.accession_id == match_protein.accession_id:
                        continue
                    match_ptms = session.query(ProteinHasPTM).filter_by(protein_accession_id=match_protein.accession_id).all()
                    match_normalized = normalize_ptm_positions(match_protein, match_ptms)
                    print(f"Matching Protein: {match_protein.accession_id}, PTMs: {match_normalized}")

                    jaccard = calculate_jaccard_index(set(query_normalized), set(match_normalized), window)
                    print(f"Jaccard Index for {query_protein.accession_id} vs {match_protein.accession_id}: {jaccard}")

                    results.append({
                        'query_protein': query_protein.accession_id,
                        'match_protein': match_protein.accession_id,
                        'jaccard_index': round(jaccard, 3)
                    })

            session.close()
            return jsonify(results)

        return render_template('compare.html')
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500  # Return error in JSON format
