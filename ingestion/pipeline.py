import argparse
from pathlib import Path
from loguru import logger

# Import all the Lego blocks we just built
from ingestion.metadata_tagger import MetadataTagger
from ingestion.parsers.pymupdf_parser import PyMuPDFParser
from ingestion.parsers.unstructured_parser import UnstructuredParser
from ingestion.chunkers.structure_chunker import StructureAwareChunker
from ingestion.embedder import QdrantEmbedder

class IngestionPipeline:
    def __init__(self):
        logger.info("Initializing CuraSource Ingestion Pipeline...")
        self.tagger = MetadataTagger()
        self.pymupdf_parser = PyMuPDFParser()
        self.unstructured_parser = UnstructuredParser()
        
        # Rule #1: Never split a table (enforced here)
        self.chunker = StructureAwareChunker(max_tokens=400, overlap_tokens=50)
        
        # Connects to your local Docker Qdrant & loads the BGE model
        self.embedder = QdrantEmbedder(collection_name="curasource_chunks")

    def process_file(self, file_path: Path):
        logger.info(f"=== Starting: {file_path.name} ===")
        
        # 1. Identify the file (Medical vs Fitness, Edition, etc.)
        metadata = self.tagger.get_source_info(file_path.name)
        
        # 2. Route to the correct Parser
        strategy = metadata.get("parser_strategy", "pymupdf")
        if strategy == "unstructured":
            parser = self.unstructured_parser
        else:
            parser = self.pymupdf_parser
            
        # 3. Parse Document
        try:
            parsed_doc = parser.parse(str(file_path), metadata)
        except Exception as e:
            logger.error(f"Failed to parse {file_path.name}: {e}")
            return
            
        # 4. Chunk Document
        chunks = self.chunker.chunk(parsed_doc)
        
        # 5. Embed & Upload to Qdrant
        self.embedder.embed_and_upload(chunks)
        
        logger.success(f"=== Finished: {file_path.name} ===")

    def run_full_corpus(self, corpus_dir: str):
        corpus_path = Path(corpus_dir)
        if not corpus_path.exists():
            logger.error(f"Corpus directory not found: {corpus_dir}")
            return
            
        pdf_files = list(corpus_path.rglob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDFs in '{corpus_dir}'.")
        
        count = 0
        for pdf in pdf_files:
            # Skip the duplicates we isolated earlier
            if "_duplicates" in pdf.parts:
                continue
                
            self.process_file(pdf)
            count += 1
            
        logger.success(f"🎉 Full corpus ingestion complete! Processed {count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CuraSource Master Ingestion Pipeline")
    parser.add_argument("--corpus-dir", type=str, default="Sources", help="Path to the corpus directory")
    parser.add_argument("--file", type=str, help="Process a single file (e.g., Sources/ACE/book.pdf)")
    
    args = parser.parse_args()
    pipeline = IngestionPipeline()
    
    if args.file:
        pipeline.process_file(Path(args.file))
    else:
        pipeline.run_full_corpus(args.corpus_dir)