from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.agent.utils.storage_utils import upload_image_to_gs, upload_csv_to_gs
import uuid
from pathlib import Path
from typing import Any

from app.deps import get_session_id

router = APIRouter()

MOUNT_PATH = "/mnt/storage"

FOLDER_PATH = ""


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


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    session_id: str = Depends(get_session_id),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    original_name = file.filename.lower()
    if not original_name.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded CSV is empty.")

    unique_name = f"{uuid.uuid4()}.csv"
    destination_path = f"datasets/{session_id}/{unique_name}"

    csv_url = upload_csv_to_gs(file_bytes, destination_path)
    if csv_url is None:
        raise HTTPException(status_code=500, detail="Failed to upload CSV to storage.")

    return {
        "url": csv_url,
        "path": destination_path,
        "original_filename": file.filename,
    }


@router.get("/list-directory")
async def list_directory(session_id: str = Depends(get_session_id)):
    try:
        dir_path = Path(MOUNT_PATH) / FOLDER_PATH / session_id
        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")
        files = [
            str(p.relative_to(dir_path))
            for p in dir_path.rglob("*")
            if p.is_file() and "node_modules" not in p.parts
        ]
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read-file")
async def read_file(file_path: str, session_id: str = Depends(get_session_id)):
    try:
        # Prevent reading files inside node_modules
        if "node_modules" in Path(file_path).parts:
            raise HTTPException(
                status_code=403, detail="Access to node_modules is forbidden"
            )
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

        def build_tree(path):
            tree = {}
            for p in path.iterdir():
                if "node_modules" in p.parts:
                    continue
                rel_name = p.name
                if p.is_dir():
                    tree[rel_name] = build_tree(p)
                elif p.is_file():
                    try:
                        content = p.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        content = p.read_bytes().decode("utf-8", errors="replace")
                    tree[rel_name] = content
            return tree

        files_tree = build_tree(dir_path)
        return {"files": files_tree}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
