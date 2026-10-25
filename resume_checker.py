import os
import re
import json
from dotenv import load_dotenv

load_dotenv()

# Safely import PDF and DOCX parsers
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

# Safely import Google GenAI SDK
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


def extract_text_from_file(file_storage):
    """Extract plain text from uploaded PDF, DOCX, or text files."""
    if not file_storage or not file_storage.filename:
        return ""

    filename = file_storage.filename.lower()
    text = ""

    try:
        if filename.endswith(".pdf"):
            if PdfReader:
                reader = PdfReader(file_storage)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            else:
                content = file_storage.read()
                text = content.decode("utf-8", errors="ignore")

        elif filename.endswith(".docx"):
            if docx:
                doc = docx.Document(file_storage)
                text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            else:
                content = file_storage.read()
                text = content.decode("utf-8", errors="ignore")

        else:
            content = file_storage.read()
            text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        return ""

    return text.strip()


# Comprehensive Technical & Domain Skills Taxonomy
TECH_SKILLS_DICTIONARY = [
    # Languages
    "python", "javascript", "typescript", "java", "c++", "c#", "golang", "go", "ruby", "php", "rust", "swift", "kotlin", "scala",
    # Frameworks & Libraries
    "flask", "django", "fastapi", "express", "nodejs", "node.js", "react", "react.js", "angular", "vue", "vue.js", "next.js", "spring boot", "asp.net", "laravel", "rails",
    # Databases & Caching
    "sql", "mysql", "postgresql", "postgres", "sqlite", "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb", "sqlalchemy", "prisma", "hibernate",
    # Cloud & DevOps
    "docker", "kubernetes", "k8s", "aws", "amazon web services", "azure", "gcp", "google cloud", "ci/cd", "github actions", "jenkins", "gitlab ci", "terraform", "ansible", "linux", "bash", "nginx",
    # APIs & Architecture
    "rest", "restful", "rest api", "rest apis", "restful apis", "graphql", "grpc", "microservices", "websockets", "system design", "data structures", "algorithms", "oop",
    # Testing & Security
    "unit testing", "pytest", "unittest", "selenium", "jest", "cypress", "postman", "authentication", "authorization", "jwt", "oauth", "bcrypt", "csrf", "cors",
    # Data & AI
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "machine learning", "deep learning", "nlp", "llm", "data analysis", "data pipeline"
]

# Soft Skills & Professional Competencies
SOFT_SKILLS_DICTIONARY = [
    "agile", "scrum", "kanban", "jira", "git", "github", "gitlab", "version control",
    "problem solving", "cross-functional collaboration", "team leadership", "communication",
    "critical thinking", "code review", "mentorship", "project management", "debugging"
]

# Dynamic Action Verbs for ATS Scoring
ACTION_VERBS = {
    "architected", "engineered", "developed", "built", "designed", "optimized", "streamlined",
    "spearheaded", "implemented", "deployed", "scaled", "automated", "refactored", "integrated",
    "orchestrated", "led", "enhanced", "resolved", "executed", "collaborated", "managed"
}


def extract_skills_from_text(text, dictionary):
    """Identify recognized skills and phrases from text."""
    lower_text = text.lower()
    found = set()

    for item in dictionary:
        pattern = r'\b' + re.escape(item) + r'\b'
        if re.search(pattern, lower_text):
            # Clean display formatting
            if item in ["sql", "aws", "gcp", "jwt", "php", "ci/cd", "oop", "llm", "api", "apis"]:
                found.add(item.upper())
            elif item in ["nodejs", "node.js"]:
                found.add("Node.js")
            elif item in ["next.js", "react.js", "vue.js"]:
                found.add(item.capitalize())
            else:
                found.add(item.title())

    return sorted(list(found))


def extract_years_of_experience(text):
    """Extract estimated years of experience from resume or JD text."""
    if not text:
        return 0
    lower = text.lower()

    # 1. Explicit statements like "4+ years of experience", "3 years experience", "5-7 years"
    matches = re.findall(r'(\d+)\+?\s*(?:to|-)?\s*\d*\s*(?:years?|yrs?)(?:\s+(?:of\s+)?experience)?', lower)
    found_nums = []
    for m in matches:
        if m.isdigit() and 1 <= int(m) <= 40:
            found_nums.append(int(m))

    if found_nums:
        return max(found_nums)

    # 2. Date ranges in work experience sections (e.g., 2019 - 2024, 2021 - Present)
    year_ranges = re.findall(r'\b(20\d\d|19\d\d)\s*(?:-|to|–)\s*(20\d\d|present|current)\b', lower)
    total_years = 0
    current_year = 2026
    for start_yr, end_yr in year_ranges:
        try:
            s = int(start_yr)
            e = current_year if end_yr in ["present", "current"] else int(end_yr)
            if 0 < (e - s) <= 40:
                total_years += (e - s)
        except ValueError:
            continue

    if total_years > 0:
        return min(total_years, 35)

    return 0


def check_ats_local(resume_text, job_description):
    """
    Realistic multi-dimensional ATS evaluation and keyword matching engine.
    Runs locally with heavy priority given to required experience and technical skills.
    """
    resume_lower = resume_text.lower()
    jd_lower = job_description.lower() if job_description else ""

    # 1. Required Experience & Seniority Match (High Priority)
    req_years = extract_years_of_experience(job_description)
    cand_years = extract_years_of_experience(resume_text)

    if req_years > 0:
        if cand_years >= req_years:
            experience_match = min(100, 90 + (cand_years - req_years) * 3)
            exp_status = f"Meets/Exceeds Requirement ({cand_years}+ yrs vs {req_years}+ yrs required)"
            exp_pass = True
        elif cand_years > 0:
            experience_match = max(30, round((cand_years / req_years) * 80))
            exp_status = f"Below Required Experience ({cand_years} yrs vs {req_years}+ yrs required)"
            exp_pass = False
        else:
            experience_match = 55
            exp_status = f"Required: {req_years}+ yrs (Candidate years not explicitly stated)"
            exp_pass = False
    else:
        req_years = 3
        experience_match = 85 if cand_years >= 3 else 70
        exp_status = f"Demonstrates ~{cand_years} years experience" if cand_years else "Experience aligned"
        exp_pass = True

    # 2. Technical Skills Extraction & Match
    jd_tech = extract_skills_from_text(job_description, TECH_SKILLS_DICTIONARY)
    if not jd_tech:
        jd_tech = ["Python", "Flask", "SQL", "MySQL", "REST APIs", "Git"]

    matched_tech = []
    missing_tech = []

    for skill in jd_tech:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, resume_lower):
            matched_tech.append(skill)
        else:
            missing_tech.append(skill)

    tech_match_pct = round((len(matched_tech) / len(jd_tech)) * 100) if jd_tech else 70

    # 3. Soft Skills & Methodologies
    jd_soft = extract_skills_from_text(job_description, SOFT_SKILLS_DICTIONARY)
    if not jd_soft:
        jd_soft = ["Agile", "Git", "Problem Solving", "Communication"]

    matched_soft = []
    missing_soft = []

    for skill in jd_soft:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, resume_lower):
            matched_soft.append(skill)
        else:
            missing_soft.append(skill)

    soft_match_pct = round((len(matched_soft) / len(jd_soft)) * 100) if jd_soft else 60

    # 4. Formatting & Structural Health Checks
    formatting_checks = []
    format_score = 100

    # Experience check item
    formatting_checks.append({
        "name": "Required Experience & Seniority",
        "status": "pass" if exp_pass else "warning",
        "detail": f"Job requirement: {req_years}+ years. Candidate profile indicates ~{cand_years if cand_years else 'entry/unspecified'} years ({exp_status})."
    })

    # Contact info check
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+', resume_text))
    has_phone = bool(re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text))
    has_links = "linkedin" in resume_lower or "github" in resume_lower

    if has_email and (has_phone or has_links):
        formatting_checks.append({
            "name": "Contact Information",
            "status": "pass",
            "detail": "Email, phone number, and professional profiles detected."
        })
    else:
        format_score -= 20
        formatting_checks.append({
            "name": "Contact Information",
            "status": "warning",
            "detail": "Ensure email, phone number, and LinkedIn URL are clearly visible in the header."
        })

    # Section headers check
    has_exp = any(h in resume_lower for h in ["experience", "work history", "employment"])
    has_edu = any(h in resume_lower for h in ["education", "degree", "university", "college"])
    has_skills_sec = any(h in resume_lower for h in ["skills", "technical skills", "technologies"])

    if has_exp and has_edu and has_skills_sec:
        formatting_checks.append({
            "name": "Core Section Structure",
            "status": "pass",
            "detail": "Standard headers (Experience, Education, Skills) are present and ATS-parseable."
        })
    else:
        format_score -= 20
        formatting_checks.append({
            "name": "Core Section Structure",
            "status": "warning",
            "detail": "Missing standard section headers like 'Experience', 'Education', or 'Technical Skills'."
        })

    # Word count check
    words = resume_text.split()
    word_count = len(words)
    if 300 <= word_count <= 900:
        formatting_checks.append({
            "name": "Length & Word Count",
            "status": "pass",
            "detail": f"{word_count} words (Ideal 1-2 page length for ATS parsing)."
        })
    elif word_count < 300:
        format_score -= 15
        formatting_checks.append({
            "name": "Length & Word Count",
            "status": "warning",
            "detail": f"{word_count} words (Too brief. Expand on responsibilities and project outcomes)."
        })
    else:
        format_score -= 10
        formatting_checks.append({
            "name": "Length & Word Count",
            "status": "warning",
            "detail": f"{word_count} words (Slightly verbose. Keep concise for better readability)."
        })

    # 5. Measurable Metrics & Action Verbs
    metrics_matches = re.findall(r'(\d+[\d,\.]*\s*(%|\+|k|x|ms|s|users|requests|million|billion|\$))', resume_lower)
    action_verbs_found = [verb.title() for verb in ACTION_VERBS if re.search(r'\b' + verb + r'\b', resume_lower)]

    impact_score = min(len(metrics_matches) * 15 + len(action_verbs_found) * 10, 100)
    impact_score = max(impact_score, 45)

    if len(metrics_matches) >= 2:
        formatting_checks.append({
            "name": "Measurable Impact & Metrics",
            "status": "pass",
            "detail": f"Found {len(metrics_matches)} quantified achievements (%, numbers, performance stats)."
        })
    else:
        formatting_checks.append({
            "name": "Measurable Impact & Metrics",
            "status": "warning",
            "detail": "Few quantified achievements found. Add measurable stats (e.g. 'improved speed by 30%')."
        })

    # 6. Composite Weighted ATS Score (Experience & Hard Skills weighted heavily)
    # 35% Required Experience + 35% Technical Skills + 10% Soft Skills + 10% Impact/Verbs + 10% Formatting
    overall_score = round(
        (experience_match * 0.35) +
        (tech_match_pct * 0.35) +
        (soft_match_pct * 0.10) +
        (impact_score * 0.10) +
        (format_score * 0.10)
    )
    overall_score = min(max(overall_score, 25), 98)

    # Verdict
    if overall_score >= 80:
        verdict = "Strong Match"
    elif overall_score >= 65:
        verdict = "Competitive Match"
    elif overall_score >= 50:
        verdict = "Moderate Match"
    else:
        verdict = "Needs Improvement"

    # Actionable Critical Fixes
    critical_fixes = []
    if not exp_pass and req_years > 0:
        critical_fixes.append(f"Position requires {req_years}+ years of experience. Highlight relevant full-time experience, internships, or production project timelines.")
    if missing_tech:
        critical_fixes.append(f"Incorporate missing core technologies: {', '.join(missing_tech[:3])} into your skills and work history.")
    if len(metrics_matches) < 2:
        critical_fixes.append("Quantify your past contributions with concrete metrics (e.g., latency reduction, user volume, test coverage %).")
    if len(action_verbs_found) < 3:
        critical_fixes.append("Start bullet points with high-impact action verbs like 'Architected', 'Engineered', 'Automated', or 'Deployed'.")

    # Tailored Bullet Point Rewrites
    top_matched = matched_tech[0] if matched_tech else "Python & Flask"
    top_missing = missing_tech[0] if missing_tech else "Docker & Cloud Deployment"

    bullet_rewrites = [
        {
            "original": f"Worked with {top_matched} to develop backend endpoints and databases.",
            "optimized": f"Architected and deployed scalable backend REST APIs using {top_matched}, improving query efficiency and reducing latency by 25%."
        },
        {
            "original": f"Helped with testing and application deployment workflows.",
            "optimized": f"Automated CI/CD deployment pipelines utilizing {top_missing}, maintaining 99.9% uptime across production releases."
        }
    ]

    summary = (
        f"Your résumé achieves a {overall_score}% ATS score for this role, with an experience match of {experience_match}% ({exp_status}) and matching {len(matched_tech)} of {len(jd_tech)} core technical requirements."
    )

    return {
        "ats_score": overall_score,
        "verdict": verdict,
        "summary": summary,
        "category_scores": {
            "experience_match": experience_match,
            "skills_match": tech_match_pct,
            "soft_skills": soft_match_pct,
            "impact_verbs": impact_score,
            "formatting": format_score
        },
        "experience_summary": {
            "required_years": f"{req_years}+ years" if req_years else "Not specified",
            "detected_years": f"{cand_years}+ years" if cand_years else "Entry / Unspecified",
            "status": exp_status
        },
        "matched_keywords": matched_tech,
        "unmatched_keywords": missing_tech,
        "soft_skills_matched": matched_soft,
        "soft_skills_missing": missing_soft,
        "formatting_checks": formatting_checks,
        "critical_fixes": critical_fixes,
        "bullet_rewrites": bullet_rewrites,
        "total_count": len(jd_tech),
        "matched_count": len(matched_tech),
        "unmatched_count": len(missing_tech)
    }


# Global cached client to avoid connection handshake latency on every request
_cached_client = None


def get_genai_client():
    global _cached_client
    if _cached_client is not None:
        return _cached_client

    api_key = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
    if api_key and genai:
        try:
            _cached_client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"Error initializing GenAI Client: {e}")
            _cached_client = None
    return _cached_client


def check_ats_gemini(resume_text, job_description):
    """
    Realistic AI-Powered ATS Resume Analysis using low-latency Google Gemini 3 Flash series.
    Gives high priority to required years of experience and seniority match.
    """
    client = get_genai_client()
    if not client:
        return None

    # Cap input text to prevent excessive processing overhead while preserving full context
    capped_resume = resume_text[:4000].strip()
    capped_jd = job_description[:3000].strip()

    try:
        prompt = f"""
        You are an elite Applicant Tracking System (ATS) algorithm and senior technical recruiter.
        Perform a rigorous, realistic ATS compatibility check and gap analysis comparing this Candidate Résumé with the Target Job Description.

        CRITICAL PRIORITY — REQUIRED EXPERIENCE & SENIORITY:
        Give HIGH IMPORTANCE to Required Years of Experience and Seniority Alignment (e.g. Junior, Mid-level, Senior, Lead, Architect).
        - Analyze the required years of experience in the Job Description versus candidate's demonstrated career depth and tenure.
        - If the candidate lacks the required years of experience or seniority level, score 'experience_match' proportionally low and penalize the overall 'ats_score'.
        - If the candidate meets or exceeds required tenure and seniority, award a high 'experience_match' score (85-100).

        Target Job Description:
        {capped_jd}

        Candidate Resume Content:
        {capped_resume}

        Evaluate across 5 key dimensions:
        1. Required Experience & Seniority Match (years of experience, relevant role titles, seniority fit)
        2. Hard Technical Skills Match (exact and semantically equivalent technologies)
        3. Soft Skills & Work Methodologies Match
        4. Action Verbs & Quantified Measurable Impact (%, $, numbers)
        5. ATS Readability & Section Formatting

        Return ONLY a valid JSON object matching this schema:
        {{
            "ats_score": <integer from 0 to 100 heavily weighted by experience and tech skills>,
            "verdict": "<'Strong Match' | 'Competitive Match' | 'Moderate Match' | 'Needs Improvement'>",
            "summary": "<2-3 sentence executive recruiter summary detailing experience fit, match strength, and highest impact gap>",
            "category_scores": {{
                "experience_match": <integer 0-100 reflecting required years and seniority match>,
                "skills_match": <integer 0-100>,
                "soft_skills": <integer 0-100>,
                "impact_verbs": <integer 0-100>,
                "formatting": <integer 0-100>
            }},
            "experience_summary": {{
                "required_years": "<e.g. '3+ years' or 'Senior (5+ years)'>",
                "detected_years": "<e.g. '4+ years demonstrated'>",
                "status": "<'Meets Requirement' | 'Below Required Experience' | 'Well Aligned'>"
            }},
            "matched_keywords": ["skill1", "skill2"],
            "unmatched_keywords": ["missingSkill1", "missingSkill2"],
            "soft_skills_matched": ["softSkill1"],
            "soft_skills_missing": ["missingSoftSkill1"],
            "formatting_checks": [
                {{"name": "Required Experience & Seniority", "status": "pass|warning", "detail": "..."}},
                {{"name": "Contact Information", "status": "pass|warning", "detail": "..."}},
                {{"name": "Core Section Structure", "status": "pass|warning", "detail": "..."}},
                {{"name": "Length & Word Count", "status": "pass|warning", "detail": "..."}},
                {{"name": "Measurable Impact & Metrics", "status": "pass|warning", "detail": "..."}}
            ],
            "critical_fixes": [
                "Top prioritized fix 1",
                "Top prioritized fix 2",
                "Top prioritized fix 3"
            ],
            "bullet_rewrites": [
                {{
                    "original": "Weak/generic bullet point related to this candidate's background",
                    "optimized": "High-impact, metric-driven ATS-tailored bullet point incorporating job description keywords"
                }},
                {{
                    "original": "Another weak/generic bullet point",
                    "optimized": "Strong action-oriented bullet point with quantified outcome"
                }}
            ]
        }}
        """

        # Ultra-low latency model order: flash-lite delivers fastest responses with highest throughput
        candidate_models = [
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3-flash-preview",
            "gemini-3.8-flash"
        ]

        gen_config = None
        if types and hasattr(types, "GenerateContentConfig"):
            gen_config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1024,
                response_mime_type="application/json"
            )

        response = None
        used_model = None

        for model_name in candidate_models:
            try:
                if gen_config:
                    chat = client.chats.create(model=model_name, config=gen_config)
                else:
                    chat = client.chats.create(model=model_name)

                resp = chat.send_message(prompt)
                if resp and resp.text:
                    response = resp
                    used_model = model_name
                    print(f"Successfully analyzed with AI model: {model_name}")
                    break
            except Exception as model_err:
                print(f"Notice: model '{model_name}' attempt error: {model_err}")
                continue

        if not response or not response.text:
            return None

        # Clean JSON markdown fences if present
        raw_text = response.text.strip()
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text, flags=re.MULTILINE)
        raw_text = re.sub(r'\s*```$', '', raw_text, flags=re.MULTILINE)

        data = json.loads(raw_text)

        matched_kw = data.get("matched_keywords", [])
        unmatched_kw = data.get("unmatched_keywords", [])
        total_kw = len(matched_kw) + len(unmatched_kw)

        data["total_count"] = total_kw
        data["matched_count"] = len(matched_kw)
        data["unmatched_count"] = len(unmatched_kw)
        data["ai_model"] = used_model

        return data
    except Exception as e:
        print(f"AI analysis fallback: {e}")
        return None



def check_ats_compatibility(resume_text, job_description):
    """
    Main entry point: Evaluates resume against job description using AI if available,
    or seamlessly falls back to the robust multi-dimensional local ATS engine.
    """
    result = check_ats_gemini(resume_text, job_description)
    if not result:
        result = check_ats_local(resume_text, job_description)
    return result

