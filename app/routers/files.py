from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.agent.utils.storage_utils import upload_image_to_gs
import uuid
from pathlib import Path

from app.deps import get_session_id

router = APIRouter()

MOUNT_PATH = "/mnt/storage"

FOLDER_PATH = "codebase"


class TestWriteFileResponse(BaseModel):
    message: str
    file_path: str


class TestWriteFileRequest(BaseModel):
    file_name: str
    content: str


@router.post("/test-write-file", response_model=TestWriteFileResponse)
async def test_write_file(request: TestWriteFileRequest):
    try:
        file_path = Path(MOUNT_PATH) / FOLDER_PATH / request.file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(request.content, encoding="utf-8")
        print(f"Wrote file at {file_path}")
        return TestWriteFileResponse(
            message="File written successfully", file_path=str(file_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list-directory")
async def list_directory(session_id: str = Depends(get_session_id)):
    try:
        dir_path = Path(MOUNT_PATH) / FOLDER_PATH / session_id
        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")
        files = [
            str(p.relative_to(dir_path)) for p in dir_path.rglob("*") if p.is_file()
        ]
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read-file")
async def read_file(file_path: str, session_id: str = Depends(get_session_id)):
    try:
        full_path = Path(MOUNT_PATH) / FOLDER_PATH / session_id / file_path
        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        content = full_path.read_text(encoding="utf-8")
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-files")
async def get_files(session_id: str = Depends(get_session_id)):
    try:
        dir_path = Path(MOUNT_PATH) / FOLDER_PATH / session_id
        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")
        files = {}
        for p in dir_path.rglob("*"):
            if p.is_file():
                relative_path = str(p.relative_to(dir_path))
                try:
                    content = p.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = p.read_bytes().decode("utf-8", errors="replace")
                files[relative_path] = content
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
