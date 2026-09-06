class Chunk:
    def __init__(self, chunk, chunk_id, source, page_start, page_end, embedding = None):
        self.chunk = chunk
        self.chunk_id = chunk_id
        self.source = source
        self.page_start = page_start
        self.page_end = page_end
        self.embedding = embedding

