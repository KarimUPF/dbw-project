import json
import numpy as np
import itertools
from flask import Blueprint, request, jsonify

jaccard_from_browser = Blueprint('jaccard_from_browser', __name__)

# Function to compute Jaccard Index with window tolerance
def calculate_jaccard_index(ptms1, ptms2, window):
    """
    Compute Jaccard Index for PTM positions, considering a tolerance window.

    :param ptms1: List of (percentile_position, ptm_type) for protein 1
    :param ptms2: List of (percentile_position, ptm_type) for protein 2
    :param window: Percentage tolerance (e.g., 0.05 for 5%)
    :return: Dictionary of Jaccard Index per PTM type
    """
    if not ptms1 and not ptms2:
        return {}

    # Group PTMs by type
    ptms1_by_type = {}
    ptms2_by_type = {}

    for pos, ptm_type in ptms1:
        ptms1_by_type.setdefault(ptm_type, []).append(pos)

    for pos, ptm_type in ptms2:
        ptms2_by_type.setdefault(ptm_type, []).append(pos)

    jaccard_scores = {}

    # Compute Jaccard index for each PTM type
    all_types = set(ptms1_by_type.keys()).union(ptms2_by_type.keys())

    for ptm_type in all_types:
        positions1 = set(ptms1_by_type.get(ptm_type, []))
        positions2 = set(ptms2_by_type.get(ptm_type, []))

        # Expand positions within the window
        expanded_set1 = set()
        expanded_set2 = set()

        for pos in positions1:
            expanded_set1.update(np.arange(pos - window, pos + window, 0.01))

        for pos in positions2:
            expanded_set2.update(np.arange(pos - window, pos + window, 0.01))

        intersection = expanded_set1.intersection(expanded_set2)
        union = expanded_set1.union(expanded_set2)

        jaccard_index = len(intersection) / len(union) if union else 0
        jaccard_scores[ptm_type] = round(jaccard_index, 4)  # Round to 4 decimal places

    return jaccard_scores


@jaccard_from_browser.route('/calculate_jaccard_browser', methods=['POST'])
def calculate_jaccard_browser():
    try:
        # Load the PTM data from the file (simulating browser.py output)
        with open("/mnt/data/compare_ptms.json", "r") as f:
            data = json.load(f)

        protein_ids = request.form.get('protein_id', '').split(',')
        window = float(request.form.get('window', 0.05))  # Default 5% tolerance

        # Store PTM data per protein
        ptm_data = {}

        for protein in data:
            ptm_data[protein["protein_id"]] = [
                (ptm["percentile_position"], ptm["type"]) for ptm in protein.get("ptms", [])
            ]

        jaccard_results = {}

        # If only one protein is provided, compare it against all others
        if len(protein_ids) == 1:
            single_protein_id = protein_ids[0]
            if single_protein_id not in ptm_data:
                return jsonify({"error": f"Protein {single_protein_id} not found"}), 404

            jaccard_results[single_protein_id] = {}

            for other_id, other_ptms in ptm_data.items():
                if other_id == single_protein_id:
                    continue
                jaccard_results[single_protein_id][other_id] = calculate_jaccard_index(
                    ptm_data[single_protein_id], other_ptms, window
                )

        # If multiple proteins are provided, compute pairwise Jaccard Index
        else:
            protein_pairs = itertools.combinations(protein_ids, 2)
            for protein1, protein2 in protein_pairs:
                if protein1 in ptm_data and protein2 in ptm_data:
                    jaccard_results[f"{protein1} vs {protein2}"] = calculate_jaccard_index(
                        ptm_data[protein1], ptm_data[protein2], window
                    )

        return jsonify(jaccard_results)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
