import argparse
import json
from pathlib import Path
from loguru import logger

from ingestion.metadata_tagger import MetadataTagger
from ingestion.parsers.pymupdf_parser import PyMuPDFParser
from ingestion.parsers.unstructured_parser import UnstructuredParser
from ingestion.chunkers.structure_chunker import StructureAwareChunker
from ingestion.embedder import QdrantEmbedder

PROGRESS_FILE = Path("ingestion_progress.json")


def load_progress() -> list[str]:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return []


def save_progress(done: list[str]):
    PROGRESS_FILE.write_text(json.dumps(done, indent=2))


class IngestionPipeline:
    def __init__(self):
        logger.info("Initializing CuraSource Ingestion Pipeline...")
        self.tagger = MetadataTagger()
        self.pymupdf_parser = PyMuPDFParser()
        self.unstructured_parser = UnstructuredParser()
        self.chunker = StructureAwareChunker(max_tokens=400, overlap_tokens=50)
        self.embedder = QdrantEmbedder(collection_name="curasource_chunks")

    def process_file(self, file_path: Path):
        logger.info(f"=== Starting: {file_path.name} ===")

        metadata = self.tagger.get_source_info(file_path.name)

        strategy = metadata.get("parser_strategy", "pymupdf")
        if strategy == "unstructured":
            parser = self.unstructured_parser
        else:
            parser = self.pymupdf_parser

        try:
            parsed_doc = parser.parse(str(file_path), metadata)
        except Exception as e:
            logger.error(f"Failed to parse {file_path.name}: {e}")
            return False

        chunks = self.chunker.chunk(parsed_doc)
        self.embedder.embed_and_upload(chunks)

        logger.success(f"=== Finished: {file_path.name} ===")
        return True

    def run_full_corpus(self, corpus_dir: str):
        corpus_path = Path(corpus_dir)
        if not corpus_path.exists():
            logger.error(f"Corpus directory not found: {corpus_dir}")
            return

        pdf_files = sorted(corpus_path.rglob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDFs in '{corpus_dir}'.")

        done = load_progress()
        remaining = [p for p in pdf_files if str(p) not in done and "_duplicates" not in p.parts]
        logger.info(f"Already ingested: {len(done)} | Remaining: {len(remaining)}")

        count = 0
        for pdf in remaining:
            try:
                ok = self.process_file(pdf)
                if ok:
                    done.append(str(pdf))
                    save_progress(done)
                    count += 1
            except Exception as e:
                logger.error(f"Error processing {pdf.name}: {e}")
                continue

        logger.success(f"Done! Processed {count} new files this run. Total ingested: {len(done)}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CuraSource Master Ingestion Pipeline")
    parser.add_argument("--corpus-dir", type=str, default="Sources", help="Path to the corpus directory")
    parser.add_argument("--file", type=str, help="Process a single file")

    args = parser.parse_args()
    pipeline = IngestionPipeline()

    if args.file:
        file_path = Path(args.file)
        ok = pipeline.process_file(file_path)
        if ok:
            done = load_progress()
            if str(file_path) not in done:
                done.append(str(file_path))
                save_progress(done)
    else:
        pipeline.run_full_corpus(args.corpus_dir)
