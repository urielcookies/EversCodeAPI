import json
import boto3
import pdfplumber
from io import BytesIO
from urllib.parse import urlparse
from fastapi import HTTPException
from openai import AsyncOpenAI
from core.config import settings
from apps.ever_apply.schemas import ParsedData

# DeepSeek client — identical to OpenAI client, only base_url differs
deepseek = AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)


# R2 client (S3-compatible — only the endpoint_url changes vs real S3)
def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",  # Required by Cloudflare R2
    )


# 1a. Delete existing resume from R2 by its public URL
async def delete_resume(resume_url: str) -> None:
    key = urlparse(resume_url).path.lstrip("/")
    client = get_r2_client()
    client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)


# 1b. Upload PDF to R2, return public URL
async def upload_resume(file_bytes: bytes, filename: str, clerk_user_id: str) -> str:
    client = get_r2_client()
    prefix = "development/resumes" if settings.ENV == "development" else "resumes"
    key = f"{prefix}/{clerk_user_id}/{filename}"
    client.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType="application/pdf",
    )
    return f"{settings.R2_PUBLIC_URL}/{key}"


# 2. Extract text from PDF bytes (no temp file needed)
def extract_text(file_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


# 3. Parse with DeepSeek → structured JSON validated against ParsedData schema
async def parse_resume(text: str) -> dict:
    response = await deepseek.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """Extract resume info as JSON with these exact keys:
- name: full name of the candidate as a string
- skills: list of strings
- titles: list of strings
- seniority: must be exactly one of: junior, mid, senior (map entry/associate to junior, map lead/staff/principal to senior)
- years_exp: integer
- summary: one sentence string
Return only valid JSON, no extra text.""",
            },
            {"role": "user", "content": text},
        ],
    )
    parsed = ParsedData(**json.loads(response.choices[0].message.content))
    # Validate parsed output looks like a real resume
    if not parsed.name.strip() or not parsed.skills:
        raise HTTPException(status_code=400, detail="Could not parse resume. Please upload your actual resume.")
    return parsed.model_dump()
