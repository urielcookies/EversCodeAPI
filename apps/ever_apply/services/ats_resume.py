import json
import fitz
import boto3
from botocore.exceptions import ClientError
from io import BytesIO
from urllib.parse import urlparse
from openai import AsyncOpenAI
from fastapi import HTTPException
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.platypus.flowables import KeepInFrame

from core.config import settings

deepseek = AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


async def download_resume_text(resume_url: str) -> str:
    """Download user's PDF from R2 and extract full text."""
    key = urlparse(resume_url).path.lstrip("/")
    try:
        response = _r2_client().get_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Resume file not found. Please re-upload your resume.")
        raise
    file_bytes = response["Body"].read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


async def generate_ats_content(resume_text: str, job_description: str) -> dict:
    """Call DeepSeek to produce an ATS-optimized resume as structured JSON."""
    response = await deepseek.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """You are an expert resume writer specializing in ATS (Applicant Tracking System) optimization.
Given a candidate's resume and a job description, rewrite the resume to maximize ATS keyword alignment and pass automated screening.

Rules:
- Mirror keywords and phrases from the job description naturally throughout the resume
- Quantify achievements with numbers/percentages wherever possible
- Use strong action verbs to start every bullet point
- Keep all facts accurate — never fabricate experience, titles, companies, or credentials
- Use standard ATS-safe section names

Return ONLY valid JSON with this exact structure:
{
  "name": "string",
  "email": "string",
  "phone": "string or null",
  "linkedin": "string or null",
  "github": "string or null",
  "location": "string or null",
  "summary": "2-3 sentence ATS-optimized professional summary targeting this specific job",
  "skills": ["skill1", "skill2"],
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "duration": "Month Year - Month Year",
      "bullets": ["bullet 1", "bullet 2"]
    }
  ],
  "education": [
    {
      "degree": "Degree Name",
      "school": "School Name",
      "year": "string or null"
    }
  ],
  "certifications": ["cert1"]
}

certifications may be an empty list if none exist.""",
            },
            {
                "role": "user",
                "content": f"CANDIDATE RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{job_description}",
            },
        ],
    )
    return json.loads(response.choices[0].message.content)


def build_pdf(data: dict) -> bytes:
    """Render structured resume data into an ATS-friendly PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    base = getSampleStyleSheet()["Normal"]

    name_style = ParagraphStyle("Name", parent=base, fontSize=18, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=10)
    contact_style = ParagraphStyle("Contact", parent=base, fontSize=9, alignment=TA_CENTER, spaceAfter=2)
    section_style = ParagraphStyle("Section", parent=base, fontSize=11, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=3)
    body_style = ParagraphStyle("Body", parent=base, fontSize=10, spaceAfter=2, leading=14)
    job_title_style = ParagraphStyle("JobTitle", parent=base, fontSize=10, fontName="Helvetica-Bold", spaceAfter=1)
    job_meta_style = ParagraphStyle("JobMeta", parent=base, fontSize=9, textColor=colors.HexColor("#555555"), spaceAfter=3)
    bullet_style = ParagraphStyle("Bullet", parent=base, fontSize=10, leftIndent=12, spaceAfter=2, leading=14)

    def divider(heavy=False):
        return HRFlowable(
            width="100%",
            thickness=1 if heavy else 0.5,
            color=colors.HexColor("#333333" if heavy else "#cccccc"),
            spaceAfter=4,
        )

    story = []

    # Header
    story.append(Paragraph(data.get("name", ""), name_style))
    contact_parts = [p for p in [
        data.get("email"),
        data.get("phone"),
        data.get("location"),
        data.get("linkedin"),
        data.get("github"),
    ] if p]
    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), contact_style))
    story.append(divider(heavy=True))

    # Summary
    if data.get("summary"):
        story.append(Paragraph("SUMMARY", section_style))
        story.append(divider())
        story.append(Paragraph(data["summary"], body_style))

    # Skills
    if data.get("skills"):
        story.append(Paragraph("SKILLS", section_style))
        story.append(divider())
        story.append(Paragraph(", ".join(data["skills"]), body_style))

    # Experience
    if data.get("experience"):
        story.append(Paragraph("EXPERIENCE", section_style))
        story.append(divider())
        for job in data["experience"]:
            story.append(Paragraph(f"{job.get('title', '')} — {job.get('company', '')}", job_title_style))
            if job.get("duration"):
                story.append(Paragraph(job["duration"], job_meta_style))
            for bullet in job.get("bullets", []):
                story.append(Paragraph(f"• {bullet}", bullet_style))
            story.append(Spacer(1, 4))

    # Education
    if data.get("education"):
        story.append(Paragraph("EDUCATION", section_style))
        story.append(divider())
        for edu in data["education"]:
            year = f" ({edu['year']})" if edu.get("year") else ""
            story.append(Paragraph(f"{edu.get('degree', '')} — {edu.get('school', '')}{year}", body_style))

    # Certifications
    if data.get("certifications"):
        story.append(Paragraph("CERTIFICATIONS", section_style))
        story.append(divider())
        for cert in data["certifications"]:
            story.append(Paragraph(f"• {cert}", bullet_style))

    usable_width = letter[0] - 1.5 * inch
    usable_height = letter[1] - 1.5 * inch
    doc.build([KeepInFrame(usable_width, usable_height, story, mode="shrink")])
    return buffer.getvalue()


async def generate_ideal_content(job_description: str) -> dict:
    """Call DeepSeek to produce a fictional ideal candidate resume as structured JSON."""
    response = await deepseek.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """You are an expert resume writer. Your job is to create a resume for the perfect fictional candidate for a given job description.
This is a sandbox/playground tool — you are free to invent a highly qualified fictional person with the ideal background, skills, metrics, and experience to score 100% on ATS and impress any hiring manager.

Rules:
- Invent a realistic fictional candidate (name, contact info, background)
- Mirror every keyword and phrase from the job description naturally
- Include specific, believable metrics and quantified achievements (percentages, numbers, team sizes, revenue impact, etc.)
- Use strong action verbs for every bullet point
- Make the experience directly relevant to the job — the candidate should look like they were born for this role
- Keep it realistic and professional — not exaggerated to the point of being unbelievable

Return ONLY valid JSON with this exact structure:
{
  "name": "string",
  "email": "string",
  "phone": "string or null",
  "linkedin": "string or null",
  "github": "string or null",
  "location": "string or null",
  "summary": "2-3 sentence professional summary perfectly targeting this job",
  "skills": ["skill1", "skill2"],
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "duration": "Month Year - Month Year",
      "bullets": ["bullet 1", "bullet 2"]
    }
  ],
  "education": [
    {
      "degree": "Degree Name",
      "school": "School Name",
      "year": "string or null"
    }
  ],
  "certifications": ["cert1"]
}

certifications may be an empty list if none exist.""",
            },
            {
                "role": "user",
                "content": f"JOB DESCRIPTION:\n{job_description}",
            },
        ],
    )
    return json.loads(response.choices[0].message.content)


async def generate_realistic_content(resume_text: str, job_description: str) -> dict:
    """Call DeepSeek to produce an enhanced resume using real skeleton + AI-generated bullets/skills/summary."""
    response = await deepseek.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """You are an expert resume writer. You will be given a candidate's real resume and a job description.
Your job is to enhance the resume to make it the perfect ATS-optimized version for that specific job.

Rules:
- PRESERVE exactly as-is: name, email, phone, LinkedIn, GitHub, location, company names, job dates, education (degree, school, year)
- PRESERVE job titles exactly as-is
- INVENT highly compelling, specific, quantified bullet points for each job — tailored to the job description keywords
- EXPAND and OPTIMIZE the skills section to maximize ATS keyword matching for this job
- GENERATE a strong AI-written professional summary targeting this specific job
- Every bullet must start with a strong action verb and include metrics/numbers where believable
- Mirror keywords and phrases from the job description naturally throughout

Return ONLY valid JSON with this exact structure:
{
  "name": "string",
  "email": "string",
  "phone": "string or null",
  "linkedin": "string or null",
  "github": "string or null",
  "location": "string or null",
  "summary": "2-3 sentence AI-generated summary targeting this specific job",
  "skills": ["skill1", "skill2"],
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "duration": "Month Year - Month Year",
      "bullets": ["bullet 1", "bullet 2"]
    }
  ],
  "education": [
    {
      "degree": "Degree Name",
      "school": "School Name",
      "year": "string or null"
    }
  ],
  "certifications": ["cert1"]
}

certifications may be an empty list if none exist.""",
            },
            {
                "role": "user",
                "content": f"CANDIDATE RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{job_description}",
            },
        ],
    )
    return json.loads(response.choices[0].message.content)


async def upload_ats_resume(pdf_bytes: bytes, clerk_user_id: str, match_id: str) -> str:
    """Upload the generated ATS resume PDF to R2 and return its public URL."""
    prefix = "development/ats-resumes" if settings.ENV == "development" else "ats-resumes"
    key = f"{prefix}/{clerk_user_id}/{match_id}.pdf"
    _r2_client().put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )
    return f"{settings.R2_PUBLIC_URL}/{key}"


async def delete_ats_resume(ats_resume_url: str) -> None:
    """Delete an ATS resume PDF from R2."""
    key = urlparse(ats_resume_url).path.lstrip("/")
    _r2_client().delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
