from config import get_settings
from typing import Dict, Any
import logging
from services.gemini_service import get_gemini_service
from services.qdrant_service import get_qdrant_service
from services.pdf_service import get_pdf_parser
from  prompts import cv_evaluation, project_evaluation, final_synthesis
from models import evaluate

settings = get_settings()

class EvaluationPipeline:
    """
    Complete evaluation pipeline implementation
    """

    def __init__(self):
        """Initialize services"""
        self.pdf_parser = get_pdf_parser()
        self.qdrant = get_qdrant_service()
        self.gemini = get_gemini_service()

    async def evaluate(self, cv_id: str, report_id: str, job_title: str) -> Dict[str, Any]:
        """
        Run complete evaluation pipeline
        """

        logging.info(f"Starting evaluation: cv={cv_id}, report={report_id}")

        try:
            cv_text = await self._parse_cv(cv_id)
            logging.debug(f"CV text: {cv_text}")
            project_text = await self._parse_project(report_id)

            logging.debug(f"CV text: {cv_text}")
            cv_result = await self._evaluate_cv(cv_text, job_title)

            logging.info("Evaluating project")
            project_result = await self._evaluate_project(project_text)

            logging.info("Generating final summary")
            overall_summary = await self._generate_summary(cv_result, project_result, job_title)

            # Combine all result
            final_result =  {
                **cv_result,
                **project_result,
                "overall_summary": overall_summary
            }

            logging.info("Evaluation completed")
            return final_result
        except Exception as e:
            logging.error(f"Evaluation failed: {str(e)}")
            raise

    async def _parse_project(self, report_id: str) -> str:
        """Parse project report PDF"""
        file_path = settings.upload_dir / f"project_report_{report_id}.pdf"
        return self.pdf_parser.extract_text(file_path)

    async def _parse_cv(self, cv_id: str) -> str:
        """Parse CV PDF"""
        file_path = settings.upload_dir / f"cv_{cv_id}.pdf"
        return self.pdf_parser.extract_text(file_path)

    async def _evaluate_cv(
            self,
            cv_text: str,
            job_title: str
    ) -> Dict[str, Any]:
        """Evaluate CV with RAG"""

        # Generate query embedding
        query = f"CV evaluation scoring criteria and guidelines for {job_title}: {cv_text[:500]}"
        logging.info(f"Evaluate cv for: {query}")
        query_embedding = await self.gemini.generate_query_embeddings([query])
        query_embedding = query_embedding[0]
        # Retrieve context form Qdrant with source separation
        context = self.qdrant.get_evaluation_context(
            collection_name=settings.qdrant_cv_collection,
            query_embedding=query_embedding,
            separate_sources=True
        )

        # # TODO:
        # rubric_test = self.qdrant.search_with_filter(
        # collection_name=settings.qdrant_cv_collection,
        # query_embedding=query_embedding,
        # source_filter="cv_rubric",
        # top_k=5,
        # score_threshold=0.0
        # )
        # logging.info(f"Direct rubric search found: {len(rubric_test)} chunks")

        # logging.info("Start formatting")

        # Extract context by source
        job_requirements = self._format_context(
            context.get("job_description", [])
        )

        # Extract context by source
        scoring_rubric = self._format_context(
            context.get("cv_rubric", [])
        )

        logging.info(
             f"Retrieved CV context: {len(job_requirements)} chars requirements, "
            f"{len(scoring_rubric)} chars rubric"
        )

        # Generate CV evaluation prompt
        prompt = cv_evaluation.get_cv_evaluation_prompt(
            cv_text=cv_text[:4000],
            job_requirements=job_requirements,
            scoring_rubric=scoring_rubric
        )

        # Call gemini with structured output
        from pydantic import BaseModel

        class CVEvalResponse(BaseModel):
            technical_skills: int
            experience_level: int
            achievements: int
            cultural_fit: int
            cv_feedback: str
            reasoning: dict

        result = await self.gemini.generate_structured_output(
            prompt=prompt,
            expected_model=CVEvalResponse,
            system_instruction=cv_evaluation.CV_SYSTEM_INSTRUCTION,
            temperature=0.2
        )

        logging.info("CV Evaluation result: " + str(result))

        # Calculate scores
        cv_scoring = evaluate.CVScoring(
            technical_skills=result["technical_skills"],
            experience_level=result["experience_level"],
            achievements=result["achievements"],
            cultural_fit=result["cultural_fit"]
        )

        return {
            "cv_match_rate": cv_scoring.match_rate,
            "cv_feedback": result["cv_feedback"],
            "cv_scores": cv_scoring.model_dump(),
            "cv_reasoning": result["reasoning"]
        }

    async def _evaluate_project(
        self,
        project_text: str
    ) -> Dict[str, Any]:
        """Evaluate Project with RAG"""

        # Generate query embedding
        query = f"Evaluate project implementation: {project_text[:500]}"
        query_embedding = await self.gemini.generate_query_embeddings([query])
        logging.info(f"Query embedding: {query_embedding}")
        query_embedding = query_embedding[0]

        # Retrieve context from Qdrant
        context = self.qdrant.get_evaluation_context(
            collection_name=settings.qdrant_project_collection,
            query_embedding=query_embedding,
            separate_sources=True
        )

        # Extract context by source
        case_study_requirements = self._format_context(
            context.get("case_study_brief", [])
        )
        scoring_rubric = self._format_context(
            context.get("project_rubric", [])
        )

        logging.info(
            f"Retrieved Project context: {len(case_study_requirements)} chars requirements, "
            f"{len(scoring_rubric)} chars rubric"
        )

          # Generate project evaluation prompt
        prompt = project_evaluation.get_project_evaluation_prompt(
            project_text=project_text[:4000],  # Limit to avoid token overflow
            case_study_requirements=case_study_requirements,
            scoring_rubric=scoring_rubric
        )

        #  Call Gemini with structured output
        from pydantic import BaseModel

        class ProjectEvalResponse(BaseModel):
            correctness: int
            code_quality: int
            resilience: int
            documentation: int
            creativity: int
            project_feedback: str
            reasoning: dict

        result = await self.gemini.generate_structured_output(
            prompt=prompt,
            expected_model=ProjectEvalResponse,
            system_instruction=project_evaluation.PROJECT_SYSTEM_INSTRUCTION,
            temperature=0.2
        )

        # Calculate scores
        project_scoring = evaluate.ProjectScoring(
            correctness=result["correctness"],
            code_quality=result["code_quality"],
            resilience=result["resilience"],
            documentation=result["documentation"],
            creativity=result["creativity"]
        )

        return {
            "project_score": project_scoring.weighted_score,
            "project_feedback": result["project_feedback"],
            "project_scores": project_scoring.model_dump(),
            "project_reasoning": result["reasoning"]
        }

    async def _generate_summary(
            self,
            cv_result: Dict[str, Any],
            project_result: Dict[str, Any],
            job_title: str
        ) -> str:
            """
            Generate final synthesis summary
            """
            prompt = final_synthesis.get_final_synthesis_prompt(
                cv_match_rate=cv_result["cv_match_rate"],
                cv_feedback=cv_result["cv_feedback"],
                project_score=project_result["project_score"],
                project_feedback=project_result["project_feedback"],
                job_title=job_title
            )

            # Generate summary with slightly higher temperature for natural language
            summary = await self.gemini.generate_with_retry(
                prompt=prompt,
                system_instruction=final_synthesis.SYNTHESIS_SYSTEM_INSTRUCTION,
                temperature=0.4,
                json_mode=False  # Plain text output
            )

            return summary.strip()

    def _format_context(self, contexts: list) -> str:
        """
        Format retrieved contexts into a single string
        """

        if not contexts:
            return "No relevant context found."

        formatted = []
        for i, ctx in enumerate(contexts, 1):
            formatted.append(f"[Context {i}]:\n{ctx.content}\n")

        return "\n".join(formatted)

def get_evaluation_pipeline() -> EvaluationPipeline:
    """Get EvaluationPipeline instance"""
    return EvaluationPipeline()
