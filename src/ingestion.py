from pathlib import Path
from pypdf import PdfReader

from src.chunk import Chunk

def load_documents() -> list:
    documents = []

    for path in Path("data").glob("*.pdf"):
        reader = PdfReader(path)
        pages = [page.extract_text() for page in reader.pages]

        documents.append({
            "pages" : pages,
            "source" : path.name
        })

    return documents

def chunk_documents(pages, source, *, chunk_size: int = 500, overlap: int = 50) -> list:
    """Split per-page text into overlapping word-based chunks.

    Keyword-only chunk_size/overlap to prevent silent positional mixups
    (the previous (overlap, chunk_size) parameter order caused exactly that).

    Words from all pages are concatenated into one continuous stream before
    chunking (same algorithm as before), but each word's originating page is
    tracked in parallel so every chunk can carry page_start/page_end - stable
    provenance back to the source PDF that survives future re-chunking runs,
    unlike chunk_id which is only unique within a given run.
    """
    words = []
    word_pages = []
    for page_num, page_text in enumerate(pages, start=1):
        page_words = page_text.split()
        words.extend(page_words)
        word_pages.extend([page_num] * len(page_words))

    chunks = []
    counter = 0

    for i in range(0, len(words), chunk_size):
        start = i
        if i > overlap:
            start = i - overlap

        end = i + chunk_size
        chunk = " ".join(words[start:end])
        page_start = word_pages[start]
        page_end = word_pages[min(end, len(words)) - 1]

        chunks.append(Chunk(chunk, counter, source, page_start, page_end))

        counter += 1

    return chunks
