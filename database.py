from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from datetime import date
import os

load_dotenv()

db_connection_string = os.getenv('DB_CONNECTION_STRING')

engine = create_engine(
    db_connection_string,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    pool_pre_ping=True,
    pool_timeout=10
)

import time

# Lightweight in-memory caches to make page transitions and API responses near-instantaneous
_jobs_cache = {"data": None, "timestamp": 0}
_job_single_cache = {}


def load_jobs_from_db(force_refresh=False):
    global _jobs_cache
    now = time.time()
    if not force_refresh and _jobs_cache["data"] is not None and (now - _jobs_cache["timestamp"]) < 60:
        return _jobs_cache["data"]

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM jobs"))
        jobs = []
        for row in result.all():
            jobs.append(dict(row._mapping))
        _jobs_cache["data"] = jobs
        _jobs_cache["timestamp"] = now
        return jobs


def load_one_job_from_db(job_id, force_refresh=False):
    global _job_single_cache
    now = time.time()
    if not force_refresh and job_id in _job_single_cache:
        data, ts = _job_single_cache[job_id]
        if (now - ts) < 60:
            return data

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM jobs WHERE job_id = :val"),
            {"val": job_id}
        )
        job = result.first()
        if job is None:
            return None
        res = dict(job._mapping)
        _job_single_cache[job_id] = (res, now)
        return res


def add_application_to_db(user_id, job_id, data):
    with engine.connect() as conn:
        query = text(
            """INSERT INTO applications (user_id, job_id, status, applied_on) values (:user_id, :job_id, :status, :applied_on)"""
                    )

        conn.execute(query, {
                    "user_id" : user_id,
                    "job_id" : job_id,
                    "status" : "",
                    "applied_on" : date.today()
                })
        conn.commit()


def add_users_to_db(
    name,
    email,
    password,
    headline="",
    linkedin="",
    education="",
    experience="",
    resume=""
):
    with engine.connect() as conn:
        query = text("""
            INSERT INTO users (
                name,
                email,
                password,
                headline,
                linkedin_url,
                education,
                work_experience,
                resume_url
            )
            VALUES (
                :name,
                :email,
                :password,
                :headline,
                :linkedin_url,
                :education,
                :work_experience,
                :resume_url
            )
        """)

        conn.execute(query, {
            "name": name,
            "email": email,
            "password": password.decode("utf-8"),
            "headline": headline or "",
            "linkedin_url": linkedin or "",
            "education": education or "",
            "work_experience": experience or "",
            "resume_url": resume or "",
        })
        conn.commit()


def get_user_from_db(email):
    with engine.connect() as conn:
        query = text(
            "SELECT * FROM users WHERE email = :email"
        )

        result = conn.execute(query,{
                    "email" : email,
                })
        
        user = result.fetchone()
        if user is None:
            return None

        return dict(user._mapping)
        

def get_user_info_from_db(user_id):
    with engine.connect() as conn:
        query = text(
            "SELECT * FROM users WHERE user_id = :user_id"
        )

        result = conn.execute(query,{
                    "user_id" : user_id
                })
        data = result.fetchone()
        if data is None:
            return None

        return dict(data._mapping)


def get_application_info_from_db(user_id):
    with engine.connect() as conn:
        # Explicitly name the columns instead of using j.* and a.*
        query = text(
            "SELECT j.job_id, j.title, j.company, a.status, a.applied_on "
            "FROM jobs AS j "
            "JOIN applications AS a ON j.job_id = a.job_id "
            "WHERE a.user_id = :user_id"
        )

        result = conn.execute(query, {
            "user_id" : user_id
        })

        # Fetch the results into a variable first
        rows = result.fetchall()

        data = []
        for row in rows:
            data.append(dict(row._mapping))

        return data


def had_user_applied(user_id, job_id):
    with engine.connect() as conn:
        query = text(
            "Select 1 from applications where user_id = :user_id and job_id = :job_id limit 1"
        )

        result = conn.execute(query,{
            "user_id" : user_id,
            "job_id" : job_id
        })

        return result.first() is not None


def update_user_profile(user_id, data):
    with engine.connect() as conn:
        query = text("update users " \
        "set name = :name, email = :email, linkedin_url = :linkedin_url," \
        "education = :education, work_experience = :work_experience, resume_url = :resume_url" \
        " where user_id = :user_id")

        conn.execute(query,{
            "user_id" : user_id,
            "name" : data['full_name'],
            "email" : data['email'],
            "linkedin_url" : data['linkedin_url'],
            "education" : data['education'],
            "work_experience" : data['work_experience'],
            "resume_url" : data['resume_url']
        })

        conn.commit()


def search_jobs_from_db(query):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM jobs WHERE title LIKE :q OR company LIKE :q OR location LIKE :q"),
            {"q": f"%{query}%"}
        )

        jobs = []
        for row in result.all():
            jobs.append(dict(row._mapping))

        return jobs


def update_user_password(email, password):
    with engine.connect() as conn:
        query = text(
            "UPDATE users SET password = :password WHERE email = :email"
        )
        conn.execute(query, {
            "email": email,
            "password": password.decode("utf-8") if isinstance(password, bytes) else password
        })
        conn.commit()


