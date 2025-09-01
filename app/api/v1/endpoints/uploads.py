import os
from typing import Any, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.api import deps
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_file(
    *,
    file: UploadFile = File(...),
    folder: str = "general",
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Upload a file to the server
    """
    # Check file size
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حجم فایل بیش از حد مجاز است",  # File size exceeds the limit
        )
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نوع فایل مجاز نیست",  # File type not allowed
        )
    
    # Sanitize folder name to prevent directory traversal
    safe_folder = folder.replace("..", "").replace("/", "").replace("\\", "")
    
    # Create uploads directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOADS_DIR, safe_folder)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate a safe filename
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Return the file path relative to the uploads directory
    relative_path = f"/uploads/{safe_folder}/{safe_filename}"
    
    return {"filename": file.filename, "path": relative_path}


@router.get("/files", response_model=List[dict])
async def list_files(
    *,
    folder: str = "general",
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    List all files in a specific folder
    """
    # Sanitize folder name to prevent directory traversal
    safe_folder = folder.replace("..", "").replace("/", "").replace("\\", "")
    
    # Get the folder path
    folder_path = os.path.join(settings.UPLOADS_DIR, safe_folder)
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        return []
    
    # List all files in the folder
    files = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            file_stat = os.stat(file_path)
            files.append({
                "filename": filename,
                "path": f"/uploads/{safe_folder}/{filename}",
                "size": file_stat.st_size,
                "created_at": file_stat.st_ctime
            })
    
    return files


@router.get("/{folder}/{filename}")
async def get_file(
    *,
    folder: str,
    filename: str,
) -> Any:
    """
    Get a file by folder and filename
    """
    # Sanitize folder and filename to prevent directory traversal
    safe_folder = folder.replace("..", "").replace("/", "").replace("\\", "")
    safe_filename = filename.replace("..", "").replace("/", "").replace("\\", "")
    
    # Get the file path
    file_path = os.path.join(settings.UPLOADS_DIR, safe_folder, safe_filename)
    
    # Check if file exists
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فایل یافت نشد",  # File not found
        )
    
    # Return the file
    return FileResponse(file_path)


@router.delete("/{folder}/{filename}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_file(
    *,
    folder: str,
    filename: str,
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Delete a file by folder and filename (admin only)
    """
    # Sanitize folder and filename to prevent directory traversal
    safe_folder = folder.replace("..", "").replace("/", "").replace("\\", "")
    safe_filename = filename.replace("..", "").replace("/", "").replace("\\", "")
    
    # Get the file path
    file_path = os.path.join(settings.UPLOADS_DIR, safe_folder, safe_filename)
    
    # Check if file exists
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فایل یافت نشد",  # File not found
        )
    
    # Delete the file
    os.remove(file_path)