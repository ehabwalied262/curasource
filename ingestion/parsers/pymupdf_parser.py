import fitz  # PyMuPDF
# This line tells the underlying C library to stop printing warnings to the console
fitz.TOOLS.mupdf_display_errors(False)

from pathlib import Path
from loguru import logger
from .base import BaseParser, ParsedDocument, ParsedPage, PageElement

class PyMuPDFParser(BaseParser):
    def parse(self, filepath: str, metadata: dict) -> ParsedDocument:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        logger.info(f"Extracting {path.name} via PyMuPDF...")
        
        doc = fitz.open(filepath)
        parsed_pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # get_text("blocks") returns text grouped by logical paragraphs
            blocks = page.get_text("blocks") 
            
            elements = []
            for block in blocks:
                text = block[4].strip() # Index 4 contains the actual string
                
                if not text:
                    continue
                
                # Basic heuristic: if it's very short and title-cased, tag as heading
                is_heading = len(text.split()) < 10 and text.istitle()
                
                elements.append(PageElement(
                    element_type="heading" if is_heading else "paragraph",
                    content=text,
                    level=2 if is_heading else None
                ))
            
            parsed_pages.append(ParsedPage(
                page_number=page_num + 1,
                elements=elements
            ))

        logger.success(f"Successfully parsed {len(parsed_pages)} pages.")
        
        return ParsedDocument(
            source_file=path.name,
            metadata=metadata,
            pages=parsed_pages
        )