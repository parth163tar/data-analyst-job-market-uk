import pandas as pd
import numpy as np
import re
from pathlib import Path

# -----------------------------
# 1. Load data
# -----------------------------
DATA_PATH = Path("uk_data_analyst_jobs.csv")   # adjust if needed

df = pd.read_csv(DATA_PATH)
print("Rows:", len(df))
df.head()
# -----------------------------
# 2. Basic text cleaning
# -----------------------------
def clean_text(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text).lower()
    # Replace newlines / tabs
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()

df["title_clean"] = df["title"].apply(clean_text)
df["description_clean"] = df["description"].apply(clean_text)

df[["title", "title_clean", "description_clean"]].head()
# -----------------------------
# 3. Skill dictionary
# -----------------------------
# Keys = canonical skill names
# Values = list of phrases/variants to search for
SKILL_DICT = {
    "Excel": [
        r"\bexcel\b",
        r"\bms excel\b",
        r"\bspreadsheet(s)?\b"
    ],
    "SQL": [
        r"\bsql\b",
        r"\bmysql\b",
        r"\bpostgresql\b",
        r"\bpostgres\b",
        r"\btsql\b",
        r"\bms sql\b"
    ],
    "Python": [
        r"\bpython\b",
        r"\bpandas\b",
        r"\bnumpy\b",
        r"\bscikit-learn\b",
        r"\bsklearn\b"
    ],
    "R": [
        r"\br language\b",
        r"\b r\b",
        r"\br studio\b",
        r"\br-studio\b"
    ],
    "Power BI": [
        r"\bpower bi\b",
        r"\bdax\b"
    ],
    "Tableau": [
        r"\btableau\b"
    ],
    "Looker": [
        r"\blooker\b",
        r"\blooker studio\b",
        r"\bdata studio\b"
    ],
    "Excel VBA": [
        r"\bvba\b",
        r"\bexcel vba\b",
        r"\bmacros?\b"
    ],
    "AWS": [
        r"\baws\b",
        r"\bamazon web services\b"
    ],
    "Azure": [
        r"\bazure\b",
        r"\bazure synapse\b",
        r"\bazure data factory\b"
    ],
    "GCP": [
        r"\bgcp\b",
        r"\bgoogle cloud\b",
        r"\bbigquery\b"
    ],
    "Statistics": [
        r"\bstatistics\b",
        r"\bstatistical\b",
        r"\bhypothesis testing\b",
        r"\bregression\b"
    ],
    "Machine Learning": [
        r"\bmachine learning\b",
        r"\bml models?\b",
        r"\bclassification\b",
        r"\bclustering\b"
    ],
    "Business Analysis": [
        r"\bbusiness analysis\b",
        r"\bbusiness analyst\b",
        r"\brequirements gathering\b",
        r"\bstakeholder(s)?\b",
    ],
    "Communication": [
        r"\bcommunication skills\b",
        r"\bstrong communicator\b",
        r"\bpresentation skills\b",
    ],
    "PowerPoint": [
        r"\bpowerpoint\b",
        r"\bpower point\b",
        r"\bslide deck(s)?\b",
    ]
}
# -----------------------------
# 4. Skill tagging
# -----------------------------
def detect_skills(text: str, skill_dict: dict) -> dict:
    """
    Returns a dict: {skill_name: 0/1}
    """
    if pd.isna(text):
        text = ""
    text = str(text).lower()
    
    result = {}
    for skill, patterns in skill_dict.items():
        found = False
        for pat in patterns:
            if re.search(pat, text):
                found = True
                break
        result[skill] = int(found)
    return result

# Apply to combined text
combined_text = (df["title_clean"].fillna("") + " " + df["description_clean"].fillna(""))

skill_rows = combined_text.apply(lambda x: detect_skills(x, SKILL_DICT))

# skill_rows is a Series of dicts – convert to DataFrame
skill_df = pd.DataFrame(list(skill_rows))

skill_df.head()
# Prefix columns with "has_"
skill_df = skill_df.add_prefix("has_")

df_skills = pd.concat([df, skill_df], axis=1)

print(df_skills.shape)
df_skills.head()
# -----------------------------
# 5. Skill frequency summary
# -----------------------------
skill_cols = [c for c in df_skills.columns if c.startswith("has_")]

skill_counts = df_skills[skill_cols].sum().sort_values(ascending=False)
skill_counts = skill_counts.rename_axis("skill").reset_index(name="num_jobs")
skill_counts["skill"] = skill_counts["skill"].str.replace("has_", "", regex=False)

skill_counts
total_jobs = len(df_skills)
skill_counts["percent_of_jobs"] = (skill_counts["num_jobs"] / total_jobs * 100).round(1)
skill_counts
# -----------------------------
# 6. Salary vs skill (safe version)
# -----------------------------
df_skills["salary_avg"] = df_skills[["salary_min", "salary_max"]].mean(axis=1)

# Keep only rows where salary exists
df_salary = df_skills.dropna(subset=["salary_avg"])

if df_salary.empty:
    print("⚠️ No salary data available in the dataset — skipping salary analysis.")
    salary_skill_df = pd.DataFrame()  # empty dataframe
else:
    salary_skill_stats = []

    for col in skill_cols:
        skill_name = col.replace("has_", "")
        has_skill = df_salary[df_salary[col] == 1]
        no_skill  = df_salary[df_salary[col] == 0]

        # skip skills with too little data
        if len(has_skill) < 5:
            continue

        salary_skill_stats.append({
            "skill": skill_name,
            "jobs_with_skill": len(has_skill),
            "avg_salary_with_skill": has_skill["salary_avg"].mean(),
            "avg_salary_without_skill": no_skill["salary_avg"].mean() if len(no_skill) > 0 else None,
        })

    salary_skill_df = pd.DataFrame(salary_skill_stats)

    if salary_skill_df.empty:
        print("⚠️ Not enough salary samples per skill to compute salary insights.")
    else:
        salary_skill_df.sort_values(
            by="avg_salary_with_skill",
            ascending=False,
            inplace=True
        )

salary_skill_df
df_skills["salary_min"].notna().sum(), df_skills["salary_max"].notna().sum()
# -----------------------------
# 7. Save enriched datasets
# -----------------------------
OUTPUT_DIR = Path("data") / "cleaned"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df_skills.to_csv(OUTPUT_DIR / "jobs_with_skills.csv", index=False, encoding="utf-8-sig")
skill_counts.to_csv(OUTPUT_DIR / "skill_counts.csv", index=False, encoding="utf-8-sig")
salary_skill_df.to_csv(OUTPUT_DIR / "skill_salary_stats.csv", index=False, encoding="utf-8-sig")

print("✅ Saved:")
print(" - jobs_with_skills.csv")
print(" - skill_counts.csv")
print(" - skill_salary_stats.csv")
