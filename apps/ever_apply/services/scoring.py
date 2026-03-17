import json
from openai import AsyncOpenAI
from core.config import settings

# DeepSeek client — identical to OpenAI client, only base_url differs
deepseek = AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)


async def score_match(resume_summary: str, job_description: str) -> dict:
    """
    Ask DeepSeek to score how well a resume matches a job description.
    Returns: {"score": 85, "reason": "Strong React and TypeScript overlap"}
    Score is 0-100. DeepSeek handles synonym reasoning natively (React = Frontend Engineer).
    """
    response = await deepseek.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a technical recruiter scoring resume-to-job fit. "
                    "Respond with JSON: {\"score\": <0-100>, \"reason\": <one sentence>}. "
                    "Scoring guide: "
                    "90-100 = strong match on all required skills and correct seniority level; "
                    "70-89 = matches core requirements with minor gaps in preferred skills; "
                    "50-69 = partial match, missing one or more key required skills; "
                    "below 50 = significant mismatch in skills or seniority. "
                    "Weight required skills heavily over preferred/nice-to-have skills. "
                    "Treat these as equivalent: JavaScript = Node.js = TypeScript, "
                    "React = Frontend Engineer, Python = Backend Engineer, "
                    "REST APIs = RESTful APIs = API development. "
                    "In the reason, name the strongest skill overlap and the most critical gap."
                ),
            },
            {
                "role": "user",
                "content": f"Resume:\n{resume_summary}\n\nJob:\n{job_description}",
            },
        ],
    )
    return json.loads(response.choices[0].message.content)
