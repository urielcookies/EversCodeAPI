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
                    "You are a technical recruiter. Score how well a candidate's resume matches a job description. "
                    "Respond with JSON: {\"score\": <0-100>, \"reason\": <one sentence>}. "
                    "Consider skill synonyms (React = Frontend, Python = Backend Engineer)."
                ),
            },
            {
                "role": "user",
                "content": f"Resume:\n{resume_summary}\n\nJob:\n{job_description}",
            },
        ],
    )
    return json.loads(response.choices[0].message.content)
