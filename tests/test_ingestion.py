from src.ingestion import chunk_documents, extract_pages


def test_extract_pages_reads_text_per_page(tmp_path, test_pdf_bytes):
    path = tmp_path / "doc.pdf"
    path.write_bytes(test_pdf_bytes(["hello world", "second page text"]))

    pages = extract_pages(path)

    assert len(pages) == 2
    assert "hello world" in pages[0]
    assert "second page text" in pages[1]


def test_chunk_documents_respects_chunk_size(test_tokenizer):
    words = [f"word{i}" for i in range(50)]
    pages = [" ".join(words)]

    chunks = chunk_documents(pages, "doc.pdf", chunk_size=10, overlap=2, tokenizer=test_tokenizer)

    assert len(chunks) > 1
    assert all(len(c.chunk.split()) <= 10 for c in chunks)


def test_chunk_documents_overlap_shares_words_between_consecutive_chunks(test_tokenizer):
    words = [f"word{i}" for i in range(30)]
    pages = [" ".join(words)]

    chunks = chunk_documents(pages, "doc.pdf", chunk_size=10, overlap=3, tokenizer=test_tokenizer)

    first_words = chunks[0].chunk.split()
    second_words = chunks[1].chunk.split()
    assert first_words[-3:] == second_words[:3]


def test_chunk_documents_every_chunk_contributes_new_content(test_tokenizer):
    # exercises the redundant-tail guard: every chunk (including the last)
    # must add at least one word not already covered by an earlier chunk
    words = [f"word{i}" for i in range(40)]
    pages = [" ".join(words)]

    chunks = chunk_documents(pages, "doc.pdf", chunk_size=10, overlap=2, tokenizer=test_tokenizer)

    seen_words: set[str] = set()
    for c in chunks:
        chunk_words = set(c.chunk.split())
        assert chunk_words - seen_words, f"chunk {c.chunk_id} contributes no new content"
        seen_words |= chunk_words


def test_chunk_documents_tracks_page_provenance(test_tokenizer):
    pages = ["one two three four five", "six seven eight nine ten"]

    chunks = chunk_documents(pages, "doc.pdf", chunk_size=6, overlap=1, tokenizer=test_tokenizer)

    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 2


def test_chunk_documents_ids_are_sequential(test_tokenizer):
    pages = ["one two three four five six seven eight nine ten"]

    chunks = chunk_documents(pages, "doc.pdf", chunk_size=4, overlap=1, tokenizer=test_tokenizer)

    assert [c.chunk_id for c in chunks] == list(range(len(chunks)))


def test_chunk_documents_text_is_byte_identical_to_source(test_tokenizer):
    # offset-slicing (not token-decode) means chunk text must be an exact
    # substring of the original, whitespace and all
    pages = ["one   two\tthree four"]

    chunks = chunk_documents(pages, "doc.pdf", chunk_size=2, overlap=0, tokenizer=test_tokenizer)

    full_text = pages[0]
    for c in chunks:
        assert c.chunk in full_text
