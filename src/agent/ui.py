"""FastAPI app for the local agent."""

from __future__ import annotations

from pathlib import Path
from typing import List

import ollama
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import agent as agent_mod
from . import db
from .ingest import ingest_file
from .retrieve import get_chunk

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data"
PRIVATE = DATA / "private"
OUTPUT = BASE / "output"
DB_PATH = DATA / "index.db"

app = FastAPI(title="Nido")
app.mount("/static", StaticFiles(directory=str(BASE / "ui")), name="static")
templates = Jinja2Templates(directory=str(BASE / "src" / "agent" / "templates"))


def _conn():
    return db.init_db(DB_PATH)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    conn = _conn()
    docs = db.list_documents(conn)
    chunks = db.count_chunks(conn)
    conn.close()
    html = templates.get_template("index.html").render(
        {
            "request": request,
            "documents": docs,
            "total_chunks": chunks,
            "network_requests": 0,
        }
    )
    return HTMLResponse(html)


@app.post("/ingest", response_class=HTMLResponse)
async def ingest(files: List[UploadFile] = File(...)):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    for f in files:
        dest = PRIVATE / f.filename
        dest.write_bytes(await f.read())
        ingest_file(dest, DB_PATH)
    conn = _conn()
    docs = db.list_documents(conn)
    chunks = db.count_chunks(conn)
    conn.close()
    html = templates.get_template("partials/doc_list.html").render(
        {"documents": docs, "total_chunks": chunks}
    )
    return HTMLResponse(html)


@app.post("/ask", response_class=HTMLResponse)
async def ask(query: str = Form(...)):
    conn = _conn()
    result = agent_mod.answer_question(conn, query)
    conn.close()
    html = templates.get_template("partials/answer.html").render(
        {"result": result, "query": query}
    )
    return HTMLResponse(html)


@app.post("/draft", response_class=HTMLResponse)
async def draft(client: str = Form(...), body: str = Form(...)):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"recordatorio-{client.replace(' ', '-').lower()}.md"
    path.write_text(body, encoding="utf-8")
    html = templates.get_template("partials/draft.html").render(
        {"path": str(path), "body": body}
    )
    return HTMLResponse(html)


@app.get("/sources/{chunk_id}", response_class=HTMLResponse)
async def source(chunk_id: int):
    conn = _conn()
    chunk = get_chunk(conn, chunk_id)
    conn.close()
    html = templates.get_template("partials/source_detail.html").render(
        {"chunk": chunk}
    )
    return HTMLResponse(html)


@app.post("/delete")
async def delete():
    if DB_PATH.exists():
        DB_PATH.unlink()
    if OUTPUT.exists():
        for p in OUTPUT.iterdir():
            if p.is_file():
                p.unlink()
    return Response(status_code=204, headers={"HX-Redirect": "/"})


@app.get("/health", response_class=JSONResponse)
async def health():
    try:
        ollama.list()
        ok = True
    except Exception:
        ok = False
    conn = _conn()
    docs = db.count_documents(conn)
    chunks = db.count_chunks(conn)
    conn.close()
    return {
        "ollama_ok": ok,
        "model": "gemma4:12b-mlx",
        "documents": docs,
        "chunks": chunks,
    }
