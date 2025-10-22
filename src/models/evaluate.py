from pydantic import BaseModel, Field, field_validator
from models.job import JobStatus
from typing import Optional

class EvaluateRequest(BaseModel):
    """Evaluation Request"""
    cv_id: str = Field(...)
    report_id: str = Field(...)
    job_title: str = Field(...)

    @field_validator('job_title')
    def validate_job_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Job title cannot be empty')
        return v.strip()

class EvaluateResponse(BaseModel):
        """Evaluation response - immediate"""
        id: str
        status: JobStatus
class CVScoring (BaseModel):
    """
    CV Evaluation Scores based on rubric
    """

    technical_skills: int = Field(ge=1, le=5, description="Weight: 40%")
    experience_level: int = Field(ge=1, le=5, description="Weight: 25%")
    achievements: int = Field(ge=1, le=5, description="Weight: 20%")
    cultural_fit: int = Field(ge=1, le=5, description="Weight: 15%")

    @property
    def weighted_score(self) -> float:
        """Calculate weighted average (1-5 scale)"""
        score = (
            self.technical_skills * 0.40 +
            self.experience_level * 0.25 +
            self.achievements * 0.20 +
            self.cultural_fit * 0.15
        )
        return round(score, 2)

    @property
    def match_rate(self) -> float:
        """Convert to 0-1 decimal as per requirement"""
        return round(self.weighted_score * 0.2, 3)

class ProjectScoring(BaseModel):
    """
    Project Evaluation Scores based on rubric
    """

    correctness: int = Field(ge=1, le=5, description="Weight: 30%")
    code_quality: int = Field(ge=1, le=5, description="Weight: 25%")
    resilience: int = Field(ge=1, le=5, description="Weight: 20%")
    documentation: int = Field(ge=1, le=5, description="Weight: 15%")
    creativity: int = Field(ge=1, le=5, description="Weight: 10%")

    @property
    def weighted_score(self) -> float:
        """Calculate weighted average (1-5 scale)"""
        score = (
            self.correctness * 0.30 +
            self.code_quality * 0.25 +
            self.resilience * 0.20 +
            self.documentation * 0.15 +
            self.creativity * 0.10
        )
        return round(score, 2)

class ScoringReasoning(BaseModel):
    """Reasoning for each score"""
    technical_skills: Optional[str] = None
    experience_level: Optional[str] = None
    achievements: Optional[str] = None
    cultural_fit: Optional[str] = None
    correctness: Optional[str] = None
    code_quality: Optional[str] = None
    resilience: Optional[str] = None
    documentation: Optional[str] = None
    creativity: Optional[str] = None


class EvaluationResultResponse(BaseModel):
    """
    Complete evaluation result
    """
    id: str
    status: JobStatus

    # CV Evaluation Results
    cv_match_rate: Optional[float] = Field(None, ge=0, le=1)
    cv_feedback: Optional[str] = None
    cv_scores: Optional[CVScoring] = None
    cv_reasoning: Optional[ScoringReasoning] = None

    # Project Evaluation Results
    project_score: Optional[float] = Field(None, ge=1, le=5)
    project_feedback: Optional[str] = None
    project_scores: Optional[ProjectScoring] = None
    project_reasoning: Optional[ScoringReasoning] = None

    # Final Summary
    overall_summary: Optional[str] = None

    # Metadata
    job_title: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None

    # Error handling
    error: Optional[str] = None
    retry_count: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "cv_match_rate": 0.82,
                "cv_feedback": "Strong backend and cloud skills, limited AI integration experience...",
                "project_score": 4.5,
                "project_feedback": "Meets prompt chaining requirements, lacks error handling robustness...",
                "overall_summary": "Good candidate fit, would benefit from deeper RAG knowledge...",
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:31:30Z",
                "completed_at": "2025-01-15T10:31:30Z"
            }
        }
