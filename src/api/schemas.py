from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    namespace: str


class SourceSchema(BaseModel):
    source: str
    chunk_id: int
    page_start: int
    page_end: int
    score: float


class QueryRequest(BaseModel):
    question: str
    namespace: str = "default"
    top_k: int | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceSchema]
    input_tokens: int
    output_tokens: int
