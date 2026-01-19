from io import BytesIO
from tempfile import NamedTemporaryFile

from langchain.schema import Document
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from pydantic import BaseModel

from mcr_generation.app.configs.settings import ChunkingConfig

chunk_config = ChunkingConfig()


class Chunk(BaseModel):
    id: int
    text: str


def chunk_docx_to_document_list(docx_bytes: BytesIO) -> list[Chunk]:
    with NamedTemporaryFile(suffix=".docx") as tmp:
        tmp.write(docx_bytes.getbuffer())
        tmp.flush()

        loader = UnstructuredWordDocumentLoader(tmp.name)
        docs = loader.load()

    # Combine all page contents into one large text
    full_text = "\n".join([doc.page_content for doc in docs])

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_config.CHUNK_SIZE,
        chunk_overlap=chunk_config.CHUNK_OVERLAP,
    )

    chunks = text_splitter.split_text(full_text)
    chunked_documents = [Document(page_content=chunk) for chunk in chunks]

    logger.info("Nb of chunked documents: {}", len(chunked_documents))

    chunks_with_ids = [
        Chunk(id=idx, text=doc.page_content)
        for idx, doc in enumerate(chunked_documents)
    ]

    logger.debug("chunks_with_ids {}", chunks_with_ids)

    return chunks_with_ids
