import hashlib
import argparse
import shutil
from pathlib import Path
from loguru import logger

def get_file_hash(filepath: Path, chunk_size: int = 8192) -> str:
    """Calculate the SHA-256 hash of a file in chunks to handle large PDFs."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()

def main(corpus_dir: str, resolve: bool = False):
    corpus_path = Path(corpus_dir)
    if not corpus_path.exists():
        logger.error(f"Directory not found: {corpus_dir}")
        return

    logger.info(f"Scanning {corpus_path.resolve()} for PDF duplicates...")
    
    seen_hashes = {}
    duplicates = []
    
    # Recursively find all PDFs
    pdf_files = list(corpus_path.rglob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files to check.")

    for file_path in pdf_files:
        # Skip our safety duplicates folder if it exists
        if "_duplicates" in file_path.parts:
            continue

        file_hash = get_file_hash(file_path)
        
        if file_hash in seen_hashes:
            original = seen_hashes[file_hash]
            logger.warning(f"DUPLICATE FOUND:\n  Keep: {original}\n  Dupe: {file_path}")
            duplicates.append(file_path)
        else:
            seen_hashes[file_hash] = file_path

    if not duplicates:
        logger.info("✅ No duplicates found! Your corpus is clean.")
        return

    logger.info(f"Found {len(duplicates)} duplicate files.")

    if resolve:
        duplicates_dir = corpus_path / "_duplicates"
        duplicates_dir.mkdir(exist_ok=True)
        
        for dupe in duplicates:
            dest_path = duplicates_dir / dupe.name
            
            # Handle name collisions in the duplicates folder
            counter = 1
            while dest_path.exists():
                dest_path = duplicates_dir / f"{dupe.stem}_{counter}{dupe.suffix}"
                counter += 1
                
            shutil.move(str(dupe), str(dest_path))
            logger.info(f"Moved duplicate to: {dest_path}")
            
        logger.success(f"Moved {len(duplicates)} duplicates to {duplicates_dir}")
    else:
        logger.info("Run with the --resolve flag to move these files to a '_duplicates' folder.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find and resolve duplicate PDFs in the corpus.")
    parser.add_argument("--corpus-dir", type=str, default="Sources", help="Path to the corpus directory")
    parser.add_argument("--resolve", action="store_true", help="Move duplicates to a _duplicates folder")
    
    args = parser.parse_args()
    main(args.corpus_dir, args.resolve)