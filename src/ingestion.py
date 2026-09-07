from pathlib import Path

from pypdf import PdfReader
from tokenizers import Tokenizer

from src.chunk import Chunk
from src.embeddings import get_tokenizer

PAGE_SEPARATOR = "\n\n"


def extract_pages(path: Path) -> list[str]:
    """Extract per-page text from a PDF at `path`.

    Split out of load_documents() so the API's upload endpoint can extract
    pages from a saved upload the same way the CLI does from data/, without
    duplicating the PdfReader call.
    """
    reader = PdfReader(path)
    return [page.extract_text() for page in reader.pages]


def load_documents() -> list:
    documents = []

    for path in Path("data").glob("*.pdf"):
        documents.append({
            "pages" : extract_pages(path),
            "source" : path.name
        })

    return documents

def chunk_documents(pages, source, *, chunk_size: int = 400, overlap: int = 40) -> list:
    """Split page text into overlapping chunks sized in the embedding model's
    own tokens, not words.

    Keyword-only chunk_size/overlap to prevent silent positional mixups
    (a previous (overlap, chunk_size) parameter order caused exactly that).

    Word counts don't predict token counts closely enough under WordPiece
    subword tokenization: a word-based "500-word" chunk averaged ~700 real
    tokens (~35% over the embedding model's 512-token limit), so the model's
    truncation was silently dropping the tail of every chunk's embedding.
    Counting with the same tokenizer fastembed uses for the real embedding
    call is what actually determines whether a chunk gets truncated.

    Chunking runs against a clone of the embedding model's tokenizer (via
    to_str/from_str - in-memory, no re-download) with truncation disabled,
    since the whole document is longer than 512 tokens; the shared singleton
    used for real embedding calls is never touched. [CLS]/[SEP] are excluded
    from the token count/window since the embedding call adds its own.

    Chunk text is sliced from the original page text by each token's
    character offset rather than decoded from token ids, so chunk text stays
    byte-identical to the source instead of picking up WordPiece decode
    artifacts (subword rejoining, whitespace normalization).
    """
    full_text = PAGE_SEPARATOR.join(pages)

    page_spans = []
    pos = 0
    for page_num, page_text in enumerate(pages, start=1):
        start = pos
        end = start + len(page_text)
        page_spans.append((start, end, page_num))
        pos = end + len(PAGE_SEPARATOR)

    def page_at(char_pos: int) -> int:
        for start, end, page_num in page_spans:
            if start <= char_pos < end:
                return page_num
        return page_spans[-1][2]

    working_tokenizer: Tokenizer = Tokenizer.from_str(get_tokenizer().to_str())
    working_tokenizer.no_truncation()
    encoding = working_tokenizer.encode(full_text)

    offsets = [
        offset
        for offset, is_special in zip(encoding.offsets, encoding.special_tokens_mask)
        if not is_special
    ]

    chunks = []
    step = chunk_size - overlap
    prev_char_end = None

    for i in range(0, len(offsets), step):
        window = offsets[i : i + chunk_size]
        if not window:
            break

        char_start = window[0][0]
        char_end = window[-1][1]

        if prev_char_end is not None and char_end <= prev_char_end:
            # This window's content is already fully covered by the previous
            # chunk (can happen when the total token count lines up exactly
            # with the step size) - it would be a wasted, fully-redundant
            # duplicate chunk, so stop instead of adding it.
            break

        chunks.append(
            Chunk(
                full_text[char_start:char_end],
                len(chunks),
                source,
                page_at(char_start),
                page_at(char_end - 1),
            )
        )
        prev_char_end = char_end

    return chunks
