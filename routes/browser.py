from flask import Blueprint, request, jsonify, render_template, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import sessionmaker
from models.all_models import Protein, PTM, ProteinHasPTM, Organism, Query, History, QueryHasProtein
from app import db
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
        protein_ids_list = [pid.strip() for pid in protein_ids.split(',')] if protein_ids else []

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
        return render_template('result.html', proteins=results)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


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
