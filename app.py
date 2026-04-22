from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import sys
import shutil
import asyncio
from fastapi import WebSocket
import json
import webbrowser
from scraper import run_main
from pydantic import BaseModel

app = FastAPI()
from fastapi.responses import FileResponse

@app.get("/download/csv")
def download_csv():
    path = os.path.abspath("outputs/output.csv")

    if not os.path.exists(path):
        return {"error": "CSV not started yet"}

    return FileResponse(path, filename="output.csv")

@app.get("/download/json")
def download_json():
    path = os.path.abspath("outputs/output.json")

    if not os.path.exists(path):
        return {"error": "JSON not ready yet"}

    return FileResponse(path, filename="output.json")
progress = {
    "total": 0,
    "processed": 0,
    "success": 0,
    "failed": 0
}

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except:
        clients.remove(websocket)

logs = []

# Serve static files
app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")


@app.get("/", response_class=HTMLResponse)
def home():
    with open(resource_path("templates/index.html"), "r", encoding="utf-8") as f:
        return f.read()


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"status": "uploaded", "file": file_path}


@app.get("/logs")
def get_logs():
    return {"logs": logs}

async def broadcast(message: str):
    for client in clients:
        try:
            await client.send_text(message)
        except:
            pass

# 🔥 background scraping
async def run_scraper(file_path, workers, tabs):
    

    async def log_callback(msg):
        logs.append(msg)
        await broadcast(msg)

    async for event in run_main(file_path, workers, tabs, log_callback):
        # event = {type: log/progress/done, data: ...}

        if event["type"] == "log":
            logs.append(event["data"]) 
            await broadcast(event["data"])

        elif event["type"] == "progress":
            progress.update(event["data"])
            await broadcast(f"PROGRESS::{json.dumps(progress)}")

        elif event["type"] == "done":
            await broadcast("DONE")

class StartRequest(BaseModel):
    file_path: str
    workers: int
    tabs: int


@app.post("/start")
async def start_scraping(req: StartRequest):
    global logs, progress

    logs = []  # reset
    progress = {
        "total": 0,
        "processed": 0,
        "success": 0,
        "failed": 0
    }

    asyncio.create_task(
        run_scraper(req.file_path, req.workers, req.tabs)
    )
    return {"status": "started"}

if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)