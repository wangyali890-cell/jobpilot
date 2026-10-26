"""岗位表的参数化 SQL 操作。"""

from __future__ import annotations

from datetime import date

from jobpilot.domain.models import Job, JobFilters, JobValues

from .db import Database


COLUMNS = (
    "company",
    "job_title",
    "job_type",
    "city",
    "job_url",
    "status",
    "applied_at",
    "deadline",
    "next_action",
    "next_action_date",
    "notes",
)


def _params(values: JobValues) -> tuple[object, ...]:
    return tuple(
        value.isoformat() if isinstance(value, date) else value
        for value in (getattr(values, name) for name in COLUMNS)
    )


def _job(row) -> Job:
    data = dict(row)
    for field in ("applied_at", "deadline", "next_action_date"):
        if data[field]:
            data[field] = date.fromisoformat(data[field])
    return Job(**data)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class JobRepository:
    def __init__(self, database: Database):
        self.database = database

    def get(self, job_id: int) -> Job | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _job(row) if row else None

    def get_by_url(self, url: str) -> Job | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_url = ?", (url,)).fetchone()
        return _job(row) if row else None

    def create(self, values: JobValues, timestamp: str) -> Job:
        placeholders = ", ".join("?" for _ in COLUMNS)
        columns = ", ".join((*COLUMNS, "created_at", "updated_at"))
        with self.database.connection() as connection:
            with connection:
                cursor = connection.execute(
                    f"INSERT INTO jobs ({columns}) VALUES ({placeholders}, ?, ?)",
                    (*_params(values), timestamp, timestamp),
                )
                job_id = cursor.lastrowid
        job = self.get(job_id)
        assert job is not None
        return job

    def update(self, job_id: int, values: JobValues, timestamp: str) -> Job | None:
        assignments = ", ".join(f"{column} = ?" for column in COLUMNS)
        with self.database.connection() as connection:
            with connection:
                cursor = connection.execute(
                    f"UPDATE jobs SET {assignments}, updated_at = ? WHERE id = ?",
                    (*_params(values), timestamp, job_id),
                )
                changed = cursor.rowcount
        return self.get(job_id) if changed else None

    def delete(self, job_id: int) -> bool:
        with self.database.connection() as connection:
            with connection:
                cursor = connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                return cursor.rowcount > 0

    def list(self, filters: JobFilters | None = None) -> list[Job]:
        filters = filters or JobFilters()
        clauses: list[str] = []
        params: list[object] = []
        query = filters.query.strip()
        if query:
            pattern = f"%{_escape_like(query)}%"
            clauses.append(
                "(company LIKE ? ESCAPE '\\' OR job_title LIKE ? ESCAPE '\\' "
                "OR coalesce(city, '') LIKE ? ESCAPE '\\')"
            )
            params.extend((pattern, pattern, pattern))
        if filters.status:
            clauses.append("status = ?")
            params.append(filters.status)
        if filters.job_type:
            clauses.append("job_type = ?")
            params.append(filters.job_type)
        if filters.city:
            clauses.append("city = ?")
            params.append(filters.city)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM jobs{where} ORDER BY updated_at DESC, id DESC"
        with self.database.connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [_job(row) for row in rows]
