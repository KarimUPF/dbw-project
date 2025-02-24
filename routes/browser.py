from flask import Blueprint, request, jsonify, render_template, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import sessionmaker
from models.all_models import Protein, PTM, ProteinHasPTM, Organism, Query, History, QueryHasProtein
from app import db
import numpy as np
from itertools import combinations
def calculate_jaccard_index(set1, set2, window):
    """ Compute the Jaccard Index between two sets of normalized PTM positions with a user-defined window size. """
    set1 = sorted(set(set1))  # Sort to ensure a structured comparison
    set2 = sorted(set(set2))  # Sort to prevent redundant matching
    
    matched = set()  # Keep track of matched elements from set2
    
    intersection = 0
    for a in set1:
        for b in set2:
            if abs(a - b) <= window and b not in matched:
                intersection += 1
                matched.add(b)  # Ensure each PTM is counted only once
                  # Move to the next PTM in set1 once a match is found

    # Corrected union calculation
    union = len(set(set1).union(set(set2)))

    return intersection / union if union > 0 else 0.0




ptm_comparator = Blueprint('ptm_comparator', __name__)

# Function to normalize PTM positions
def normalize_ptm_positions(protein, protein_has_ptm):
    """ Calculate relative positions of PTMs by dividing PTM position by protein length. """
    return [(ptm.position / protein.length, ptm.residue, ptm.ptm_id) for ptm in protein_has_ptm]



@ptm_comparator.route('/compare_ptms', methods=['POST'])
@login_required
def compare_ptms():
    try:
        protein_ids = request.form.get('protein_id')
        ptm_types = request.form.get('ptm_type', '').split(',') if request.form.get('ptm_type') else None
        organisms = request.form.get('organism', '').split(',') if request.form.get('organism') else None

        session = db.session

        # If no PTM types are selected, default to all PTM types in the database
        if not ptm_types:
            ptm_types = [ptm[0] for ptm in session.query(PTM.type).distinct().all()]

        # If no organisms are selected, default to all organisms in the database
        if not organisms:
            organisms = [org[0] for org in session.query(Organism.scientific_name).distinct().all()]

        if not ptm_types:
            return jsonify({"error": "No PTM types available in the database"}), 400
        if not organisms:
            return jsonify({"error": "No organisms available in the database"}), 400

        results = []
        missing_ptms = []  # List to track proteins with no PTMs
        protein_ids_list = [pid.strip() for pid in protein_ids.split(',')] if protein_ids else []
        window=float(request.form.get('window'))
        if len(protein_ids_list) > 1:
            proteins = session.query(Protein).filter(Protein.accession_id.in_(protein_ids_list)).all()
        else:
            query_protein_id = protein_ids_list[0] if protein_ids_list else None

            proteins_query = session.query(Protein).join(
                ProteinHasPTM, Protein.accession_id == ProteinHasPTM.protein_accession_id
            ).join(
                PTM, ProteinHasPTM.ptm_id == PTM.id
            ).filter(PTM.type.in_(ptm_types))

            if organisms:
                proteins_query = proteins_query.join(
                    Organism, Protein.organism_id == Organism.id
                ).filter(Organism.scientific_name.in_(organisms))

            proteins_dict = {}

            if query_protein_id:
                user_protein = session.query(Protein).filter(Protein.accession_id == query_protein_id).first()
                if user_protein:
                    proteins_dict[query_protein_id] = user_protein

            for protein in proteins_query.distinct().all():
                if protein.accession_id not in proteins_dict:
                    proteins_dict[protein.accession_id] = protein

            proteins = list(proteins_dict.values())

        #parameters = [" ".join(organisms), " ".join(ptm_types)] 
        query = Query(parameters="parameters", summary_table=None, graph=None)

        for protein in proteins:
            ptm_query = session.query(ProteinHasPTM.position, PTM.type).join(
                PTM, ProteinHasPTM.ptm_id == PTM.id
            ).filter(
                ProteinHasPTM.protein_accession_id == protein.accession_id,
                PTM.type.in_(ptm_types)  # Retrieve only the selected PTM types
            )

            ptms = ptm_query.all()

            # If no PTMs found, warn the user and skip this protein
            if not ptms:
                flash(f"Protein {protein.accession_id} has no PTMs.")
                continue
            
            ptm_list = [{
                'position': ptm.position,
                'percentile_position': round((ptm.position / protein.length) * 100, 2),
                'type': ptm.type
            } for ptm in ptms]

<<<<<<< Updated upstream
=======
            if ptm_list:
                results.append({
                    'protein_id': protein.accession_id,
                    'sequence': protein.sequence,
                    'ptms': ptm_list
                })
            else:
                missing_ptms.append(protein.accession_id)  # Store proteins with no PTMs

        # If only one protein was requested and it has no PTMs, return an error message
        if len(protein_ids_list) == 1 and missing_ptms:
            session.close()
            return jsonify({"error": f"The protein '{missing_ptms[0]}' has no PTMs."}), 400
>>>>>>> Stashed changes

            results.append({
                'protein_id': protein.accession_id,
                'sequence': protein.sequence,
                'ptms': ptm_list
            })
            query_prot = QueryHasProtein(query_id=query.id, protein_accession_id=protein.accession_id)
            session.add(query_prot)

        session.add(query)
                
        # current_user                
        existing_history = History.query.filter_by(user_id=current_user.id).first()
        if not existing_history:
            existing_history = History(user_id=current_user.id)
            session.add(existing_history)
        
        existing_history.queries.append(query)
        session.add(existing_history)
        session.commit()
               
        session.close()
<<<<<<< Updated upstream
        return render_template('result.html', proteins=results)
=======
        

        # Compute Jaccard Index for all possible protein pairs if more than one protein is compared
        if len(proteins) > 1:
            jaccard_results = []
            protein_combinations = list(combinations(results, 2))

            for protein1, protein2 in protein_combinations:
                norm_positions_1 = [ptm['percentile_position'] / 100 for ptm in protein1['ptms']]
                norm_positions_2 = [ptm['percentile_position'] / 100 for ptm in protein2['ptms']]
                jaccard_index = calculate_jaccard_index(norm_positions_1, norm_positions_2, window)

                jaccard_results.append({
                    'jaccard_index': jaccard_index,
                    'protein_ids': [protein1['protein_id'], protein2['protein_id']]
                })

            results.append({'jaccard_indices': jaccard_results})


        return jsonify(results)
>>>>>>> Stashed changes

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


<<<<<<< Updated upstream
=======

>>>>>>> Stashed changes
@ptm_comparator.route('/get_organisms', methods=['GET'])
def get_organisms():
    try:
        session = db.session
        organisms = session.query(Organism.scientific_name).distinct().all()
        session.close()

        organism_list = [org[0] for org in organisms]  # Convert to list of strings
        return jsonify(organism_list)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ptm_comparator.route('/get_ptm_types', methods=['GET'])
def get_ptm_types():
    try:
        session = db.session
        ptm_types = session.query(PTM.type).distinct().all()
        session.close()

        ptm_list = [ptm[0] for ptm in ptm_types]  # Convert to list of strings
        return jsonify(ptm_list)

    except Exception as e:
        return jsonify({"error": str(e)}), 500