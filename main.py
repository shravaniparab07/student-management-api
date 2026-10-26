from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, EmailStr, Field

from database import create_table, get_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_table()
    yield

app = FastAPI(title="Student Management API", description="CRUD REST API using FastAPI and SQLite.", version="1.0.0", lifespan=lifespan)

class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=250)
    enrollment_date: Optional[date] = None

class StudentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=250)
    enrollment_date: Optional[date] = None

def row_to_dict(row):
    return dict(row) if row is not None else None

def normalize_dates(data):
    for field in ("date_of_birth", "enrollment_date"):
        if field in data and data[field] is not None:
            data[field] = data[field].isoformat()
    return data

@app.get("/", tags=["Health"])
def home():
    return {"message": "Student Management API is running!", "docs": "/docs"}

@app.post("/students", status_code=status.HTTP_201_CREATED, tags=["Students"])
def create_student(student: StudentCreate):
    data = normalize_dates(student.model_dump())
    data["name"] = data["name"].strip()
    connection = get_connection()
    try:
        cursor = connection.execute("""INSERT INTO students
            (name, date_of_birth, email, phone, course, address, enrollment_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (data["name"], data["date_of_birth"], data["email"], data["phone"], data["course"], data["address"], data["enrollment_date"]))
        connection.commit()
        return row_to_dict(connection.execute("SELECT * FROM students WHERE id = ?", (cursor.lastrowid,)).fetchone())
    except Exception as exc:
        connection.rollback()
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=409, detail="A student with this email already exists")
        raise
    finally:
        connection.close()

@app.get("/students", tags=["Students"])
def list_students(name: Optional[str] = Query(default=None), course: Optional[str] = Query(default=None), limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)):
    sql = "SELECT * FROM students WHERE 1=1"
    params = []
    if name:
        sql += " AND name LIKE ?"; params.append(f"%{name}%")
    if course:
        sql += " AND course LIKE ?"; params.append(f"%{course}%")
    sql += " ORDER BY id LIMIT ? OFFSET ?"; params.extend([limit, offset])
    connection = get_connection()
    try:
        return [row_to_dict(row) for row in connection.execute(sql, params).fetchall()]
    finally:
        connection.close()

@app.get("/students/{student_id}", tags=["Students"])
def get_student(student_id: int):
    connection = get_connection()
    try:
        row = connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if row is None: raise HTTPException(status_code=404, detail="Student not found")
        return row_to_dict(row)
    finally:
        connection.close()

@app.put("/students/{student_id}", tags=["Students"])
def update_student(student_id: int, student: StudentUpdate):
    data = normalize_dates(student.model_dump(exclude_unset=True))
    if not data: raise HTTPException(status_code=400, detail="Provide at least one field to update")
    if "name" in data and data["name"] is not None: data["name"] = data["name"].strip()
    allowed = {"name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date"}
    columns = [key for key in data if key in allowed]
    connection = get_connection()
    try:
        if connection.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Student not found")
        assignments = ", ".join(f"{column} = ?" for column in columns)
        connection.execute(f"UPDATE students SET {assignments} WHERE id = ?", [data[c] for c in columns] + [student_id])
        connection.commit()
        return row_to_dict(connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone())
    except Exception as exc:
        connection.rollback()
        if "UNIQUE constraint failed" in str(exc): raise HTTPException(status_code=409, detail="A student with this email already exists")
        raise
    finally:
        connection.close()

@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Students"])
def delete_student(student_id: int):
    connection = get_connection()
    try:
        cursor = connection.execute("DELETE FROM students WHERE id = ?", (student_id,))
        if cursor.rowcount == 0: raise HTTPException(status_code=404, detail="Student not found")
        connection.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    finally:
        connection.close()

@app.get("/ai/ask", tags=["Optional AI"])
def ask_about_students(question: str = Query(min_length=3, max_length=500)):
    """Optional Ollama endpoint; records are fetched by Python, never by model-generated SQL."""
    import json, os, urllib.request
    model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    connection = get_connection()
    try:
        records = [dict(row) for row in connection.execute("SELECT id, name, date_of_birth, email, phone, course, enrollment_date FROM students ORDER BY id LIMIT 500").fetchall()]
    finally:
        connection.close()
    prompt = ("Answer only using these student records. If the records do not answer the question, say so. Do not invent data and do not execute or generate SQL.\nRecords: " + json.dumps(records) + "\nQuestion: " + question + "\nAnswer:")
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response: result = json.loads(response.read().decode())
        return {"question": question, "answer": result.get("response", "").strip(), "model": model}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable. Start Ollama and pull '{model}'. Details: {exc}")
