from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func, text

from .database import Base


class BaseAuditMixin:
    """Reusable audit columns for all tables."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100), nullable=False, server_default=text("'system'"))
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Role(Base, BaseAuditMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    division = Column(String(100), nullable=False)

    # Relationships
    reference_documents = relationship("ReferenceDocument", back_populates="role")


class Category(Base, BaseAuditMixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    collection_name = Column(String(50), nullable=False)

    # Relationships
    reference_documents = relationship("ReferenceDocument", back_populates="category")


from sqlalchemy import Enum as SQLEnum
import enum

class ContextStatus(enum.Enum):
    RELATED = "RELATED"
    OPTIONAL = "OPTIONAL"
    DEFAULT = "DEFAULT"
    MANDATORY = "MANDATORY"

class ReferenceDocument(Base, BaseAuditMixin):
    __tablename__ = "reference_documents"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys to roles and categories
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Content
    title = Column(String(255), nullable=False)
    content = Column(JSONB, nullable=False)
    # response_format now nullable to satisfy requirement
    response_format = Column(JSONB, nullable=True)

    # Context usage status
    context_status = Column(
        SQLEnum(ContextStatus, name="context_status_enum"),
        nullable=False,
        server_default=text("'OPTIONAL'")
    )

    # Versioning & Audit
    version = Column(Integer, nullable=False, server_default=text("1"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))

    # Additional metadata (column name 'metadata', mapped to attribute 'metadata_')
    metadata_ = Column('metadata', JSONB, server_default=text("'{}'::jsonb"), nullable=False)

    # Constraints (unique constraint removed per requirement)
    __table_args__ = ()

    # Relationships
    role = relationship("Role", back_populates="reference_documents")
    category = relationship("Category", back_populates="reference_documents")