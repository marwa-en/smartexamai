"""Service de segmentation (chunking)"""
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


CHUNK_SIZE = 550
CHUNK_OVERLAP = 150
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
NB_CHUNKS_RECHERCHE = 3
class ChunkerService:
    """Service responsable du découpage en chunks."""
    
    @staticmethod
    def chunker_documents(documents: List[Document]) -> List[Document]:
        """Découpe les documents en chunks."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=SEPARATORS,
            length_function=len,
            is_separator_regex=False,
        )
        
        chunks = text_splitter.split_documents(documents)
        
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
            chunk.metadata["chunk_size"] = len(chunk.page_content)
        
        return chunks