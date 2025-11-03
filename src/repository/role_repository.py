import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from src.databases.postgres.model import Role
from typing import List
from src.databases.postgres.database import get_db
import src.databases.postgres.model as models

def find_all(db: Session) -> List[Role]:
    result = db.query(models.Role).all()
    logging.info(f"Result query: {result}")
    return result

def find_role_by_name(db: Session, name: str) -> Role:
    result = db.query(models.Role).filter(models.Role.name == name).first()
    logging.info(f"Result query: {result}")
    return result