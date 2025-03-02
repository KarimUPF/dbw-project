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
    # Get alignment length from first sequence
    alignment_length = len(next(iter(sequences.values())))
    window_size = int(alignment_length * window_percentage)
    
    # Normalize positions to 0-1 range
    normalized_ptms = {}
    for prot_id, ptms in adjusted_positions.items():
        normalized_ptms[prot_id] = set(pos / alignment_length for pos in ptms.keys())
    
    # Calculate Jaccard indices for top 10 proteins
    protein_ids = list(sequences.keys())[:10]  # Get top 10 proteins
    jaccard_scores = {}
    
    for i in range(len(protein_ids)):
        for j in range(i + 1, len(protein_ids)):
            prot1, prot2 = protein_ids[i], protein_ids[j]
            
            # Skip if either protein has no PTMs
            if not normalized_ptms[prot1] or not normalized_ptms[prot2]:
                jaccard_scores[(prot1, prot2)] = 0
                continue
            
            # Find matching PTMs within window
            matches = 0
            for pos1 in normalized_ptms[prot1]:
                window_start = max(0, pos1 - (window_size/2)/alignment_length)
                window_end = min(1, pos1 + (window_size/2)/alignment_length)
                
                for pos2 in normalized_ptms[prot2]:
                    if window_start <= pos2 <= window_end:
                        matches += 1
                        break
            
            # Calculate Jaccard index
            union = len(normalized_ptms[prot1]) + len(normalized_ptms[prot2])
            jaccard_score = matches / union if union > 0 else 0
            jaccard_scores[(prot1, prot2)] = jaccard_score
    
    return jaccard_scores
