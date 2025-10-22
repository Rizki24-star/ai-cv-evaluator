import logging
CV_SYSTEM_INSTRUCTION = """You are an expert technical recruiter with 10+ years of experience evaluating backend engineers. You make consistent, fair evaluations based ONLY on provided criteria. You NEVER make assumptions about missing information. You are precise with scoring based on the rubric provided."""

def get_cv_evaluation_prompt(cv_text: str,
    job_requirements: str,
    scoring_rubric: str) -> str:
    logging.info("Generating CV evaluation prompt | req_len=%d | rubric_len=%d", len(job_requirements), len(scoring_rubric))
    """Generate CV evaluation prompt"""
    return f"""Evaluate this candidate's CV for a Backend Product Engineer role.

    JOB REQUIREMENTS:
    {job_requirements}

    SCORING RUBRIC:
    {scoring_rubric}

    CANDIDATE CV:
    {cv_text}

    Evaluate the candidate against these 4 parameters with EXACT scoring:

    1. **Technical Skills Match (Weight: 40%)**
    Requirements: Backend technologies (APIs, databases, cloud), AI/LLM exposure (RAG, prompt engineering, vector DBs)

    Score Guidelines:
    - 1 = Irrelevant skills, no backend experience
    - 2 = Few overlaps, mostly unrelated skills
    - 3 = Partial match, has some backend but missing key areas
    - 4 = Strong match with backend + cloud, missing AI/LLM
    - 5 = Excellent match with backend + cloud + AI/LLM exposure

    Your Score: [Analyze CV carefully]

    2. **Experience Level (Weight: 25%)**
    Requirements: Years of relevant experience and project complexity

    Score Guidelines:
    - 1 = <1 year OR only trivial projects
    - 2 = 1-2 years with simple projects
    - 3 = 2-3 years with mid-scale projects
    - 4 = 3-4 years with solid track record
    - 5 = 5+ years with high-impact projects

    Your Score: [Count years, assess complexity]

    3. **Relevant Achievements (Weight: 20%)**
    Requirements: Measurable impact - scaling, performance improvements, user adoption

    Score Guidelines:
    - 1 = No clear achievements mentioned
    - 2 = Minimal improvements, no metrics
    - 3 = Some measurable outcomes mentioned
    - 4 = Significant contributions with metrics
    - 5 = Major measurable impact (e.g., "reduced latency 60%", "scaled to 1M users")

    Your Score: [Look for numbers and metrics]

    4. **Cultural/Collaboration Fit (Weight: 15%)**
    Requirements: Communication skills, learning mindset, teamwork/leadership

    Score Guidelines:
    - 1 = Not demonstrated in CV
    - 2 = Minimal indicators
    - 3 = Average - mentions team work
    - 4 = Good - clear collaboration examples
    - 5 = Excellent - leadership, mentoring, strong communication demonstrated

    Your Score: [Assess soft skills indicators]

    CRITICAL SCORING RULES:
    - Be STRICT with score 5 - only give if truly exceptional
    - Score 1 means complete absence or irrelevance
    - Most candidates should be in 2-4 range
    - Provide specific CV evidence for each score
    - NO benefit of doubt - score only what's explicitly stated

    Return ONLY this JSON format (no markdown, no code blocks):
    {{
    "technical_skills": <1-5>,
    "experience_level": <1-5>,
    "achievements": <1-5>,
    "cultural_fit": <1-5>,
    "cv_feedback": "<3-5 sentences: key strengths, notable gaps, specific examples from CV>",
    "reasoning": {{
        "technical_skills": "<why this score, cite specific technologies>",
        "experience_level": "<why this score, cite years/projects>",
        "achievements": "<why this score, cite specific achievements>",
        "cultural_fit": "<why this score, cite specific indicators>"
        }}
    }}"""


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
