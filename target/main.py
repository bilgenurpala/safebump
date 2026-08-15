from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from database import get_connection, initialize_database


def task_from_row(row):
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@asynccontextmanager
async def lifespan(application: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="FlyRank BE-02", lifespan=lifespan)


def invalid_title_response():
    return JSONResponse(
        status_code=400,
        content={"error": "Title is required"},
    )


async def read_json_body(request: Request):
    try:
        body = await request.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


@app.get("/tasks")
def list_tasks():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, done FROM tasks ORDER BY id"
        ).fetchall()
    return [task_from_row(row) for row in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return task_from_row(row)


@app.post("/tasks", status_code=201)
async def create_task(request: Request):
    body = await read_json_body(request)
    title = body.get("title") if body is not None else None
    if not isinstance(title, str) or not title.strip():
        return invalid_title_response()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            (title.strip(), 0),
        )
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return task_from_row(row)


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, request: Request):
    body = await read_json_body(request)
    title = body.get("title") if body is not None else None
    done = body.get("done") if body is not None else None
    if not isinstance(title, str) or not title.strip() or not isinstance(done, bool):
        return JSONResponse(
            status_code=400,
            content={"error": "Valid title and done values are required"},
        )
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (title.strip(), int(done), task_id),
        )
        if cursor.rowcount == 0:
            return JSONResponse(
                status_code=404,
                content={"error": "Task not found"},
            )
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
    return task_from_row(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )
    if cursor.rowcount == 0:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return Response(status_code=204)

