"""
skills_db.py
-------------
A curated taxonomy of skills used for extraction and matching.
Organized by category so the app can show category-level breakdowns
(e.g. "Programming Languages", "Cloud & DevOps", "Soft Skills").

This is intentionally a plain Python data structure (not a 3rd-party
dependency) so the app works fully offline for extraction, and only
calls an external API for the "AI-generated improvement suggestions"
feature.
"""

SKILLS_DB = {
    "Programming Languages": [
        "python", "java", "javascript", "typescript", "c++", "c#", "c",
        "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "scala",
        "r", "matlab", "perl", "dart", "objective-c", "sql", "bash", "shell scripting"
    ],
    "Web Development": [
        "html", "css", "react", "react.js", "angular", "vue", "vue.js", "next.js",
        "node.js", "express.js", "django", "flask", "fastapi", "spring boot",
        "asp.net", "ruby on rails", "jquery", "bootstrap", "tailwind css",
        "webpack", "graphql", "rest api", "restful api", "websockets"
    ],
    "Data Science & ML": [
        "machine learning", "deep learning", "natural language processing", "nlp",
        "computer vision", "data science", "data analysis", "data analytics",
        "statistics", "scikit-learn", "tensorflow", "pytorch", "keras",
        "pandas", "numpy", "matplotlib", "seaborn", "opencv", "xgboost",
        "lightgbm", "hugging face", "transformers", "llm", "large language models",
        "generative ai", "feature engineering", "model deployment", "mlops",
        "a/b testing", "predictive modeling", "time series analysis", "regression",
        "classification", "clustering", "reinforcement learning"
    ],
    "Databases": [
        "mysql", "postgresql", "mongodb", "sqlite", "oracle", "sql server",
        "redis", "cassandra", "dynamodb", "elasticsearch", "firebase",
        "neo4j", "mariadb", "nosql", "database design", "data warehousing",
        "etl", "snowflake", "bigquery"
    ],
    "Cloud & DevOps": [
        "aws", "amazon web services", "azure", "gcp", "google cloud platform",
        "docker", "kubernetes", "jenkins", "ci/cd", "terraform", "ansible",
        "linux", "git", "github", "gitlab", "bitbucket", "devops",
        "microservices", "serverless", "lambda", "cloudformation", "nginx",
        "load balancing", "monitoring", "prometheus", "grafana"
    ],
    "Project Management & Tools": [
        "agile", "scrum", "kanban", "jira", "confluence", "trello", "asana",
        "project management", "product management", "stakeholder management",
        "risk management", "pmp", "six sigma", "waterfall", "sprint planning"
    ],
    "Soft Skills": [
        "communication", "leadership", "teamwork", "collaboration",
        "problem solving", "critical thinking", "time management",
        "adaptability", "creativity", "attention to detail",
        "presentation skills", "negotiation", "conflict resolution",
        "decision making", "mentoring", "public speaking", "analytical skills"
    ],
    "Design": [
        "figma", "adobe xd", "sketch", "photoshop", "illustrator",
        "ui/ux design", "ui design", "ux design", "wireframing", "prototyping",
        "user research", "design systems", "indesign", "after effects"
    ],
    "Business & Finance": [
        "financial modeling", "excel", "powerpoint", "financial analysis",
        "budgeting", "forecasting", "accounting", "sap", "salesforce",
        "crm", "erp", "business analysis", "market research", "valuation",
        "power bi", "tableau", "looker"
    ],
    "Testing & QA": [
        "unit testing", "selenium", "test automation", "manual testing",
        "qa", "quality assurance", "pytest", "junit", "cypress", "postman",
        "load testing", "regression testing"
    ],
    "Mobile Development": [
        "android", "ios", "react native", "flutter", "xamarin", "swiftui",
        "mobile app development"
    ],
}

# Flat lookup: skill -> category, all lowercase for matching
SKILL_TO_CATEGORY = {
    skill: category
    for category, skills in SKILLS_DB.items()
    for skill in skills
}

# All skills as a flat sorted list (longest first helps phrase matching)
ALL_SKILLS = sorted(SKILL_TO_CATEGORY.keys(), key=len, reverse=True)

# Common aliases / synonyms -> canonical skill name
ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "ml": "machine learning",
    "dl": "deep learning",
    "cv": "computer vision",
    "k8s": "kubernetes",
    "aws cloud": "aws",
    "postgres": "postgresql",
    "tf": "tensorflow",
    "sklearn": "scikit-learn",
    "node": "node.js",
    "reactjs": "react.js",
    "react js": "react.js",
    "vuejs": "vue.js",
    "nextjs": "next.js",
    "oop": "object oriented programming",
    "genai": "generative ai",
    "power point": "powerpoint",
}
