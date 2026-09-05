from pathlib import Path
from pypdf import PdfReader

from src.chunk import Chunk

def load_documents() -> list:
    documents = []

    for path in Path("data").glob("*.pdf"):
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() for page in reader.pages)

        documents.append({
            "text" : text,
            "source" : path.name
        })

    return documents

def chunk_documents(text, source, *, chunk_size: int = 500, overlap: int = 50) -> list:
    """Split text into overlapping word-based chunks.

    Keyword-only chunk_size/overlap to prevent silent positional mixups
    (the previous (overlap, chunk_size) parameter order caused exactly that).
    """
    words = text.split()
    chunks = []
    counter = 0

    for i in range(0, len(words), chunk_size):
        start = i
        if i > overlap:
            start = i - overlap

        chunk = " ".join(words[start:i + chunk_size])
        chunks.append(Chunk(chunk, counter, source))

        counter += 1

    return chunks
