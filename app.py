import streamlit as st
import re

# Optional: Google Gemini (only needed when you click "Tailor Resume")
try:
    import google.generativeai as genai
except Exception:
    genai = None

st.set_page_config(page_title="ATS Resume Tailor", page_icon="🧠", layout="centered")

st.title("🧠 ATS Resume Tailor")
st.write("Paste each section of your resume, add a job description, and get a tailored, ATS-friendly version. Just copy and paste the results!")

# --- UI: Paste Resume Sections ---
with st.expander("Paste resume sections separately", expanded=True):
    summary_text = st.text_area("Summary", height=80, placeholder="E.g. Experienced software engineer with 5+ years in fintech…")
    skills_text = st.text_area("Skills", height=80, placeholder="E.g. Python, SQL, AWS, Docker…")
    experience_text = st.text_area("Work Experience", height=150, placeholder="E.g. Software Engineer, ABC Inc, 2020–2023\n- Built...")
    education_text = st.text_area("Education", height=60, placeholder="E.g. B.Tech in Computer Science, XYZ University, 2019")
    certifications_text = st.text_area("Certifications (optional)", height=50, placeholder="E.g. AWS Certified Solutions Architect")
    projects_text = st.text_area("Projects (optional)", height=60, placeholder="E.g. Developed a real-time trading dashboard…")

jd_text = st.text_area("Paste Job Description", height=180, placeholder="Paste the job description here…")

col_a, col_b = st.columns(2)
with col_a:
    draft_btn = st.button("✨ Tailor Resume")
with col_b:
    clear_btn = st.button("Clear All")

if clear_btn:
    st.experimental_rerun()

# --- Sidebar: Gemini API Key ---
with st.sidebar:
    st.header("Settings")
    provider = st.selectbox("Model", ["Gemini 1.5 Flash"], index=0)
    api_key = st.text_input("GEMINI_API_KEY (or set via Streamlit Secrets)", type="password")
    use_secrets = st.checkbox("Use Streamlit Secrets", True)
    if use_secrets:
        api_key = st.secrets.get("GEMINI_API_KEY", api_key)

# --- Main Flow ---
if draft_btn:
    # 1) Gather resume sections
    resume_sections = {
        "SUMMARY": summary_text,
        "SKILLS": skills_text,
        "EXPERIENCE": experience_text,
        "EDUCATION": education_text,
        "CERTIFICATIONS": certifications_text,
        "PROJECTS": projects_text,
    }
    filled_sections = {k: v.strip() for k, v in resume_sections.items() if v.strip()}

    if not filled_sections:
        st.warning("Please fill in at least one resume section.")
        st.stop()
    if not jd_text.strip():
        st.warning("Please paste the job description.")
        st.stop()
    if genai is None:
        st.error("google-generativeai not installed.")
        st.stop()
    if not api_key:
        st.info("Add your GEMINI_API_KEY in the sidebar or Streamlit Secrets.")
        st.stop()

    # 2) Build resume text from sections
    resume_text = "\n".join(f"{section}\n{content}" for section, content in filled_sections.items())

    # 3) Prompt — strict ATS formatting + honesty
    system_rules = """
You are an expert resume writer specializing in ATS compliance.

Rules:
- Keep it factual. Do NOT invent experience, employers, or dates.
- Use plain, ATS-safe formatting: no tables, columns, images, headers/footers.
- Standard section headings: SUMMARY, SKILLS, EXPERIENCE, EDUCATION, CERTIFICATIONS (if any), PROJECTS (optional).
- Bullets should be concise and results-oriented. Prefer '-' bullets.
- Mirror relevant keywords/phrases from the JD naturally (no stuffing).
- Keep to 1–2 pages of text.
- Preserve job titles/employers/dates from the original resume unless user content provides updates.
- Where there is a relevant achievement you can rephrase it using JD language, but do not fabricate.

Return TWO blocks in this exact format:

<RESUME>
[ATS-optimized resume only, clearly separated by section headings]
</RESUME>

<MATCH_REPORT>
- Top keywords used
- Notable gaps (if any)
- Suggestions to strengthen fit (skills, certs, metrics)
</MATCH_REPORT>
""".strip()

    user_payload = f"""
[RESUME]
{resume_text}

[JOB_DESCRIPTION]
{jd_text}
""".strip()

    # 4) Model call
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    with st.spinner("Tailoring your resume…"):
        resp = model.generate_content([system_rules, user_payload])
        content = resp.text or ""

    # 5) Parse response
    resume_block = ""
    report_block = ""
    m1 = re.search(r"<RESUME>(.*?)</RESUME>", content, flags=re.DOTALL | re.IGNORECASE)
    m2 = re.search(r"<MATCH_REPORT>(.*?)</MATCH_REPORT>", content, flags=re.DOTALL | re.IGNORECASE)
    if m1:
        resume_block = m1.group(1).strip()
    if m2:
        report_block = m2.group(1).strip()
    if not resume_block:
        resume_block = content.strip()

    # 6) Display tailored sections for copy-paste
    st.subheader("Tailored Resume (ATS-friendly, copy-paste below)")

    section_titles = ["SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION", "CERTIFICATIONS", "PROJECTS"]
    found_any = False
    for title in section_titles:
        m = re.search(rf"{title}\n(.*?)(?=\n[A-Z ]+\n|$)", resume_block, re.DOTALL)
        if m and m.group(1).strip():
            st.markdown(f"**{title.title()}**")
            st.code(m.group(1).strip(), language="text")
            found_any = True
    if not found_any:
        st.code(resume_block, language="text")

    st.subheader("Match Report")
    st.write(report_block if report_block else "—")

st.caption("Tip: Copy each section above and paste into your resume. Keep bullets concise and include measurable impact (%, time saved, cost reduced).")
