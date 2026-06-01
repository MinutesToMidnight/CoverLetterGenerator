# cover_letter_generator.py
import os
import asyncio
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
import sys
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend import rag

# Загрузка переменных окружения (локально из .env, на Railway — системные env vars)
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

MAX_HOURS_PER_WEEKS = 40

# ----------------------------------------------------------------------
# 1. Профили пользователей (полные данные)
# ----------------------------------------------------------------------
user_profiles = [
    {
        "name": "Tilek Chubakov",
        "position": "Senior AI/ML Engineer, AI Agents, LLM, MLOps, Lead Data Engineer",
        "skills": [
            "ETL/ELT pipelines with dbt and scalable data warehousing",
            "Data lake and lakehouse architectures for analytics and ML",
            "High-performance data systems optimized for cost and latency",
            "AWS, Google Cloud, and Microsoft Azure infrastructure",
            "Docker and Kubernetes for scalable deployments",
            "CI/CD pipelines with GitHub Actions and GitLab CI/CD",
            "Event-driven systems with Kinesis, Event Hubs, and RabbitMQ",
            "Docker, AWS, RAG, LangChain, LLM fine-tuning",
            "Hugging Face Transformers",
            "Prompt engineering, tool usage, and context-aware pipelines",
            "Autonomous workflows integrating APIs, databases, and enterprise systems",
            "Real-time decision systems replacing manual operations",
            "End-to-end ML pipelines with MLflow and Kubeflow",
            "Time-series forecasting with Prophet and ARIMA",
            "Gradient boosting using XGBoost, LightGBM, and CatBoost",
            "Deep learning with PyTorch and TensorFlow on GPU infrastructure",
            "Supervised and unsupervised learning for anomaly detection, fraud detection, and risk modeling",
            "Named entity recognition, classification, and semantic search",
            "Knowledge retrieval systems and question-answering pipelines",
            "Contract analysis, invoice automation, and compliance validation",
            "Multilingual NLP and morphologically rich language processing",
            "Batch and streaming pipelines using Apache Spark, Apache Kafka, and Apache Airflow",
            "Cloud-native architectures with BigQuery, Dataflow, Pub/Sub, and Snowflake",
            "Hadoop, Hive, Spark (Databricks), Kafka (Confluent), Airflow, DataFlow, Pub/Sub, Kinesis, RabbitMQ, Event Hubs, NiFi, Stitch, Great Expectations",
            "Apache Superset, Tableau, Looker, Power BI",
            "Python, C#, Scala, Java, R, JavaScript, VB.NET, C/C++, shell scripting",
            "sci-kit learn, PyTorch, TensorFlow, Kubeflow, MLflow",
            "Snowflake, MySQL, PostgreSQL, MS SQL Server, MongoDB, Cassandra, HBase, Oracle, Redis, Amazon Redshift",
            "AWS (EC2, S3, RDS, Lambda, Redshift, Glue, Kinesis)",
            "Azure (Function Apps, Event Hubs, Data Explorer, Storage)",
            "GCP (Cloud Functions, Pub/Sub, BigQuery, Cloud Run)",
            "HTML/CSS, React, Node.js, Flask, Express, FastAPI",
            "Docker, Kubernetes, Terraform",
            "Git, GitLab CI/CD, GitHub Actions, dbt, Fivetran, CircleCI, SSIS, CDK"
        ],
        "min_salary_per_hour_usd": 50,
        "priority_cases": [
            "Scale AI", "Arcade", "Deverus", "Generative AI Marketplace",
            "AI Identity Verification", "CryptoPay", "LLM Chatbot & RAG System",
            "AI Document Processing", "FinTech Payment System"
        ],
        "portfolio_link": "https://github.com/tilekchubakov"
    },
    {
        "name": "Victoria",
        "position": "Senior Full-Stack Developer, React, Node.js, Scalable SaaS",
        "skills": [
            "Full-stack development with React and Node.js for scalable web applications",
            "Frontend engineering with React, Next.js, TypeScript, Redux, Tailwind CSS",
            "Backend development using Node.js and Express.js for REST API architecture",
            "SaaS platform development with multi-tenant systems and cloud infrastructure",
            "Database design with PostgreSQL and MongoDB, including performance optimization",
            "API integrations, authentication, and secure data handling",
            "Cloud deployment with AWS, Docker, and CI/CD pipelines",
            "Cross-platform development using Flutter and React Native"
        ],
        "min_salary_per_hour_usd": 40,
        "min_salary_agency_usd": 35,
        "priority_cases": [
            "Deverus", "Compassly", "Arcade", "Solstice",
            "FlexCare", "Classful", "Garantme",
            "NFT Ticketing", "Flink", "A Little Dose of Happy"
        ]
    },
    {
        "name": "Vicode Solutions",
        "position": "Full-Cycle Software Development Agency, React, Node.js, Scalable SaaS, 350+ developers",
        "skills": [
            "Responsive, high-performance interfaces using React, Next.js, TypeScript, Redux, and Tailwind CSS - clean architecture, intuitive UX, and optimized performance",
            "Robust server-side systems with Node.js and Express.js, secure RESTful APIs, and scalable infrastructures powered by PostgreSQL and MongoDB",
            "Authentication systems, third-party service integrations, and cloud deployment with CI/CD pipelines",
            "Full-stack SaaS application development",
            "React & Next.js frontend architecture",
            "Node.js backend systems and REST API design",
            "Database modeling with PostgreSQL and MongoDB",
            "Multi-tenant platforms and subscription-based products",
            "Payment integrations and secure authentication",
            "Cloud infrastructure and DevOps workflows"
        ],
        "min_salary_per_hour_usd": 35,
        "priority_cases": [
            "Deverus", "Compassly", "Arcade", "Solstice",
            "FlexCare", "Classful", "Garantme",
            "NFT Ticketing", "Flink", "A Little Dose of Happy"
        ],
        "portfolio_link": "vicode.solutions/portfolio"
    },
]

# ----------------------------------------------------------------------
# 3. Базовые правила отбора работы
# ----------------------------------------------------------------------
selection_rules = {
    "min_duration_months": 2,
    "preferred_work_hours_per_week": 30,
    "red_flags": """No job details, too niche stack (GHL-only, OpenClaw-only, n8n-only),
                 geo restrictions that exclude the profile, screen-recorded assessments,
                 Loom mandatory with no alternative."""
}

# ----------------------------------------------------------------------
# 4. Правила составления письма
# ----------------------------------------------------------------------
cover_letter_rules = """
Structure: each case contains project name, client URL or Upwork portfolio link, tech stack (technologies used), industry or niche, role description (what was built), key results with metrics, and a priority flag.

Case 1 (required) must come from the Upwork portfolio. Pick the most relevant Upwork case by stack, niche, and problem type.

Case 2 (best match) is the single most relevant case from the combined pool: Upwork portfolio plus full Interexy case database. There is no hierarchy between the two sources; relevance wins. The system uses the full internal case database to determine best fit.

Case Matching Logic
Match by stack keywords from the job's mandatory skills section. Match by industry or niche. Match by problem type (real-time systems, payments, AI integration, healthcare, etc.). Case 1 is always from the Upwork portfolio. Case 2 is the best-matching case from either the Upwork portfolio or the full Interexy case database, whichever is more relevant. Maximum 2 cases per letter. Never use the same case in both Tilek and Victoria letters for the same job.

Output Block 3: two selected cases with a one-line explanation of why each was chosen.

Keyword Integration Rules
Source: mandatory skills section of the job posting. Naturally weave three to five mandatory skill keywords into the cover letter body. Never list them. Always embed them in the context of case descriptions or the closing statement.

Example: mandatory skills: React, Node.js, Supabase, TypeScript → "Built a production-grade React and Node.js platform with TypeScript throughout and Supabase as the real-time data layer."

Cover Letter Generation Pipeline

Step 0 — Job Analysis (mandatory, executed before all other steps)

Extract the following data from the job description (as a JSON object; do not include it in the final output, but use it for subsequent steps):

- `required_skills` (array of strings) – all skills from the "Mandatory skills" section and those mentioned in the text.
- `core_technical_terms` (array of strings) – specialized terms: "ontology", "knowledge graph", "RAG", "compliance enforcement", "multi-agent", etc.
- `business_pain_points` (array of strings) – specific client problems (e.g., "existing tools don't scale", "lack of automation", "compliance risks").
- `screening_questions` (array of objects with fields `question` and `type`) – all questions the client explicitly or implicitly asks. For example, "Walk us through one part you find interesting", "What would you do your first week".
- `special_instructions` (object) – flags: `loom_required: true/false`, `nda_required: true/false`, `test_task: "paid"/"unpaid"/none`.
- `urgency` (string) – "immediate", "with_days", "none".
- `budget` (object) – `min`, `max`, `type` ("hourly"/"fixed").
- `weekly_hours` (number) – the number of hours per week required (if specified).

This data is used in steps 3–7 to generate a personalized, targeted response.

Step 1 - Job Evaluation: assess duration, hours, budget, stack fit, red flags. Output PASS or SKIP with reasoning. Stop if SKIP.

Step 2 - Profile Selection: determine Tilek / Victoria / Vicode Solutions / both. If both, run the pipeline twice independently.

Dual-profile rule (when both Tilek and Victoria letters are generated): cases must be completely different; no case can appear in both letters. Letter texts must be meaningfully distinct in hook, framing, and angle - not paraphrases of each other. Screening question answers must also differ; each answer written from the respective profile's perspective with different cases and different language.

Step 3 - Hook Generation: generate two or three hook options for the user to choose from, or auto-select the strongest one.

Hook Rules: never start with "Most...". Use conversational openers only: "Let me be honest...", "From what I see...", "To be honest...", "Let me be direct...". The hook must address a specific technical risk or business pain visible in the job description. One or two sentences maximum. No generic compliments to the client.

Step 4 - Case Selection: pull the two most relevant Priority 1 cases. Format per case: name plus link (if available) plus one or two lines on what was built and with which stack, plus a key result with metric.

Step 5 - Closing Statement: one or two sentences containing years of experience, core stack match to job requirements, availability (40 hours/week), and hourly rate (omit if fixed price).

Immediate start rule: if the job posting indicates the client wants to start immediately, within a few days, or urgently, include in the closing statement that the selected profile is available to start immediately.

Step 6 - CTA and Signature: CTA is always "Let's talk." Signature formats: for a solo profile (Tilek or Victoria) use "Best, [Name]". For the agency angle (Vicode Solutions) use "Best, [Name], Vicode Solutions / vicode.solutions/portfolio". For Tilek on technical roles, add "https://github.com/tilekchubakov" on a separate line.

Step 7 - Screening Questions (if present): detect if the job posting contains a screening questions block (for example, "You will be asked to answer the following questions" or similar). If yes, generate answers as a separate output block; never mix them into the letter body.

Format per answer: use a numbered list matching the job's question order. For "Describe recent experience" or any request to describe a case or project, answer in full detail: project name plus link, what the product does, the client's pain point, the solution built, tech stack, role on the project, and measurable results. Never give a brief or summary answer to this type of question. For technical questions, give a precise technical answer. For "Do you have certifications?" use a standard answer referencing production experience. Include GitHub or portfolio links where relevant. When both Tilek and Victoria answers are generated, each must use different cases and different language.

Cover Letter Structure

Block 1 Hook: one or two sentences, conversational, addresses a specific pain or risk from the job description.
Block 2 Bridge: one sentence connecting the hook to the solution being offered.
Block 3 Case 1: name and link on the same line, followed by one or two lines describing what was built, stack used, and a key result with metric.
Block 4 Case 2: same format as Case 1.
Block 5 Closing: years of experience plus stack match plus availability plus rate if hourly, plus "available to start immediately" if the job is urgent.
Block 6 CTA: "Let's talk."
Block 7 Signature: "Best, [Name]" plus optional portfolio/GitHub line.

Formatting Rules
Use hyphen-minus ( - ) only, never em dash ( — ) or en dash ( – ). No bold text inside the letter. No bullet points inside the letter. No headers inside the letter. Use plain paragraphs only. The case name and link appear on the same line, for example: Classful - https://classful.com. Letter length is 150-200 words maximum. Screening answers are always a separate block, never inside the letter. If the job posting contains specific instructions (answer questions, provide a timeline, include something particular), always follow them without exception. Missing a stated requirement is an automatic disqualifier.

Edge Cases
If the client name is known, open the letter with the client name. If the client name is unknown, use no greeting or just "Hi there". If a Loom is mandatory, write that a Loom will be sent upon response. If an NDA is required, acknowledge willingness to sign in the closing. If "Agency preferred" is stated, use the Vicode Solutions angle. For a fixed price job, do not mention a rate anywhere in the letter. For an hourly job, include the rate in the closing statement. If a screen-recorded assessment is required, flag it to the user and ask whether to proceed. If both AI and fullstack are required, generate two letters independently. If the job requires a test task or assessment, state in the letter that test tasks are completed on a paid basis only, and that the terms can be discussed separately; never agree to unpaid test tasks. If an urgent start or start within days is required, include in the closing that the profile is available to start immediately.
"""

# ----------------------------------------------------------------------
# 5. Шаблон письма-отклика (few-shot examples + правила)
# ----------------------------------------------------------------------
letter_template = """
Example 1 (Good — specific, with metrics and stack):

[Block 1 Hook]
From what I see - this is less about building a shoe store and more about building a conversion machine that happens to sell shoes.

[Block 2 Bridge]
Performance, SEO, and clean architecture from day one - that's where I focus.

[Block 3 Case 1]
Arcade - https://arcade.ai
AI-powered marketplace handling thousands of concurrent requests. Built scalable backend infrastructure and React frontend optimized for high-load, real-time user interactions.

[Block 4 Case 2]
Classful - https://classful.com
EdTech SaaS, 1M+ MAU. Stripe integration, PostgreSQL optimization, page load speed improved by 55%. Conversion rate up 30%.

[Block 5 Closing]
15+ years building scalable backend systems. I'll make sure your store is fast, clean, and ready to grow. Available 40 hrs/week.

[Block 6 CTA]
Let's talk.

[Block 7 Signature]
Best,
Tilek


Example 2 (Good — addresses specific pain, includes technical answer, fixed‑price mention):

[Block 1 Hook]
Hi Jason,
This is a backend ownership problem - multi-tenant data isolation, HIPAA-compliant infrastructure, and a clean API layer a real clinic can trust from day one. The frontend is done; the hard part is everything underneath it.

[Block 2 Bridge]
I work as a senior full-stack engineer owning Node.js + Fastify backends and React frontends end to end - PostgreSQL schema design, REST API boundaries, auth systems, and production delivery. I'm fluent in TypeScript, work with Prisma and Supabase regularly, and handle Redis-backed async infrastructure as a standard part of the stack.

[Block 3 Case 1]
On Renegade Health - https://renegade.health/ - a HIPAA-regulated telemedicine platform, I led compliance audit preparation: PHI access controls, audit logging, and architectural sign-off. Stack: Node.js, TypeScript, PostgreSQL, GCP.

[Block 4 Case 2]
On Deverus - https://www.deverus.com/ - a regulated multi-tenant SaaS, I worked on backend redesign and integrated a blockchain-based digital wallet for sensitive document verification - another environment where data isolation wasn't optional.

[Block 5 Closing]
For RLS in PostgreSQL: I set a session-level clinic_id variable per connection and enforce Supabase RLS policies that filter all PHI reads and writes against it - combined with Prisma middleware injecting tenant context before every query.

Available immediately, 40 hrs/week, open to fixed-price per phase or hourly.

[Block 6 CTA]
Let's jump on a short call to walk through the spec and scope Phase 1.

[Block 7 Signature]
Best,
Viktoryia


Example 3 (Good — risk‑aware, DevOps‑heavy, one case only, but strong metrics):

[Block 1 Hook]
❗You are not considering the significant technical risk which can cost you $150k according to my experience when React + Python systems are scaled on AWS without proper Terraform, API boundaries, and cloud cost control.

[Block 2 Bridge]
I build full stack platforms using React for complex admin UIs, Python for backend services, AWS Lambda for scalable workloads, GraphQL for stable data contracts, and Terraform for fully reproducible infrastructure, with production-grade DevOps from day one.

[Block 3 Case 1]
On Deverus, a large-scale background screening platform, the business faced onboarding drop-offs and scaling limits due to legacy architecture, so I rebuilt core flows with React frontend, Python services on AWS, API-first design, and cloud automation, resulting in a 74% reduction in drop-off and support for millions of checks monthly.
Link: https://www.deverus.com/ 

[Block 4 Case 2]
(Second case missing – structure allows one case, but two are preferred)

[Block 5 Closing]
Working with me means you get a senior full stack engineer who designs systems to survive real traffic, audits, and growth, not just pass initial QA.
I proactively eliminate AWS cost leaks, GraphQL overfetching, and infra drift that usually appear after launch and quietly burn budgets.

My clients get predictable delivery, clean handover, and architectures that new engineers can safely extend without rewrites.

[Block 6 CTA]
Reply to this proposal to have a chat ASAP.

[Block 7 Signature]
Best,
Tilek


Example 4 (BAD — generic, no personalisation, missing answers to job questions, weak cases):

[Block 1 Hook]
Let me be honest, building a responsive and performant web application from scratch requires not just technical skills but also a deep understanding of user needs and AI integration.

[Block 2 Bridge]
I focus on creating solutions that are both user-friendly and technically sound.

[Block 3 Case 1]
Stauffer (Estimating app) - https://stauffer.com
Developed an internal web application for estimating landscape projects using JS/TS, React, and Node.js, optimizing calculations and improving efficiency by 40%.

[Block 4 Case 2]
MyGenMe (ChatBot) - https://mygenme.com
Built a conversational chatbot using Node.js for the backend and React Native for the frontend, enhancing user engagement through AI integration.

[Block 5 Closing]
With over 5 years of experience in full-stack development, I specialize in React and Node.js, and I am available to start immediately, working 40 hours per week.

[Block 6 CTA]
Let's talk.

[Block 7 Signature]
Best,
Victoria

Why this is weak:
- Hook: does not target a specific pain from the job description (no mention of greenfield, LLM integration risk, or DevOps).
- Bridge: generic declaration (“user-friendly and technically sound”) – no method, no tools.
- Cases: Stauffer is irrelevant to AI/DevOps; MyGenMe lacks metrics and specific AI details (e.g., which LLM, embeddings, scale).
- Closing: missing rate (hourly job) and excludes AI/DevOps skills.
- No answers to mandatory screening questions (the job had three questions).


Example 5 (GOOD — personalised, addresses specific job requirements, includes answers to questions):

[Block 1 Hook]
Let me be honest - building a greenfield product with LLMs from scratch is already risky. Adding a responsive frontend without a solid CI/CD pipeline is how AI budgets get burned.

[Block 2 Bridge]
That's why I start every AI project with Docker Compose for local dev, GitHub Actions for CI/CD, and Terraform for AWS. The same stack keeps your RAG pipeline and React frontend in sync without cost surprises.

[Block 3 Case 1]
MyGenMe - https://mygenme.com
Built a conversational chatbot with RAG over product docs using GPT-4, Pinecone vector DB, and Node.js. Deployed on AWS Lambda with API Gateway, handling 10k daily requests at <2s p95 latency.

[Block 4 Case 2]
Arcade - https://arcade.ai
AI-powered marketplace with thousands of concurrent users. Built scalable backend (Node.js + Redis) and React frontend, set up GitHub Actions CI/CD and Docker deployment on AWS ECS.

[Block 5 Closing]
10+ years full-stack, 5+ LLM integrations. React, Node.js, Python, Docker, AWS CDK. Available 40 hrs/week, rate $35/hr. I can start immediately.

[Block 6 CTA]
Let's jump on a short call to walk through your spec.

[Block 7 Signature]
Best,
Tilek
https://github.com/tilekchubakov

[Answers to your questions]
1. I'm strongest in AI integration (LLM APIs, embeddings, RAG) and DevOps (CI/CD, Docker, Terraform). I also do full-stack React/Node.js.
2. MyGenMe chatbot (above): built the entire pipeline from prompt design to production deployment on AWS Lambda.
3. Preferred stack: React + Node.js + MongoDB + Docker + AWS ECS. Why? Because it gives fast iteration for greenfield projects, scales for AI workloads, and keeps cloud costs predictable.


# ----------------------------------------------------------------------
# WRITING GUIDELINES (must follow for every generated letter)
# ----------------------------------------------------------------------
- Use only hyphen-minus " - " as dash, never em dash (—) or en dash (–).
- No bold text, no bullet points, no internal headers inside the letter.
- Case name and link on same line, e.g., "Project - https://example.com"
- Letter length: 150-200 words maximum.
- Screening answers always as a separate block after the signature.
- If client name is known, open with "Hi [Name],". If unknown, use no greeting or just "Hi there".
- If a test task or unpaid assessment is requested, reply in screening: "Test tasks are completed on a paid basis only. Terms can be discussed separately."
- For hourly jobs: include rate in Block 5 Closing.
- For fixed price: never mention rate.
- If urgent start required: add "available to start immediately" in Block 5.

Hook rules:
- Start with the statement like: "Let me be honest...", "From what I see...", "To be honest...", "Let me be direct...", or "Hi, the problem you come across is related to..." (with client name if known).
- Never start with "Most...".
- Must address a specific technical risk or business pain visible in the job description (e.g., scaling, security, cost, latency, compliance, greenfield uncertainty).
- One to two sentences maximum.
- No generic compliments.

Bridge rules:
- One sentence connecting the hook to the solution.
- Must name at least one concrete technology or method (e.g., "That's why I use Docker + GitHub Actions + Terraform").
- Avoid empty statements like "I focus on quality".

Case rules:
- Pull the two most relevant Priority 1 cases for the job (by keywords: AI, DevOps, stack, industry).
- Each case description must include: what was built, stack used, and a key result with metric (%, time saved, requests handled, etc.).
- If no perfect match exists, still provide two cases but explain briefly why relevant (e.g., "Matches your need for real-time processing").

Closing rules:
- Include years of experience + core stack match to job requirements + availability (40 hrs/week unless stated otherwise).
- Include hourly rate only if job is hourly; omit for fixed price.
- If job is urgent: add "available to start immediately".

Screening answers (if job has questions):
- Number each answer matching the job's question order.
- For "Describe recent experience" or "What project have you built": answer with full detail – project name, link, pain point, solution, stack, role, measurable result.
- For technical questions: give precise technical answer.
- For certifications: reference production experience instead (unless certification is mandatory).
- For "preferred stack and why": give explicit stack plus a reason tied to the job's needs (e.g., "Because it scales for AI workloads and keeps costs low").
- Never give a one-line generic answer.
"""

# ----------------------------------------------------------------------
# Путь к папке с кейсами (относительно корня проекта)
# ----------------------------------------------------------------------
CASES_DIR = Path(__file__).parent.parent / "backend" / "knowledge_base" / "cases"


async def load_case_content(case_id: str) -> str:
    case_path = CASES_DIR / f"{case_id}.md"
    if not case_path.exists():
        print(f"⚠️ Файл кейса {case_id} не найден по пути {case_path}")
        return ""
    with open(case_path, "r", encoding="utf-8") as f:
        return f.read()


def fix_newlines(text: str) -> str:
    text = text.replace('\\n', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


async def generate_initial_response(
    job_description: str,
    best_cases_with_content: list,
    user_profiles: list,
    selection_rules: dict,
    cover_letter_rules: str,
    letter_template: str,
    api_key: str,
    allowed_profiles: list = None,
    forbidden_case_ids: list = None
) -> dict:
    """
    Генерирует ответ для первого запроса (без истории).
    Формирует полный промпт с кейсами, правилами, профилями.
    """
    client_local = AsyncOpenAI(api_key=api_key)
    profiles_to_use = [p for p in user_profiles if allowed_profiles is None or p["name"] in allowed_profiles]

    main_part = f"""
    ### Cover letter writing rules (shortened)

    **Letter structure (blocks):**
    1. **Hook** – 1‑2 conversational sentences addressing a specific technical risk or business pain from the job description. Never start with "Most...".
    2. **Bridge** – one sentence connecting the hook to the solution, must name at least one concrete technology or method.
    3. **Case 1** – name and link on the same line, then 1‑2 lines: what was built, stack used, key result with metric.
    4. **Case 2** – same format.
    5. **Closing** – years of experience, core stack match, availability ({MAX_HOURS_PER_WEEKS}), hourly rate (if hourly), "available to start immediately" if urgent.
    6. **CTA** – "Let's talk."
    7. **Signature** – "Best, [Name]" (+ Portfolio link if stated in user profile).

    **Formatting:** Use only hyphen-minus " - " (not em dash or en dash). No bold, no bullet points, no headers. Letter length 150‑200 words. Screening answers as a separate block after the signature.

    **Case selection:** 
    - Use ONLY from the provided case list. Never invent cases. Select **exactly 2 most relevant** cases for the candidate, taking into account both the job requirements **and the candidate's own skills and past projects**. 
    - **Candidate‑centric selection:** Prefer cases that are listed in the candidate's `priority_cases` (if provided). Do not assign a case to a candidate if the candidate had no role in that case (i.e., cases are not shared across different candidates unless explicitly indicated). 
    - If the candidate has no relevant cases (or none of the cases match their profile).
    ---

    ### Step 0 – Job Analysis (semantic extraction)

    Extract the following **only if explicitly stated** in the job description text (do not infer):

    - `required_skills` – all skills from "Mandatory skills" section or explicitly mentioned.
    - `core_technical_terms` – specialized terms (e.g., "RAG", "knowledge graph", "multi-agent").
    - `business_pain_points` – specific client problems (e.g., "existing tools don't scale").
    - `screening_questions` – explicit questions (e.g., "Walk us through...").
    - `budget` – min, max, type (hourly/fixed).
    - `weekly_hours` – required hours per week (if given).

    In addition, collect **observations** – any explicit facts that may affect the proposal.  
    Each observation is a dict with `type` and `reasoning` (short justification).  
    Example: `{{"type": "loom_required", "reasoning": "Client explicitly asks to record a Loom explaining the approach"}}`.

    **Observation types (use exact strings):**
    - `loom_required` – client explicitly says "record a Loom" or "send a short video", but does NOT require it to be attached to the proposal.
    - `loom_mandatory_in_proposal` – client explicitly requires the video to be **attached** to the proposal (this is a red flag → SKIP).
    - `project_based` – job is described as "project-based", "one-off", "fixed scope", or similar (duration short).
    - `part_time` – client specifies fewer than 30 hours/week or "part‑time".
    - `urgent_start` – client explicitly wants start immediately or within days.
    - `nda_required` – client explicitly mentions NDA.
    - `test_task_paid` / `test_task_unpaid` – client explicitly asks for a test task, with payment status.
    - `screen_recorded_assessment` – client requires a screen‑recorded assessment (red flag).
    - `geo_restriction` – client restricts location (red flag).
    - `niche_stack` – client requires a very narrow technology that does not match profiles (red flag).
    - `no_job_details` – job description is empty or lacks technical details (red flag).

    **Important:** Do NOT add an observation unless the job description explicitly states it.  
    If a type is not applicable, omit it.

    **Red flags** are observations that cause SKIP (any of: `loom_mandatory_in_proposal`, `screen_recorded_assessment`, `geo_restriction`, `niche_stack`, `no_job_details`).  
    If any red flag is present, decision = SKIP.

    ---

    ### Step 1 – Job Evaluation (PASS/SKIP) for each candidate

    For **each candidate** in the provided list, evaluate independently:
    
    1. **Budget mismatch**: If budget is extracted and candidate's min_salary > budget['max'] → SKIP.
    
    2. **Hours limit**: If weekly_hours > {MAX_HOURS_PER_WEEKS} → SKIP.
    
    3. **Red flag**: If any red flag observation exists → SKIP.
    
    4. **Skill mismatch**: If the candidate lacks a couple of skills required, but overall candidate's stack is relevant DO NOT skip (be less strict with that point). If the candidate specializes in a completely different field and do not have any real chances of applying → SKIP.
    
    5. Otherwise → PASS.

    After evaluation, collect **all observations** (including skill mismatches) into `observations`.  
    The `reasoning` must explicitly state why the candidate passed or failed.
    
    ---

    ### Step 2 – Candidate‑specific generation

    For **each candidate** in the provided profiles list (JSON below), generate a JSON object with the following fields:

    - `job_evaluation` (object with `decision`, `reasoning`, `observations`)
    - `selected_cases` (array of exactly 2 case objects, each with `case_id`, `name`, `link`, `reasoning`)
    - `hook_options` (array of 3 hook objects, each with `text` and `specificity_score`)
    - `selected_hook` (string, the best hook)
    - `cover_letter` (string, the generated letter)
    - `screening_answers` (string, answers to questions or empty)

    Do **not** include a `selected_profile` field – the profile is already identified by the outer key.

    **Important:**  
    - For each candidate, use their own `min_salary_per_hour_usd` and `portfolio_link` (if provided).  
    - Cases must be selected independently for each candidate.  
    - You may reuse cases across candidates; no need to forbid duplicates unless instructed otherwise.
    - **Skills validation:** When generating the letter and screening answers, you may only mention a required skill (from the job description) if that skill is explicitly present in the candidate's `skills` list or is clearly demonstrated by at least one of the selected cases. Do not claim the candidate has experience in a skill that is not supported by their profile or cases. In particular, do not mention "HIPAA" unless the candidate's profile or a case explicitly contains evidence of HIPAA work (e.g., BAA, PHI handling, compliance).
    - **Candidate‑centric case selection:** When selecting cases for a candidate, prefer cases that are listed in the candidate's `priority_cases` (if provided) and that match the candidate's own skills and past projects. Do not assign a case to a candidate if the candidate had no role in that case (e.g., a case from another candidate's portfolio). Use only cases that belong to the candidate's own experience. If the candidate has no relevant cases, you may leave `selected_cases` empty and the decision will be SKIP.

    ---
    
    ### Step 3 – Cover Letter Generation

    - Use `selected_hook` as Block 1.
    - Weave 3‑5 required skills into case descriptions or closing.
    - Strictly follow structure and formatting rules.
    - Use `\n` for line breaks inside JSON strings.
    - **If observation `loom_required` exists**: add the phrase "I'll record a Loom as requested." in the letter (no details). Do not describe Loom content in letter or screening answers.
    - **If observation `nda_required` exists**: mention in closing that you are willing to sign.
    - **If observation `test_task_unpaid` exists**: in screening answers state that test tasks are completed on a paid basis only.

    **Personalization and uniqueness (CRITICAL):**
    - Every field in `letter_parts` (hook, bridge, case1_text, case2_text, closing, cta) MUST be unique per candidate. Even if two candidates share 90% of their tech stack, the generated text must differ substantially in phrasing, sentence structure, angles, and chosen details.
    - **Hook variation:** Rotate the opening angle across candidates (do not use the same pattern). Possible angles: technical risk, missed revenue, slow time-to-market, scalability bottleneck, user experience gap, cost inefficiency, security concern, team velocity. Phrase each hook differently, avoiding templates like "You are not considering...".
    - **Bridge variation:** Always connect the candidate’s exact stack to a specific pain point from the job description. Use different sentence structures: start with the technology, start with the problem, or start with the outcome. Never reuse the same bridging phrase for different candidates.
    - **Case uniqueness:** If two candidates worked on similar projects (e.g., both built an AI marketplace), select different aspects to highlight: one case focuses on latency reduction, the other on recommendation accuracy; one mentions concrete metrics like "40% load time drop", the other mentions "handled 10k concurrent users". Use different project names/URLs as given in the candidate's data. If a candidate has multiple projects, pick a diverse pair that showcases different skills.
    - **Closing uniqueness:** Vary the order of skills, emphasize different top skills, and rephrase availability details. Instead of a rigid "X years full-stack, Y years cloud. Tech stack A, B, C. Rate $Z", change the flow: "I bring 8 years of production experience, most recently focused on cloud-native architectures with AWS and Kubernetes. I'm available 40 hrs/week at $60/hr, ready to start in 3 days."
    - **CTA uniqueness:** Rotate through different natural calls-to-action: "Let's talk.", "Open to a quick call?", "I'd love to discuss how I can help.", "When works for you?" – but adjust to match the letter's tone.
    - **Signature:** Always use the candidate’s provided name and link(s). This part is inherently tied to the individual, but ensure it is populated from the input data and not hardcoded.
    - **No copy-paste patterns:** Avoid repeating any full phrase, transitional sentence, or list structure from other candidates. Treat each generation as completely independent. If you notice similar stacks, consciously rewrite every sentence.
    - **Job description terms:** Weave in precise terminology from the job description (exact technology names, business pain points, industry jargon). Do not use generic phrases like "I have experience with AI/ML" – instead say "I deployed a RAG pipeline with LangChain and Pinecone handling 10k requests/day."
    - **No hallucinated skills:** Never write a sentence like "I have experience with X" unless X is present in the candidate's `skills` list or is explicitly described in one of the selected cases. If a required skill from the job is missing from the candidate, simply omit it from the letter – do not invent it.
    
    **Case description format (one‑shot example):**
    Arcade - Developed an AI-powered marketplace with real-time recommendation engine using Python, FastAPI, and PostgreSQL. Reduced page load time by 40% and increased user engagement by 25%.
    
    - Start with the case name, then a space, then the link **only if it's a valid external client website** (not internal Interexy pages, not app stores). If no valid link, write only the case name.
    - After the name (and optional link), write a **newline** (`\n`), then the description.
    - The description must include: what was built, specific technologies used, and a key result with a metric (%, numbers).
    
    ### Output format (strict JSON)

    Return a **single JSON object** where **keys are candidate names** (exactly as they appear in the profiles list) and **values are objects** with the following fields:
    - `job_evaluation` (object with `decision`, `reasoning`, `observations`)
    - `selected_cases` (array of exactly 2 case objects, each with `case_id`, `name`, `link`, `reasoning`)
    - `hook_options` (array of 3 hook objects, each with `text` and `specificity_score`)
    - `selected_hook` (string, the best hook)
    - **`letter_parts`** (object with fields: `hook`, `bridge`, `case1_text`, `case2_text`, `closing`, `cta`, `signature`)
    - `screening_answers` (string, answers to questions or empty)
    
    **Important:** Do **not** include a field named `cover_letter`. Instead, use `letter_parts` as described.
    
    Example of `letter_parts` (inside a candidate object):

    ```json
    "letter_parts": {{
      "hook": "You are not considering the significant technical risk...",
      "bridge": "I build full stack platforms using React for complex admin UIs, Python for backend services...",
      "case1_text": "Arcade - https://arcade.ai\\nDeveloped an AI-powered marketplace with real-time recommendation engine using Python, FastAPI, and PostgreSQL. Reduced page load time by 40%.",
      "case2_text": "Classful - https://classful.com\\nEdTech SaaS serving 1M+ MAU. Rewrote backend from monolith to microservices with Node.js, Docker, and Kubernetes. Cut server costs by 30%.",
      "closing": "15+ years full-stack, 5+ years cloud/DevOps. React, Node.js, Python, Docker, AWS CDK. Available 40 hrs/week, rate $50/hr. I can start immediately.",
      "cta": "Let's talk.",
      "signature": "Best, Tilek\\nhttps://github.com/tilekchubakov"
    }}
    ```
    
    Example for two candidates:

    ```json
    {{
      "Tilek Chubakov": {{
        "job_evaluation": {{
          "decision": "",
          "reasoning": "...",
          "observations": []
        }},
        "selected_cases": [
          {{ "case_id": "...", "name": "...", "link": "...", "reasoning": "..." }},
          {{ "case_id": "...", "name": "...", "link": "...", "reasoning": "..." }}
        ],
        "hook_options": [
          {{ "text": "...", "specificity_score": 0 }},
          {{ "text": "...", "specificity_score": 0 }},
          {{ "text": "...", "specificity_score": 0 }}
        ],
        "selected_hook": "...",
        "letter_parts": {{
          "hook": "...",
          "bridge": "...",
          "case1_text": "...",
          "case2_text": "...",
          "closing": "...",
          "cta": "...",
          "signature": "..."
        }},
        "screening_answers": "..."
      }},
      "Victoria": {{
        "job_evaluation": {{
          "decision": "",
          "reasoning": "...",
          "observations": []
        }}
      }},
      "Vicode Solutions": {{
        "job_evaluation": {{
          "decision": "",
          "reasoning": "...",
          "observations": []
        }},
        "selected_cases": [
          {{ "case_id": "...", "name": "...", "link": "...", "reasoning": "..." }},
          {{ "case_id": "...", "name": "...", "link": "...", "reasoning": "..." }}
        ],
        "hook_options": [
          {{ "text": "...", "specificity_score": 0 }},
          {{ "text": "...", "specificity_score": 0 }},
          {{ "text": "...", "specificity_score": 0 }}
        ],
        "selected_hook": "...",
        "letter_parts": {{
          "hook": "...",
          "bridge": "...",
          "case1_text": "...",
          "case2_text": "...",
          "closing": "...",
          "cta": "...",
          "signature": "..."
        }},
        "screening_answers": "..."
      }}
    }}
    ```
    
    If a candidate's decision is SKIP, you may omit all fields except job_evaluation (or include empty/placeholder values – but including only job_evaluation is acceptable).
    Always include observations array (empty if none).
    Each screening answer must start on a new line with number, dot, space.
    Do not copy example values; generate actual data from the job analysis.
    
    ### Candidate profiles
    {json.dumps(profiles_to_use, indent=2, ensure_ascii=False)}
"""

    cases_text = ""
    for idx, case in enumerate(best_cases_with_content, 1):
        cases_text += f"\n=== КЕЙС {idx} ===\nID: {case.get('id')}\nНазвание: {case.get('name', 'Unknown')}\nСсылка: {case.get('link', 'N/A')}\nСодержание:\n{case.get('content', '')[:3000]}\n"

    prompt = f"""
Ты – AI-ассистент по подбору персонала для IT-вакансий. Твоя задача – оценить вакансию, выбрать наиболее подходящего кандидата из списка профилей и сгенерировать готовое письмо-отклик и ответы на скрининг-вопросы (если есть).

### Описание вакансии:
{job_description}

### Список релевантных кейсов компании (каждый с ID, названием, ссылкой и полным описанием):
{cases_text}

### Базовые правила отбора работы (общие для всех кандидатов):
{json.dumps(selection_rules, indent=2, ensure_ascii=False)}

{main_part}
"""
    system_message = {"role": "system", "content": "Ты – экспертный помощник по подбору персонала для IT-компаний. Отвечай только JSON."}
    messages = [system_message, {"role": "user", "content": prompt}]

    try:
        response = await client_local.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)

        # Постобработка для нового формата (letter_parts)
        if isinstance(result, dict):
            for name, data in result.items():
                if not isinstance(data, dict):
                    continue
                # Обработка letter_parts
                if 'letter_parts' in data and isinstance(data['letter_parts'], dict):
                    for part in ['hook', 'bridge', 'case1_text', 'case2_text', 'closing', 'cta', 'signature']:
                        if part in data['letter_parts'] and isinstance(data['letter_parts'][part], str):
                            data['letter_parts'][part] = fix_newlines(data['letter_parts'][part])
                # Обработка остальных текстовых полей
                if 'screening_answers' in data and isinstance(data['screening_answers'], str):
                    data['screening_answers'] = fix_newlines(data['screening_answers'])
                if 'selected_hook' in data and isinstance(data['selected_hook'], str):
                    data['selected_hook'] = fix_newlines(data['selected_hook'])
                if 'hook_options' in data and isinstance(data['hook_options'], list):
                    for opt in data['hook_options']:
                        if 'text' in opt and isinstance(opt['text'], str):
                            opt['text'] = fix_newlines(opt['text'])
                # Гарантия наличия обязательных полей
                data.setdefault('job_evaluation',
                                {"decision": "SKIP", "reasoning": "Missing evaluation", "observations": []})
                data.setdefault('selected_cases', [])
                data.setdefault('hook_options', [])
                data.setdefault('selected_hook', "")
                data.setdefault('letter_parts', {})
                data.setdefault('screening_answers', "")
        else:
            raise ValueError(f"Expected dict, got {type(result)}")
        return result
    except Exception as e:
        print(f"Initial generation error: {e}")
        return {p["name"]: {
            "job_evaluation": {"decision": "SKIP", "reasoning": f"Error: {e}", "observations": []},
            "selected_cases": [],
            "hook_options": [],
            "selected_hook": "",
            "letter_parts": {},
            "screening_answers": ""
        } for p in profiles_to_use}


async def generate_edit_response(
    edit_request: str,
    previous_response: dict,
    conversation_history: list,
    api_key: str
) -> dict:
    client_local = AsyncOpenAI(api_key=api_key)
    system_message = {
        "role": "system",
        "content": (
            "Ты – помощник по редактированию сгенерированных писем. "
            "Пользователь хочет изменить предыдущий ответ. Ты получишь JSON с предыдущим ответом "
            "и запрос на изменение. Верни обновлённый JSON в том же формате, что и исходный. "
            "Не меняй структуру, только поля, которые нужно отредактировать (например, letter_parts, selected_hook, screening_answers). "
            "Если запрос неясен, оставь поля без изменений."
        )
    }
    messages = [system_message]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "assistant", "content": json.dumps(previous_response, ensure_ascii=False)})
    messages.append({"role": "user", "content": f"Edit request: {edit_request}"})

    try:
        response = await client_local.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        # Постобработка для letter_parts
        if 'letter_parts' in result and isinstance(result['letter_parts'], dict):
            for part in ['hook', 'bridge', 'case1_text', 'case2_text', 'closing', 'cta', 'signature']:
                if part in result['letter_parts'] and isinstance(result['letter_parts'][part], str):
                    result['letter_parts'][part] = fix_newlines(result['letter_parts'][part])
        if 'screening_answers' in result and isinstance(result['screening_answers'], str):
            result['screening_answers'] = fix_newlines(result['screening_answers'])
        if 'selected_hook' in result and isinstance(result['selected_hook'], str):
            result['selected_hook'] = fix_newlines(result['selected_hook'])
        if 'hook_options' in result and isinstance(result['hook_options'], list):
            for opt in result['hook_options']:
                if 'text' in opt and isinstance(opt['text'], str):
                    opt['text'] = fix_newlines(opt['text'])
        return result
    except Exception as e:
        print(f"Edit generation error: {e}")
        return previous_response




def append_to_google_sheet(job_description: str, profile_name: str, cover_letter: str, screening_answers: str = ""):
    """
    Записывает данные в Google Sheets таблицу.
    """
    try:
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        worksheet_name = os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Sheet1")

        if not creds_json or not spreadsheet_id:
            print("⚠️ Google Sheets credentials not configured, skipping logging")
            return

        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client_gspread = gspread.authorize(creds)

        sheet = client_gspread.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        now = datetime.now().isoformat()

        # Ограничиваем длину полей
        job_preview = job_description[:5000] + "..." if len(job_description) > 5000 else job_description
        letter_preview = cover_letter[:5000] + "..." if len(cover_letter) > 5000 else cover_letter
        screening_preview = screening_answers[:5000] + "..." if len(screening_answers) > 5000 else screening_answers

        row = [now, job_preview, profile_name, letter_preview, screening_preview]
        sheet.append_row(row)
        print(f"✅ Записано в Google Sheets: {profile_name} - PASS")
    except Exception as e:
        import traceback
        print(f"❌ Ошибка записи в Google Sheets: {e}")
        traceback.print_exc()


# ----------------------------------------------------------------------
# Пайплайн обработки (без GUI)
# ----------------------------------------------------------------------
async def process_job(job_description: str, conversation_history: list = None, saved_state: dict = None):
    try:
        if conversation_history and len(conversation_history) > 1:
            if not saved_state:
                return {"error": "No saved state for editing."}, None
            edit_request = job_description
            old_responses = saved_state.get("responses", {})
            new_responses = {}
            for name, old_resp in old_responses.items():
                new_resp = await generate_edit_response(
                    edit_request=edit_request,
                    previous_response=old_resp,
                    conversation_history=conversation_history,
                    api_key=OPENAI_API_KEY
                )
                new_responses[name] = new_resp
            new_saved_state = {
                "cases": saved_state["cases"],
                "responses": new_responses
            }
            return new_responses, new_saved_state
        else:
            best_cases = await rag.retrieve_cases(job_description, OPENAI_API_KEY)
            if not best_cases:
                return {"error": "No relevant cases found."}, None
            best_cases_with_content = []
            for case in best_cases:
                case_id = case.get("id")
                if not case_id:
                    continue
                content = await load_case_content(case_id)
                if content:
                    best_cases_with_content.append({
                        "id": case_id,
                        "name": case.get("name", ""),
                        "link": case.get("link", ""),
                        "content": content
                    })
            if not best_cases_with_content:
                return {"error": "No cases could be loaded."}, None
            all_responses = await generate_initial_response(
                job_description=job_description,
                best_cases_with_content=best_cases_with_content,
                user_profiles=user_profiles,
                selection_rules=selection_rules,
                cover_letter_rules=cover_letter_rules,
                letter_template=letter_template,
                api_key=OPENAI_API_KEY,
                allowed_profiles=None
            )
            new_saved_state = {
                "cases": best_cases_with_content,
                "responses": all_responses
            }
            return all_responses, new_saved_state
    except Exception as e:
        return {"error": f"Processing failed: {str(e)}"}, None
