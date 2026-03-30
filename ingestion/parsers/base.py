from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional, List

# These dataclasses perfectly match your DATA_PIPELINE.md specifications
@dataclass  
class PageElement:
    element_type: Literal["heading", "paragraph", "table", "figure", "list", "algorithm"]
    content: str
    level: Optional[int] = None       # e.g., 1 for H1, 2 for H2
    image_path: Optional[str] = None  # Local path or R2 URL
    caption: Optional[str] = None
    raw_html: Optional[str] = None    # Useful for preserving complex tables

@dataclass
class ParsedPage:
    page_number: int
    elements: List[PageElement]

@dataclass
class ParsedDocument:
    source_file: str
    metadata: dict
    pages: List[ParsedPage]

class BaseParser(ABC):
    """
    Abstract base class that all parsers (PyMuPDF, Unstructured, etc.) must inherit from.
    Enforces the Open/Closed Principle from CODE_STANDARDS.md.
    """
    
    @abstractmethod
    def parse(self, filepath: str, metadata: dict) -> ParsedDocument:
        """Parses a file and returns a standardized ParsedDocument."""
        pass