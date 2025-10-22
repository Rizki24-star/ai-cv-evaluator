PROJECT_SYSTEM_INSTRUCTION = """You are a senior technical reviewer evaluating a candidate's project submission for a backend engineering role. You assess code quality, architecture decisions, and production-readiness. You are thorough and fair, scoring based only on evidence in the project report."""


def get_project_evaluation_prompt(
    project_text: str,
    case_study_requirements: str,
    scoring_rubric: str
) -> str:
    """
    Generate project evaluation prompt
    """
    return f"""Evaluate this candidate's project submission against the case study requirements.

CASE STUDY REQUIREMENTS:
{case_study_requirements}

SCORING RUBRIC:
{scoring_rubric}

PROJECT REPORT/CODE:
{project_text}

Evaluate against these 5 parameters:

1. **Correctness - Prompt & Chaining (Weight: 30%)**
   Requirements: Implements prompt design, LLM chaining (multi-stage), RAG context injection

   Score Guidelines:
   - 1 = Not implemented, missing core features
   - 2 = Minimal attempt, incomplete implementation
   - 3 = Works partially, some features missing
   - 4 = Works correctly, all required features present
   - 5 = Fully correct + thoughtful design choices

   Your Score: [Check for: prompts, chain stages, RAG integration]

2. **Code Quality & Structure (Weight: 25%)**
   Requirements: Clean, modular, reusable code with tests

   Score Guidelines:
   - 1 = Poor quality, monolithic, no structure
   - 2 = Some structure but messy
   - 3 = Decent modularity, acceptable quality
   - 4 = Good structure + some tests
   - 5 = Excellent quality + strong test coverage

   Your Score: [Assess architecture, separation of concerns]

3. **Resilience & Error Handling (Weight: 20%)**
   Requirements: Handles long-running jobs, retries, API failures, randomness control

   Score Guidelines:
   - 1 = Missing entirely, no error handling
   - 2 = Minimal try-catch, no retry logic
   - 3 = Partial handling, basic retries
   - 4 = Solid handling with exponential backoff
   - 5 = Production-ready with comprehensive safeguards

   Your Score: [Look for: async processing, retry mechanisms, fallbacks]

4. **Documentation & Explanation (Weight: 15%)**
   Requirements: Clear README, setup instructions, architecture explanation, trade-off discussions

   Score Guidelines:
   - 1 = Missing or inadequate
   - 2 = Minimal documentation
   - 3 = Adequate, covers basics
   - 4 = Clear and complete
   - 5 = Excellent + insightful design rationale

   Your Score: [Assess documentation quality]

5. **Creativity / Bonus Features (Weight: 10%)**
   Requirements: Features beyond requirements (auth, deployment, UI, monitoring, etc.)

   Score Guidelines:
   - 1 = None, bare minimum only
   - 2 = Very basic extras
   - 3 = Useful additional features
   - 4 = Strong enhancements
   - 5 = Outstanding creativity and polish

   Your Score: [Identify bonus features]

SCORING GUIDELINES:
- Be objective - score what's actually implemented
- Score 5 requires exceptional quality
- Look for evidence in code/documentation
- Consider production-readiness
- Note both strengths and weaknesses

Return ONLY this JSON format (no markdown, no code blocks):
{{
  "correctness": <1-5>,
  "code_quality": <1-5>,
  "resilience": <1-5>,
  "documentation": <1-5>,
  "creativity": <1-5>,
  "project_feedback": "<3-5 sentences: what works well, what's missing, specific suggestions>",
  "reasoning": {{
    "correctness": "<why this score, cite specific implementations>",
    "code_quality": "<why this score, cite architecture patterns>",
    "resilience": "<why this score, cite error handling examples>",
    "documentation": "<why this score, cite README quality>",
    "creativity": "<why this score, list bonus features>"
  }}
}}"""
