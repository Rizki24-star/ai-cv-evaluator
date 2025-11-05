import logging

def get_system_instruction(role: str) -> str:
    return f"""You are an expert technical recruiter with 10+ years of experience evaluating {role}. You make consistent, fair evaluations based ONLY on provided criteria. You NEVER make assumptions about missing information. You are precise with scoring based on the rubric provided."""

def get_cv_evaluation_prompt(
    role: str = "the specified role",
    cv_text: str = "",
    job_requirements: str = "",
    scoring_rubric: str = "",
    response_format: str = ""
) -> str:
    """
    Generate CV evaluation prompt.
    All params are optional to maintain backward compatibility with older call sites.
    """
    # Provide a safe default response format if not supplied
    if not response_format:
        response_format = (
            '{"technical_skills": 1, '
            '"experience_level": 1, '
            '"achievements": 1, '
            '"cultural_fit": 1, '
            '"cv_feedback": "", '
            '"reasoning": {}}'
        )
    logging.info(
        "Generating CV evaluation prompt | req_len=%d | rubric_len=%d",
        len(job_requirements),
        len(scoring_rubric)
    )
    return f"""Evaluate this candidate's CV for a {role} role.

    JOB REQUIREMENTS:
    {job_requirements}

    SCORING RUBRIC:
    {scoring_rubric}

    CANDIDATE CV:
    {cv_text}

    Return ONLY this JSON format (no markdown, no code blocks):
    {response_format}"""


# Few-shot examples for consistency
CV_FEW_SHOT_EXAMPLES = """
EXAMPLE 1:
CV: "3 years Python backend, built REST APIs with Django, deployed on AWS, optimized DB queries reducing load time by 40%"
Job: Backend + Cloud + 2+ years

Scores:
- technical_skills: 4 (strong backend + cloud, but NO AI/LLM mentioned)
- experience_level: 4 (3 years solid, good complexity)
- achievements: 4 (clear metric: 40% improvement)
- cultural_fit: 2 (no team/communication indicators)

EXAMPLE 2:
CV: "5 years backend, implemented RAG system with Pinecone, fine-tuned prompts for chatbot, led team of 3 engineers"
Job: Backend + AI/LLM

Scores:
- technical_skills: 5 (backend + direct RAG/LLM experience)
- experience_level: 5 (5+ years, complex AI project)
- achievements: 3 (project mentioned but no metrics)
- cultural_fit: 5 (leadership + team leading)

EXAMPLE 3:
CV: "1 year junior developer, built simple CRUD app with Express.js"
Job: Backend + AI/LLM

Scores:
- technical_skills: 2 (minimal backend, no AI)
- experience_level: 1 (<2 years, trivial project)
- achievements: 1 (no achievements mentioned)
- cultural_fit: 1 (not demonstrated)
"""
