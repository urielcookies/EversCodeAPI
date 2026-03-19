import json
from openai import AsyncOpenAI
from core.config import settings

# DeepSeek client — identical to OpenAI client, only base_url differs
deepseek = AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)


async def score_match(resume_summary: str, job_description: str, user_preferences: dict | None = None) -> dict:
    """
    Ask DeepSeek to score how well a resume matches a job description.
    Returns: {"score": 85, "reason": "Strong React and TypeScript overlap"}
    Score is 0-100. DeepSeek handles synonym reasoning natively (React = Frontend Engineer).
    If user_preferences includes remote_type, DeepSeek will return score 0 on work arrangement mismatch.
    """
    prefs = user_preferences or {}
    remote_pref = prefs.get("remote_type")

    preference_instruction = ""
    if remote_pref:
        preference_instruction = (
            f"IMPORTANT: The user requires {remote_pref} work. "
            "Read the job description carefully to determine the work arrangement. "
            f"If the job clearly requires a work arrangement incompatible with {remote_pref} "
            "(e.g. requires in-office presence, lists a physical office as required, or explicitly "
            f"states onsite/hybrid when the user wants remote), you MUST return "
            f"{{\"score\": 0, \"reason\": \"Job does not match {remote_pref} work preference\"}}. "
            "Only proceed with skill scoring if the work arrangement is compatible or unspecified. "
        )

    pref_context = ""
    if remote_pref:
        pref_context += f"\nWork arrangement preference: {remote_pref}"

    response = await deepseek.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a technical recruiter scoring resume-to-job fit. "
                    "Respond with JSON: {\"score\": <0-100>, \"reason\": <one sentence>}. "
                    f"{preference_instruction}"
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
                "content": f"Resume:\n{resume_summary}{pref_context}\n\nJob:\n{job_description}",
            },
        ],
    )
    return json.loads(response.choices[0].message.content)
