import os
from pathlib import Path
from loguru import logger
from unstructured.partition.pdf import partition_pdf
from .base import BaseParser, ParsedDocument, ParsedPage, PageElement

class UnstructuredParser(BaseParser):
    def parse(self, filepath: str, metadata: dict) -> ParsedDocument:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        logger.info(f"Extracting {path.name} via Unstructured (hi_res)... this may take a moment.")
        
        # Define where we want to save any extracted ECGs or medical figures
        image_output_dir = Path("Sources/extracted_figures") / path.stem
        os.makedirs(image_output_dir, exist_ok=True)

        # The magic happens here: hi_res + table inference
        raw_elements = partition_pdf(
            filename=filepath,
            strategy="hi_res",
            infer_table_structure=True,
            extract_images_in_pdf=True,
            image_output_dir_path=str(image_output_dir)
        )

        pages_dict = {}
        for el in raw_elements:
            page_num = el.metadata.page_number
            if page_num not in pages_dict:
                pages_dict[page_num] = []

            # Map Unstructured's dynamic types to our strict PageElement schema
            el_type = type(el).__name__
            content = str(el).strip()
            
            if not content and el_type != "Image":
                continue
                
            element_type = "paragraph"
            level = None
            raw_html = None
            image_path = None
            
            if el_type in ["Title", "Header"]:
                element_type = "heading"
                level = 2 
            elif el_type == "Table":
                element_type = "table"
                raw_html = el.metadata.text_as_html  # Crucial for complex drug dosing charts
            elif el_type == "Image":
                element_type = "figure"
                image_path = el.metadata.image_path
            elif el_type == "ListItem":
                element_type = "list"
                
            pages_dict[page_num].append(PageElement(
                element_type=element_type,
                content=content,
                level=level,
                raw_html=raw_html,
                image_path=image_path
            ))
        
        # Assemble the final standardized document
        parsed_pages = [
            ParsedPage(page_number=p_num, elements=pages_dict[p_num])
            for p_num in sorted(pages_dict.keys())
        ]

        logger.success(f"Successfully parsed {len(parsed_pages)} pages with complex layouts.")

        return ParsedDocument(
            source_file=path.name,
            metadata=metadata,
            pages=parsed_pages
        )