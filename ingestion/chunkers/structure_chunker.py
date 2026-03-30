import uuid
import hashlib
from typing import List
from loguru import logger
from pydantic import BaseModel

# Import our data models
from ingestion.parsers.base import ParsedDocument, PageElement
from ingestion.metadata_tagger import ChunkMetadata

class Chunk(BaseModel):
    content: str
    metadata: ChunkMetadata

class StructureAwareChunker:
    def __init__(self, max_tokens: int = 400, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.tokens_per_word = 1.3  # Rough approximation for speed

    def _count_words(self, tokens: int) -> int:
        return int(tokens / self.tokens_per_word)

    def _generate_hash(self, content: str, source: str, page: int) -> str:
        unique_str = f"{source}_{page}_{content}"
        return hashlib.sha256(unique_str.encode('utf-8')).hexdigest()

    def chunk(self, document: ParsedDocument) -> List[Chunk]:
        chunks = []
        current_heading = "Introduction"
        prose_buffer = ""
        
        logger.info(f"Chunking {document.source_file} (Rule: Structure-Aware)...")

        for page in document.pages:
            for element in page.elements:
                
                # RULE: Never chunk across headings. Flush buffer if heading changes.
                if element.element_type == "heading":
                    if prose_buffer.strip():
                        chunks.extend(self._chunk_prose(prose_buffer, document, current_heading, page.page_number))
                        prose_buffer = ""
                    current_heading = element.content

                # RULE: Build up standard text paragraphs
                elif element.element_type in ["paragraph", "list"]:
                    prose_buffer += element.content + "\n\n"

                # RULE: Tables are ATOMIC. Never split them.
                elif element.element_type == "table":
                    # Flush any pending prose first
                    if prose_buffer.strip():
                        chunks.extend(self._chunk_prose(prose_buffer, document, current_heading, page.page_number))
                        prose_buffer = ""
                    
                    # Store table exactly as-is (using HTML if available for complex layouts)
                    table_content = element.raw_html if element.raw_html else element.content
                    chunks.append(self._create_chunk(
                        content=table_content,
                        doc=document,
                        heading=current_heading,
                        page_num=page.page_number,
                        c_type="table"
                    ))

                # RULE: Figures keep their captions
                elif element.element_type == "figure":
                    if prose_buffer.strip():
                        chunks.extend(self._chunk_prose(prose_buffer, document, current_heading, page.page_number))
                        prose_buffer = ""
                        
                    fig_content = f"[Figure Image: {element.image_path}]\nCaption: {element.content}"
                    chunks.append(self._create_chunk(
                        content=fig_content,
                        doc=document,
                        heading=current_heading,
                        page_num=page.page_number,
                        c_type="figure"
                    ))

        # Final flush for the end of the document
        if prose_buffer.strip():
            chunks.extend(self._chunk_prose(prose_buffer, document, current_heading, document.pages[-1].page_number))

        logger.success(f"Generated {len(chunks)} cleanly structured chunks for {document.source_file}.")
        return chunks

    def _chunk_prose(self, text: str, doc: ParsedDocument, heading: str, page_num: int) -> List[Chunk]:
        """Splits long prose using a sliding window approach with overlap."""
        words = text.split()
        max_w = self._count_words(self.max_tokens)
        overlap_w = self._count_words(self.overlap_tokens)
        
        prose_chunks = []
        i = 0
        while i < len(words):
            chunk_words = words[i : i + max_w]
            chunk_text = " ".join(chunk_words)
            
            prose_chunks.append(self._create_chunk(
                content=chunk_text,
                doc=doc,
                heading=heading,
                page_num=page_num,
                c_type="prose"
            ))
            i += (max_w - overlap_w)
            
        return prose_chunks

    def _create_chunk(self, content: str, doc: ParsedDocument, heading: str, page_num: int, c_type: str) -> Chunk:
        """Packages the content with its full metadata payload."""
        c_hash = self._generate_hash(content, doc.source_file, page_num)
        
        meta = ChunkMetadata(
            source_file=doc.source_file,
            title=doc.metadata.get("title", doc.source_file),
            domain=doc.metadata.get("domain", "medical"),
            subdomain=doc.metadata.get("subdomain", "unknown"),
            edition=doc.metadata.get("edition"),
            publication_year=doc.metadata.get("publication_year"),
            page_number=page_num,
            content_type=c_type,
            chunk_hash=c_hash
        )
        
        # Prepend the heading to the content to give the LLM context of what it's reading
        enriched_content = f"[{doc.metadata.get('title')} - {heading}]\n{content}"
        
        return Chunk(content=enriched_content, metadata=meta)