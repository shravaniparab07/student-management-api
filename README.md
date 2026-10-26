# Student Management API

A Python backend project for the EWB internship assignment. It uses **FastAPI** for REST endpoints and **SQLite** for persistent storage, with an optional local AI endpoint powered by Ollama.

## Features
- Create, list, retrieve, update, and delete student records (CRUD)
- Filter by part of a student's name or course; pagination with `limit` and `offset`
- Input validation, unique email constraint, and `404` responses for missing students
- Interactive API documentation at `/docs`
- Optional Ollama Q&A grounded in records retrieved by backend code; the model does not execute SQL

## Student fields
Required: `name`, `date_of_birth` (`YYYY-MM-DD`). Optional: `email`, `phone`, `course`, `address`, `enrollment_date` (`YYYY-MM-DD`).

## Run on Windows / VS Code
Open a terminal in this folder:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` in that terminal, then activate again. If you already created `venv`, just activate it and install requirements.

Open `http://127.0.0.1:8000/docs`. The `students.db` file is created automatically beside `database.py` when the server starts.

## Test CRUD in `/docs`
Expand `POST /students`, choose **Try it out**, and submit this fictional sample:

```json
{
  "name": "Aarav Sharma",
  "date_of_birth": "2005-04-12",
  "email": "aarav.demo@example.com",
  "phone": "9000000001",
  "course": "BSc IT",
  "address": "Mumbai",
  "enrollment_date": "2026-06-01"
}
```

Then try `GET /students`, `GET /students/1` (use the ID returned by your create request), `PUT /students/1` with `{"course":"Artificial Intelligence"}`, and `DELETE /students/1`. Use a different email if repeating the create request.

Filter examples: `/students?name=Aarav`, `/students?course=BSc%20IT`, `/students?limit=20&offset=0`.

## Optional AI extension (Ollama)
The core CRUD project does not require Ollama. To use `/ai/ask`, install Ollama, ensure it is running, and download a model such as `llama3.2:1b`. Open `GET /ai/ask` in `/docs` and ask a question such as `How many students are there?`. The model receives a bounded set of records as context; it does not execute model-generated SQL. Verify answers against `GET /students`.

## Submission notes
- Use only fictional/demo records; do not upload real students' personal data.
- Do not commit secrets.
- `students.db` is generated at runtime and intentionally not included in this ZIP.
- Run and test this project locally before submitting it. Be prepared to explain the endpoints and demonstrate all four CRUD operations.
