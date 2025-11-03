import logging
from sqlalchemy.orm import Session
from typing import List
import src.databases.postgres.model as models

def find_all(db: Session) -> List[models.Category]:
    """Fetch all category"""
    result = (db.query(models.Category).all())
    logging.info(f"Result query: {result}")
    return result