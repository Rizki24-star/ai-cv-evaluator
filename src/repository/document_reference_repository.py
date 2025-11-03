import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List
import src.databases.postgres.model as models
from typing import Optional
from sqlalchemy import exc as sa_exc

def find_docs_by_role_id_and_titles(db: Session, role_id: int, title: List[str]) -> List[models.ReferenceDocument]:
    result = (
        db.query(models.ReferenceDocument)
        .options(
            joinedload(models.ReferenceDocument.category)
        )
        .filter(models.ReferenceDocument.role_id == role_id)
        .filter(models.ReferenceDocument.title.in_(title))
        .all()
    )
    logging.info(f"Result query: {result}")
    return result

def find_doc_by_role_id_and_title(db: Session, role_id: int, title) -> models.ReferenceDocument:
    result = (
        db.query(models.ReferenceDocument)
        .options(
            joinedload(models.ReferenceDocument.category)
        )
        .filter(models.ReferenceDocument.role_id == role_id)
        .filter(models.ReferenceDocument.title.in_(title))
        .first()
    )
    logging.info(f"Result query: {result}")
    return result

def find_doc_by_ids(db: Session, ids: List[int]) -> List[models.ReferenceDocument]:
    result = (
        db.query(models.ReferenceDocument)
        .options(
            joinedload(models.ReferenceDocument.category)
        )
        .filter(models.ReferenceDocument.id.in_(ids))
        .all()
    )
    logging.info(f"Result query: {result}")
    return result


def find_mandatory_by_role_and_categories(db: Session, role_id: int, categories: List[str]) -> List[models.ReferenceDocument]:
    """Fetch DEFAULT docs for a role filtered by category names (e.g., ['CV'] or ['Project']).
    Note: Historically called 'mandatory'; now uses ContextStatus.DEFAULT per new spec.
    Falls back to ignoring context_status filter if database enum values mismatch.
    """
    try:
        result = (
            db.query(models.ReferenceDocument)
            .join(models.Category, models.ReferenceDocument.category_id == models.Category.id)
            .options(joinedload(models.ReferenceDocument.category))
            .filter(
                models.ReferenceDocument.role_id == role_id,
                models.ReferenceDocument.is_active == True,
                models.ReferenceDocument.context_status == models.ContextStatus.DEFAULT,
                models.Category.name.in_(categories),
            )
            .all()
        )
        logging.info(f"Default docs for role {role_id} categories {categories}: {result}")
        return result
    except sa_exc.DataError as e:
        logging.warning(f"Enum filter failed for context_status DEFAULT, falling back without status filter: {e}")
        db.rollback()
        result = (
            db.query(models.ReferenceDocument)
            .join(models.Category, models.ReferenceDocument.category_id == models.Category.id)
            .options(joinedload(models.ReferenceDocument.category))
            .filter(
                models.ReferenceDocument.role_id == role_id,
                models.ReferenceDocument.is_active == True,
                models.Category.name.in_(categories),
            )
            .all()
        )
        return result


def find_default_and_mandatory_by_role_and_categories(db: Session, role_id: int, categories: List[str]) -> List[models.ReferenceDocument]:
    """Fetch documents with context_status in {DEFAULT, MANDATORY} for a role filtered by category names.
    Includes eager-loaded category to access collection_name and other fields.
    Falls back to ignoring context_status filter if database enum values mismatch.
    """
    try:
        result = (
            db.query(models.ReferenceDocument)
            .join(models.Category, models.ReferenceDocument.category_id == models.Category.id)
            .options(joinedload(models.ReferenceDocument.category))
            .filter(
                models.ReferenceDocument.role_id == role_id,
                models.ReferenceDocument.is_active == True,
                models.ReferenceDocument.context_status.in_([models.ContextStatus.DEFAULT, models.ContextStatus.MANDATORY]),
                models.Category.name.in_(categories),
            )
            .all()
        )
        logging.info(f"Default+Mandatory docs for role {role_id} categories {categories}: {result}")
        return result
    except sa_exc.DataError as e:
        logging.warning(f"Enum filter failed for context_status IN (DEFAULT, MANDATORY), falling back without status filter: {e}")
        db.rollback()
        result = (
            db.query(models.ReferenceDocument)
            .join(models.Category, models.ReferenceDocument.category_id == models.Category.id)
            .options(joinedload(models.ReferenceDocument.category))
            .filter(
                models.ReferenceDocument.role_id == role_id,
                models.ReferenceDocument.is_active == True,
                models.Category.name.in_(categories),
            )
            .all()
        )
        return result