from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.agent.utils.storage_utils import upload_image_to_gs
import uuid
from pathlib import Path

router = APIRouter()

FOLDER_PATH = "assets"


class UploadResponse(BaseModel):
    url: str
    filename: str
    destination: str


@router.post("/upload-image", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image to Google Cloud Storage.

    Args:
        file: The image file to upload (supports common image formats)

    Returns:
        UploadResponse with the public URL, filename, and destination path
    """
    try:
        # Validate file type
        allowed_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/webp",
            "image/gif",
            "image/svg+xml",
            "image/tiff",
            "image/bmp",
            "image/heic",
            "image/avif",
            "image/ico",
        ]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
            )

        # Read file content
        image_content = await file.read()

        # Generate unique filename
        file_extension = Path(file.filename).suffix
        random_uuid = str(uuid.uuid4())
        destination_filename = f"{random_uuid}{file_extension}"
        destination_path = f"{FOLDER_PATH}/{destination_filename}"

        # Determine file type
        is_gif = file.content_type == "image/gif"
        is_svg = file.content_type == "image/svg+xml"

        # Upload to Google Cloud Storage
        public_url = upload_image_to_gs(
            image_content=image_content,
            destination_path=destination_path,
            is_gif=is_gif,
            is_svg=is_svg,
        )

        if not public_url:
            raise HTTPException(
                status_code=500, detail="Failed to upload image to storage"
            )

        return UploadResponse(
            url=public_url, filename=file.filename, destination=destination_path
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while uploading the image: {str(e)}",
        )
