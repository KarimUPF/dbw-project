from sqlalchemy import create_engine, text
import os

# Create a direct connection to MySQL (no Flask imports)
engine = create_engine("mysql+pymysql://ptm:Popojad123!@localhost/ptm_nexus")

def generate_fasta(output_file="protein_sequences.fasta"):
    """Fetch all protein sequences from MySQL and save them in FASTA format."""
    
    query = text("SELECT accession_id, sequence FROM protein")  # Adjust table name if necessary

    with engine.connect() as conn:
        results = conn.execute(query).fetchall()

        if not results:
            print("No protein sequences found in the database.")
            return

        with open(output_file, "w") as fasta_file:
            for accession_id, sequence in results:
                fasta_file.write(f">{accession_id}\n{sequence}\n")
    
    print(f"FASTA file '{output_file}' generated successfully!")

if __name__ == "__main__":
    generate_fasta()
