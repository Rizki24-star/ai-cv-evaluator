import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.services.qdrant_service import get_qdrant_service
from src.services.gemini_service import get_gemini_service
from src.services.pdf_service import get_pdf_parser
from src.models.qdrant import ChunkMetadata
import logging

settings = get_settings()


async def chunk_text(
    text: str,
    source: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> list[ChunkMetadata]:
    """
    chunking based on document type
    """
    pdf_parser = get_pdf_parser()


    if "rubric" in source:
        try:
            sections = pdf_parser.chunk_by_sections(text)
            if sections:
                logging.info(f"Using section-based chunking for {source}")
                chunks = []
                for i, (section, content) in enumerate(sections):
                    chunks.append(
                        ChunkMetadata(
                            source=source,
                            content=f"{section}\n\n{content}",
                            chunk_index=i,
                            section=section
                        )
                    )
                return chunks
        except Exception as e:
            logging.warning(f"Section chunking failed: {e}, using word-based")

    word_chunks = pdf_parser.chunk_text(text, chunk_size, overlap)

    chunks = []
    for i, chunk_text in enumerate(word_chunks):
        chunks.append(
            ChunkMetadata(
                source=source,
                content=chunk_text,
                chunk_index=i
            )
        )

    return chunks


async def ingest_cv_evaluation_docs():
    """
    Ingest documents for CV evaluation:
    - Job Description
    - CV Scoring Rubric
    """

    qdrant = get_qdrant_service()
    gemini = get_gemini_service()
    pdf_parser = get_pdf_parser()

    all_chunks = []

    # 1. Job Description
    logging.info("\n Processing Job Description...")
    job_desc_path = settings.reference_docs_dir / settings.job_description_file

    if not job_desc_path.exists():
        logging.error(f"Job description not found: {job_desc_path}")
        logging.info("Please add job_description.pdf to reference_docs/")
        return

    job_text = pdf_parser.extract_text(job_desc_path)
    logging.info(f"Extracted {len(job_text)} characters")

    job_chunks = await chunk_text(
        job_text,
        source="job_description",
        chunk_size=500,
        overlap=50
    )
    logging.info(f"Created {len(job_chunks)} chunks")
    all_chunks.extend(job_chunks)

    # 2. CV Scoring Rubric
    logging.info("\n Processing CV Scoring Rubric...")
    cv_rubric_path = settings.reference_docs_dir / settings.cv_rubric_file

    if not cv_rubric_path.exists():
        logging.error(f"CV rubric not found: {cv_rubric_path}")
        logging.info("Please add cv_scoring_rubric.pdf to reference_docs/")
        return

    rubric_text = pdf_parser.extract_text(cv_rubric_path)
    logging.info(f"Extracted {len(rubric_text)} characters")

    rubric_chunks = await chunk_text(
        rubric_text,
        source="cv_rubric",
        chunk_size=400,
        overlap=30
    )
    logging.info(f"Created {len(rubric_chunks)} chunks")
    all_chunks.extend(rubric_chunks)

    # 3. Generate embeddings
    logging.info(f"\nGenerating embeddings for {len(all_chunks)} chunks...")
    texts = [chunk.content for chunk in all_chunks]
    embeddings = await gemini.generate_embeddings(texts)
    logging.info(f"Generated {len(embeddings)} embeddings")

    # 4. Ingest to Qdrant
    logging.info(f"\nIngesting to Qdrant collection: {settings.qdrant_cv_collection}")
    count = qdrant.ingest_documents(
        collection_name=settings.qdrant_cv_collection,
        chunks=all_chunks,
        embeddings=embeddings
    )

    logging.info(f"Successfully ingested {count} chunks for CV evaluation")


async def ingest_project_evaluation_docs():
    """
    Ingest documents for Project evaluation:
    - Case Study Brief
    - Project Scoring Rubric
    """
    logging.info("\n" + "=" * 60)
    logging.info("INGESTING PROJECT EVALUATION DOCUMENTS")
    logging.info("=" * 60)

    qdrant = get_qdrant_service()
    gemini = get_gemini_service()
    pdf_parser = get_pdf_parser()

    all_chunks = []

    # 1. Case Study Brief
    logging.info("\nProcessing Case Study Brief...")
    case_study_path = settings.reference_docs_dir / settings.case_study_file

    if not case_study_path.exists():
        logging.error(f"Case study not found: {case_study_path}")
        logging.info("Please add case_study_brief.pdf to reference_docs/")
        return

    case_text = pdf_parser.extract_text(case_study_path)
    logging.info(f"Extracted {len(case_text)} characters")

    case_chunks = await chunk_text(
        case_text,
        source="case_study_brief",
        chunk_size=500,
        overlap=50
    )
    logging.info(f"Created {len(case_chunks)} chunks")
    all_chunks.extend(case_chunks)

    # 2. Project Scoring Rubric
    logging.info("\nProcessing Project Scoring Rubric...")
    project_rubric_path = settings.reference_docs_dir / settings.project_rubric_file

    if not project_rubric_path.exists():
        logging.error(f"Project rubric not found: {project_rubric_path}")
        logging.info("Please add project_scoring_rubric.pdf to reference_docs/")
        return

    rubric_text = pdf_parser.extract_text(project_rubric_path)
    logging.info(f"Extracted {len(rubric_text)} characters")

    rubric_chunks = await chunk_text(
        rubric_text,
        source="project_rubric",
        chunk_size=400,
        overlap=30
    )
    logging.info(f"Created {len(rubric_chunks)} chunks")
    all_chunks.extend(rubric_chunks)

    # 3. Generate embeddings
    logging.info(f"\nGenerating embeddings for {len(all_chunks)} chunks...")
    texts = [chunk.content for chunk in all_chunks]
    embeddings = await gemini.generate_embeddings(texts)
    logging.info(f"Generated {len(embeddings)} embeddings")

    # 4. Ingest to Qdrant
    logging.info(f"\nIngesting to Qdrant collection: {settings.qdrant_project_collection}")
    count = qdrant.ingest_documents(
        collection_name=settings.qdrant_project_collection,
        chunks=all_chunks,
        embeddings=embeddings
    )

    logging.info(f"Successfully ingested {count} chunks for project evaluation")


async def main():
    """
    Main ingestion workflow
    """
    logging.info("Starting document ingestion process...")

    try:
        # Initialize Qdrant and create collections
        logging.info("\nInitializing Qdrant collections...")
        qdrant = get_qdrant_service()
        qdrant.create_collections()

        # Ingest CV evaluation documents
        await ingest_cv_evaluation_docs()

        # Ingest Project evaluation documents
        await ingest_project_evaluation_docs()

        # Show collection info
        logging.info("\n" + "=" * 60)
        logging.info("INGESTION COMPLETE")
        logging.info("=" * 60)

        cv_info = qdrant.get_collection_info(settings.qdrant_cv_collection)
        project_info = qdrant.get_collection_info(settings.qdrant_project_collection)

        logging.info(f"\nCV Evaluation Collection:")
        logging.info(f"  - Points: {cv_info.get('points_count', 0)}")
        logging.info(f"  - Status: {cv_info.get('status', 'unknown')}")

        logging.info(f"\nProject Evaluation Collection:")
        logging.info(f"  - Points: {project_info.get('points_count', 0)}")
        logging.info(f"  - Status: {project_info.get('status', 'unknown')}")

        logging.info("\n✅ All documents ingested successfully!")
        logging.info("You can now start the API server and begin evaluations.\n")

    except Exception as e:
        logging.error(f"\n❌ Ingestion failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

