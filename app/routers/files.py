from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.agent.utils.storage_utils import upload_image_to_gs
import uuid
from pathlib import Path

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
