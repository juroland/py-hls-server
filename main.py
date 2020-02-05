import os

from fastapi import FastAPI
from starlette.responses import FileResponse

app = FastAPI()

MEDIAS_DIR : str = os.environ.get("HLS_SERVER_MEDIAS_DIR", ".")

@app.get("/medias")
async def list_medias():
    medias = []
    for entry in os.scandir(MEDIAS_DIR):
        if entry.is_dir():
            medias.append({"id": int(entry.name)})
    return medias


@app.get("/medias/{media_id}/stream/")
async def read_media(media_id: int):
    filename = os.path.join(MEDIAS_DIR, str(media_id), "master.m3u8")
    return FileResponse(filename, media_type="application/x-mpegURL")


@app.get("/medias/{media_id}/stream/{segment_name}")
async def read_segment(media_id: int, segment_name: str):
    filename = os.path.join(MEDIAS_DIR, str(media_id), segment_name)
    return FileResponse(filename, media_type="video/MP2T")
