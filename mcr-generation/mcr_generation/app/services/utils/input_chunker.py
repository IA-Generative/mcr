from io import BytesIO
from tempfile import NamedTemporaryFile

from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from pydantic import BaseModel

from mcr_generation.app.configs.settings import ChunkingConfig
from mcr_generation.app.exceptions.exceptions import InvalidTranscriptionFileError
from mcr_generation.app.schemas.transcript import FullTranscript

chunk_config = ChunkingConfig()


class Chunk(BaseModel):
    id: int
    text: str


def chunk_docx_to_document_list(docx_bytes: BytesIO) -> list[Chunk]:
    try:
        with NamedTemporaryFile(suffix=".docx") as tmp:
            tmp.write(docx_bytes.getbuffer())
            tmp.flush()

            loader = UnstructuredWordDocumentLoader(tmp.name)
            docs = loader.load()
    except Exception as e:
        raise InvalidTranscriptionFileError(
            f"Failed to parse DOCX transcription: {e}"
        ) from e

    # Combine all page contents into one large text
    full_text = "\n".join([doc.page_content for doc in docs])

    return _split_text_to_chunks(full_text)


def chunk_transcript_to_document_list(full_transcript: FullTranscript) -> list[Chunk]:
    full_text = "\n".join(
        f"{segment.speaker} : {segment.transcription}"
        for segment in full_transcript.segments
    )

    return _split_text_to_chunks(full_text)


def _split_text_to_chunks(full_text: str) -> list[Chunk]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_config.CHUNK_SIZE,
        chunk_overlap=chunk_config.CHUNK_OVERLAP,
    )

    chunks_with_ids = [
        Chunk(id=idx, text=text)
        for idx, text in enumerate(text_splitter.split_text(full_text))
    ]

    logger.info("Nb of chunked documents: {}", len(chunks_with_ids))
    logger.debug("chunks_with_ids {}", chunks_with_ids)

    return chunks_with_ids
