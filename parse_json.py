import json
from app import app, db
from models.all_models import *

with app.app_context():
    # Load the JSON file
    with open("uniprotkb_AND_reviewed_true_AND_existen_2025_03_26.json", "r") as file:  # Ensure correct path
        data = json.load(file)

    print("Data loaded")
    # Extract results
    proteins_data = data.get("results", [])

    # Process Organisms
    for entry in proteins_data:
        organism_name = entry['organism']['scientificName']
        organism_common_name = entry['organism'].get('commonName', None)  # Use .get() to avoid KeyError
        taxon_id = entry['organism']['taxonId']
        
        organism = Organism.query.filter_by(accession_id=taxon_id).first()
        if not organism:
            organism = Organism(accession_id=taxon_id, common_name=organism_common_name, scientific_name=organism_name)
            db.session.add(organism)
            db.session.commit()

    # Process Proteins
    for entry in proteins_data:

        # 🔁 Fix: re-fetch or re-create the correct organism here
        organism_name = entry['organism']['scientificName']
        organism_common_name = entry['organism'].get('commonName', None)
        taxon_id = entry['organism']['taxonId']

        organism = Organism.query.filter_by(accession_id=taxon_id).first()
        if not organism:
            organism = Organism(accession_id=taxon_id, common_name=organism_common_name, scientific_name=organism_name)
            db.session.add(organism)
            db.session.commit()

        subcellular_locations = []
        for comment in entry.get("comments", []):
            if comment.get("type") == "SUBCELLULAR LOCATION":
                for sublocation in comment.get("subcellularLocations", []):
                    location_name = sublocation.get("location", {}).get("value")
                    if location_name:
                        subcellular_locations.append(location_name)

        subcellular_location_str = ", ".join(subcellular_locations) if subcellular_locations else None

        # Insert Protein
        protein = Protein(
            accession_id=entry['primaryAccession'],
            name=entry['uniProtkbId'],
            sequence=entry['sequence']['value'],
            length=entry['sequence']['length'],
            subcellular_location=subcellular_location_str,
            organism_id=organism.id,  # ✅ Now correctly assigned
            database="SwissProt",
            evidence=0  # entry.get("ProteinExistence")
        )
        db.session.add(protein)
        db.session.commit()

        # Process PTMs for this protein
        for feature in entry.get("features", []):
            if feature["type"] == "Modified residue":
                position = feature.get("location", {}).get("start", {}).get("value")
                description = feature.get("description", "Unknown PTM").lower()

                amino_acids = [
                    "alanine", "arginine", "asparagine", "aspartic acid", "cysteine", "glutamine",
                    "glutamic acid", "glycine", "histidine", "isoleucine", "leucine", "lysine",
                    "methionine", "phenylalanine", "proline", "serine", "threonine", "tryptophan",
                    "tyrosine", "valine"
                ]

                found_aa = next((aa for aa in amino_acids if aa in description), None)

                if found_aa:
                    ptm_type = description.replace(found_aa, "").strip()
                    residue = found_aa
                else:
                    ptm_type = description
                    residue = "Unknown"

                if ";" in ptm_type:
                    split = ptm_type.split(";")
                    ptm_type = split[0]

                ptm = PTM.query.filter_by(type=ptm_type).first()
                if not ptm:
                    ptm = PTM(type=ptm_type)
                    db.session.add(ptm)
                    db.session.commit()

                ptm_relation = ProteinHasPTM(
                    position=position,
                    residue=residue,
                    source="SwissProt",
                    protein_accession_id=protein.accession_id,
                    ptm_id=ptm.id
                )
                db.session.add(ptm_relation)

        # Process Domains for this protein
        for feature in entry.get("features", []):
            if feature["type"] == "Domain":
                start_position = feature.get("location", {}).get("start", {}).get("value")
                end_position = feature.get("location", {}).get("end", {}).get("value")
                domain_description = feature.get("description", "Unknown Domain")

                domain = Domain(
                    accession_id=entry['primaryAccession'],
                    name=domain_description,
                    position_start=start_position,
                    position_end=end_position
                )
                db.session.add(domain)
                db.session.commit()

                domain_relation = DomainHasProtein(
                    domain_id=domain.id,
                    protein_accession_id=protein.accession_id
                )
                db.session.add(domain_relation)

    db.session.commit()
    print("Database populated successfully!")
