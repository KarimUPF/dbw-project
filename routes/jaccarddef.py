def calculate_ptm_jaccard_with_window(adjusted_positions, sequences, window_percentage=0.05):
    """
    Calculate Jaccard index for PTMs between proteins, considering a sliding window.

    Args:
        adjusted_positions: Dict of {Protein ID: {Position: PTM info}}
        sequences: Dict of {Protein ID: Aligned sequence}
        window_percentage: Percentage of sequence length to use as window size

    Returns:
        Dict of {(protein1, protein2): jaccard_score}
    """
    alignment_length = len(next(iter(sequences.values())))  # Get alignment length
    window_size = int(alignment_length * window_percentage)  # Convert to absolute positions

    ptm_sets = {prot_id: set(ptms.keys()) for prot_id, ptms in adjusted_positions.items()}

    protein_ids = list(sequences.keys())
    jaccard_scores = {}

    for i in range(len(protein_ids)):
        for j in range(i + 1, len(protein_ids)):
            prot1, prot2 = protein_ids[i], protein_ids[j]

            ptms1 = ptm_sets.get(prot1, set())
            ptms2 = ptm_sets.get(prot2, set())

            if not ptms1 or not ptms2:
                jaccard_scores[(prot1, prot2)] = 0
                continue

            # Fix: Track matches more accurately
            matched_ptms = set()
            for pos1 in ptms1:
                for pos2 in ptms2:
                    if abs(pos1 - pos2) <= window_size:
                        matched_ptms.add((pos1, pos2))
                        break  # Only count the closest match

            # Fix: calculate intersection based on matched pairs
            intersection_size = len(matched_ptms)
            # Fix: union should be total unique PTMs minus duplicates
            union_size = len(ptms1 | ptms2) 
            jaccard_score = intersection_size / union_size if union_size > 0 else 0
            jaccard_scores[(prot1, prot2)] = jaccard_score

    return jaccard_scores