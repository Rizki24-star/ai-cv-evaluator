SYNTHESIS_SYSTEM_INSTRUCTION = """You are a hiring manager making a final assessment of a candidate. You synthesize technical evaluation results into a clear, actionable recommendation. You are direct and specific."""


def get_final_synthesis_prompt(
    cv_match_rate: float,
    cv_feedback: str,
    project_score: float,
    project_feedback: str,
    job_title: str
) -> str:
    """
    Generate final synthesis prompt
    """
    # Convert match rate to percentage for readability
    cv_percentage = int(cv_match_rate * 100)

    return f"""You are evaluating a candidate for the {job_title} position.

    CV EVALUATION:
    - Match Rate: {cv_percentage}% ({cv_match_rate:.2f}/1.00)
    - Feedback: {cv_feedback}

    PROJECT EVALUATION:
    - Score: {project_score}/5.0
    - Feedback: {project_feedback}

    TASK: Write a 3-5 sentence overall_summary that synthesizes both evaluations.

    Your summary MUST cover:
    1. **Overall Fit**: Is this candidate a good fit for the role? (Strong fit / Moderate fit / Weak fit)
    2. **Key Strengths**: What are their standout qualities? (Be specific - mention technical skills or project achievements)
    3. **Notable Gaps**: What's missing or weak? (Be direct but constructive)
    4. **Recommendation**: Hire / Maybe / Pass - with brief reasoning

    STYLE GUIDELINES:
    - Be direct and actionable
    - Use specific examples from the evaluations
    - Balance positive and critical feedback
    - End with a clear recommendation

    EXAMPLE FORMAT:
    "This candidate shows [overall fit level] for the Backend Product Engineer role. They demonstrate strong [specific strength] and [another strength], as evidenced by [specific example]. However, they lack [specific gap], which is [important/critical] for this position. Given [reasoning], I recommend [Hire/Maybe/Pass] - [brief justification]."

    Write ONLY the summary text (no JSON, no formatting, just the paragraph):"""
