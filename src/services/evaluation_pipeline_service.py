from src.config import get_settings
from typing import Dict, Any, List
import logging
from src.services.gemini_service import get_gemini_service
from src.services.qdrant_service import get_qdrant_service
from src.services.pdf_service import get_pdf_parser
from src.prompts import cv_evaluation, project_evaluation, final_synthesis

from src.databases.postgres.database import sessionLocal
from src.repository import document_reference_repository, role_repository
import json
from src.utils.validator import normalize_json_fields, clean_json_string

settings = get_settings()

def _json_to_block(title: str, data: dict) -> str:
    """Render JSON content into a readable block with a title header."""
    try:
        body = json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        body = str(data)
    return f"=== {title} ===\n{body}"

class EvaluationPipeline:
    """
    Complete evaluation pipeline implementation
    """

    def __init__(self):
        """Initialize services"""
        self.pdf_parser = get_pdf_parser()
        self.qdrant = get_qdrant_service()
        self.gemini = get_gemini_service()
        self.db = sessionLocal()

    async def evaluate(self, cv_id: str, cv_context: List[int], report_id: str, project_context: List[int], job_title: str) -> Dict[str, Any]:
        """
        Run complete evaluation pipeline
        """

        logging.info(f"Starting evaluation: cv={cv_id}, report={report_id}")

        try:
            # Get role information
            role = role_repository.find_role_by_name(self.db, job_title)
            if not role:
                raise ValueError(f"Role not found: {job_title}")

            cv_text = await self._parse_cv(cv_id)
            project_text = await self._parse_project(report_id)

            logging.info("Evaluating CV")
            cv_result = await self._evaluate_cv(cv_text, cv_context, job_title, role.id)

            logging.info("Evaluating project")
            project_result = await self._evaluate_project(project_text, project_context, job_title, role.id)

            logging.info("Generating final summary")
            overall_summary = await self._generate_summary(cv_result, project_result, job_title)

            # Build only dynamic formatted_result; avoid hardcoded top-level schema
            formatted_result = {
                "cv": cv_result.get("cv_formatted"),
                "project": project_result.get("project_formatted"),
            }

            final_result = {
                "job_title": job_title,
                "overall_summary": overall_summary,
                "formatted_result": formatted_result,
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
            cv_context: List[int],
            job_title: str,
            role_id: int,
    ) -> Dict[str, Any]:
        """Evaluate CV using mandatory rubric (full) + optional JD from Qdrant"""
        # Prepare rubric/context documents: use DEFAULT and MANDATORY as prompting blocks (with titles)
        cv_docs_for_prompt = document_reference_repository.find_default_and_mandatory_by_role_and_categories(self.db, role_id, ["CV"]) 
        rubric_blocks: List[str] = []
        for doc in cv_docs_for_prompt:
            rubric_blocks.append(_json_to_block(doc.title, doc.content))
        scoring_rubric = "\n\n".join(rubric_blocks) if rubric_blocks else "No rubric provided."

        # Optional contexts from Qdrant using provided ReferenceDocument IDs (e.g., Job Description)
        optional_docs = document_reference_repository.find_doc_by_ids(self.db, cv_context)

        # Generate query embedding
        query = f"CV evaluation scoring criteria and guidelines for {job_title}: {cv_text[:500]}"
        logging.info(f"Evaluate cv for: {query}")
        query_embedding_list = await self.gemini.generate_query_embeddings([query])
        query_embedding = query_embedding_list[0]

        # Retrieve JD context from Qdrant by each provided optional doc
        jd_contexts_all = []
        for doc in optional_docs:
            collection_name = doc.category.collection_name
            # Map category to source filter
            # Note: some existing ingestions may not tag 'source' properly; search without source filter for robustness
            jd_contexts = self.qdrant.search_with_filter(
                collection_name=collection_name,
                query_embedding=query_embedding,
                source_filter=None,
                top_k=3,
                score_threshold=settings.rag_score_threshold,
            )
            jd_contexts_all.extend(jd_contexts)

        job_requirements = self._format_context(jd_contexts_all)


        logging.info(
            f"Retrieved CV context blocks: JD={len(jd_contexts_all)}; rubric blocks={len(rubric_blocks)}"
        )

        # Prepare response format taken from the first DEFAULT doc (fallback to first available) 
        cv_response_format_obj = None
        # pick first DEFAULT doc with non-null response_format
        default_docs = [d for d in cv_docs_for_prompt if getattr(getattr(d, 'context_status', None), 'name', '') == 'DEFAULT']
        for d in default_docs:
            if getattr(d, 'response_format', None):
                cv_response_format_obj = d.response_format
                break
        # fallback: any doc with response_format
        if cv_response_format_obj is None:
            for d in cv_docs_for_prompt:
                if getattr(d, 'response_format', None):
                    cv_response_format_obj = d.response_format
                    break
        cv_response_format = json.dumps(cv_response_format_obj, ensure_ascii=False, indent=2) if cv_response_format_obj else '{"scores": {"technical_skills": 1, "experience_level": 1, "achievements": 1, "cultural_fit": 1}, "cv_feedback": "", "reasoning": {}}'

        # Generate CV evaluation prompt (build inline to avoid import signature issues)
        prompt = (
            f"Evaluate this candidate's CV for a {job_title} role.\n\n"
            f"JOB REQUIREMENTS:\n{job_requirements}\n\n"
            f"SCORING RUBRIC:\n{scoring_rubric}\n\n"
            f"CANDIDATE CV:\n{cv_text[:4000]}\n\n"
            f"Return ONLY this JSON using EXACTLY the following JSON schema.\n"
            f"- The output must be valid JSON parseable by json.loads().\n"
            f"- Use only the keys provided in the schema; do not add or rename keys.\n"
            f"- Replace any placeholder/example values with real values.\n"
            f"- For numeric fields, output JSON numbers (e.g., 3 or 4.5), not strings.\n"
            f"- Do not wrap the JSON in code fences or add any explanations.\n"
            f"Schema:\n{cv_response_format}"
        )

        # Ask LLM to produce JSON exactly in the specified response_format (dynamic)
        try:
            formatted_text = await self.gemini.generate_with_retry(
                prompt=prompt,
                system_instruction=cv_evaluation.get_system_instruction(job_title),
                temperature=0.1,
                json_mode=True,
            )
            # First attempt to parse as-is
            try:
                cv_formatted = json.loads(formatted_text)
            except Exception:
                # Fallback: clean typical artifacts like ```json fences and retry
                cleaned = clean_json_string(formatted_text)
                cv_formatted = json.loads(cleaned)
            # Unwrap nested {"cv": {...}} if present and normalize
            if isinstance(cv_formatted, dict) and isinstance(cv_formatted.get("cv"), dict):
                cv_formatted = cv_formatted["cv"]
            cv_formatted = normalize_json_fields(cv_formatted)
        except Exception as e:
            logging.error(f"Failed to generate CV formatted result by response_format: {e}")
            cv_formatted = None

        # Return only dynamic formatted output to avoid hardcoded schema
        return {
            "cv_formatted": cv_formatted,
        }

    async def _evaluate_project(
        self,
        project_text: str,
        project_context: List[int],
        job_title: str,
        role_id: int,
    ) -> Dict[str, Any]:
        """Evaluate Project using mandatory rubric (full) + optional Case Study from Qdrant"""

        # Prepare rubric/context documents: use DEFAULT and MANDATORY as prompting blocks (with titles)
        proj_docs_for_prompt = document_reference_repository.find_default_and_mandatory_by_role_and_categories(self.db, role_id, ["Project"])
        rubric_blocks: List[str] = []
        for doc in proj_docs_for_prompt:
            rubric_blocks.append(_json_to_block(doc.title, doc.content))
        scoring_rubric = "\n\n".join(rubric_blocks) if rubric_blocks else "No rubric provided."

        # Optional contexts from Qdrant using provided ReferenceDocument IDs (e.g., Case Study Brief)
        optional_docs = document_reference_repository.find_doc_by_ids(self.db, project_context)

        # Generate query embedding
        query = f"Evaluate project implementation for {job_title}: {project_text[:500]}"
        query_embedding_list = await self.gemini.generate_query_embeddings([query])
        logging.info(f"Query embedding generated for project")
        query_embedding = query_embedding_list[0]

        # Retrieve Case Study context from Qdrant by each provided optional doc
        cs_contexts_all = []
        for doc in optional_docs:
            collection_name = doc.category.collection_name
            # Map to source
            title_lower = (doc.title or "").lower()
            source = "case_study_brief" if "case study" in title_lower else None
            if not source:
                continue
            cs_contexts = self.qdrant.search_with_filter(
                collection_name=collection_name,
                query_embedding=query_embedding,
                source_filter=source,
                top_k=3,
                score_threshold=settings.rag_score_threshold,
            )
            cs_contexts_all.extend(cs_contexts)

        case_study_requirements = self._format_context(cs_contexts_all)

        logging.info(
            f"Retrieved Project context blocks: CaseStudy={len(cs_contexts_all)}; rubric blocks={len(rubric_blocks)}"
        )

        # Prepare response format from DEFAULT project doc if available
        proj_response_format_obj = None
        default_proj_docs = [d for d in proj_docs_for_prompt if getattr(getattr(d, 'context_status', None), 'name', '') == 'DEFAULT']
        for d in default_proj_docs:
            if getattr(d, 'response_format', None):
                proj_response_format_obj = d.response_format
                break
        if proj_response_format_obj is None:
            for d in proj_docs_for_prompt:
                if getattr(d, 'response_format', None):
                    proj_response_format_obj = d.response_format
                    break
        proj_response_format = json.dumps(proj_response_format_obj, ensure_ascii=False, indent=2) if proj_response_format_obj else None

        # Build dynamic project prompt (avoid hard-coded schema)
        if proj_response_format:
            prompt = (
                "Evaluate this candidate's project submission.\n\n"
                f"CASE STUDY REQUIREMENTS:\n{case_study_requirements}\n\n"
                f"SCORING RUBRIC:\n{scoring_rubric}\n\n"
                f"PROJECT REPORT/CODE:\n{project_text[:4000]}\n\n"
                f"Return ONLY this JSON using EXACTLY the following JSON schema.\n"
                f"- The output must be valid JSON parseable by json.loads().\n"
                f"- Use only the keys provided in the schema; do not add or rename keys.\n"
                f"- Replace any placeholder/example values with real values.\n"
                f"- For numeric fields, output JSON numbers (e.g., 3 or 4.5), not strings.\n"
                f"- Do not wrap the JSON in code fences or add any explanations.\n"
                f"Schema:\n{proj_response_format}"
            )
        else:
            # Fallback to existing textual prompt if no response_format supplied
            prompt = project_evaluation.get_project_evaluation_prompt(
                project_text=project_text[:4000],
                case_study_requirements=case_study_requirements,
                scoring_rubric=scoring_rubric,
            )

        # Generate JSON output dynamically
        try:
            formatted_text = await self.gemini.generate_with_retry(
                prompt=prompt,
                system_instruction=project_evaluation.PROJECT_SYSTEM_INSTRUCTION,
                temperature=0.2,
                json_mode=True,
            )
            # First attempt to parse as-is
            try:
                project_formatted = json.loads(formatted_text)
            except Exception:
                # Fallback: clean typical artifacts like ```json fences and retry
                cleaned = clean_json_string(formatted_text)
                project_formatted = json.loads(cleaned)
            # Unwrap nested {"project": {...}} if present and normalize
            if isinstance(project_formatted, dict) and isinstance(project_formatted.get("project"), dict):
                project_formatted = project_formatted["project"]
            project_formatted = normalize_json_fields(project_formatted)
        except Exception as e:
            logging.error(f"Failed to generate Project formatted result: {e}")
            project_formatted = None

        # Return only dynamic formatted output to avoid hardcoded schema
        return {
            "project_formatted": project_formatted,
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
            # Derive optional summary inputs dynamically from formatted results
            cv_formatted = cv_result.get("cv_formatted") or {}
            project_formatted = project_result.get("project_formatted") or {}

            # Try to extract feedbacks
            cv_feedback = None
            if isinstance(cv_formatted, dict):
                cv_feedback = cv_formatted.get("cv_feedback") or cv_formatted.get("feedback")

            project_feedback = None
            if isinstance(project_formatted, dict):
                project_feedback = project_formatted.get("project_feedback") or project_formatted.get("feedback")

            # Compute simple scores if present (best-effort)
            def _avg_from_scores(obj: Any) -> Any:
                if not isinstance(obj, dict):
                    return None
                numeric_values = [v for v in obj.values() if isinstance(v, (int, float))]
                if numeric_values:
                    return round(sum(numeric_values) / len(numeric_values), 3)
                return None

            cv_match_rate = None
            if isinstance(cv_formatted, dict):
                # Support multiple score key variants and nested shapes
                nested_cv = cv_formatted.get("cv") if isinstance(cv_formatted.get("cv"), dict) else None
                scores_obj = (
                    cv_formatted.get("scores")
                    or cv_formatted.get("cv_scores")
                    or cv_formatted.get("scores_cv")
                    or (nested_cv.get("scores") if nested_cv else None)
                    or (nested_cv.get("cv_scores") if nested_cv else None)
                )
                avg = _avg_from_scores(scores_obj)
                if isinstance(avg, (int, float)):
                    # Normalize 1-5 to 0-1 if looks like 1-5
                    cv_match_rate = round(float(avg) / 5.0, 3)

            project_score = None
            if isinstance(project_formatted, dict):
                nested_proj = project_formatted.get("project") if isinstance(project_formatted.get("project"), dict) else None
                scores_obj = (
                    project_formatted.get("scores")
                    or project_formatted.get("project_scores")
                    or (nested_proj.get("scores") if nested_proj else None)
                    or (nested_proj.get("project_scores") if nested_proj else None)
                    or project_formatted
                )
                avg = _avg_from_scores(scores_obj)
                if isinstance(avg, (int, float)):
                    project_score = round(float(avg), 2)

            # Final guard defaults to avoid None in downstream prompts/operations
            cv_feedback = cv_feedback or ""
            project_feedback = project_feedback or ""
            if not isinstance(cv_match_rate, (int, float)):
                cv_match_rate = 0.0
            if not isinstance(project_score, (int, float)):
                project_score = 0.0

            prompt = final_synthesis.get_final_synthesis_prompt(
                cv_match_rate=cv_match_rate,
                cv_feedback=cv_feedback,
                project_score=project_score,
                project_feedback=project_feedback,
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
