import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException
from app.core.config import get_settings
import re

settings = get_settings()

class UploadService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.base_url = settings.BASE_URL
        self.max_file_size = 5 * 1024 * 1024  # 5MB limit

    def sanitize_filename(self, filename: str) -> str:
        """Remove dangerous characters from filename."""
        return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    async def save_file(self, file: UploadFile, sub_dir: str, custom_filename: str = None) -> str:
        """
        Save an uploaded file to a subdirectory and return the public URL.
        Uses chunked writing to save memory.
        """
        # Ensure sub-directory exists
        target_dir = os.path.join(self.upload_dir, sub_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        # Sanitize and generate filename
        original_filename = self.sanitize_filename(file.filename)
        extension = os.path.splitext(original_filename)[1].lower()
        
        if custom_filename:
            filename = f"{custom_filename}{extension}"
        else:
            filename = f"{uuid.uuid4().hex}_{original_filename}"

        file_path = os.path.join(target_dir, filename)
        
        # Save content in chunks
        size = 0
        try:
            with open(file_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    size += len(chunk)
                    if size > self.max_file_size:
                        buffer.close()
                        os.remove(file_path)
                        raise HTTPException(status_code=413, detail="File too large (max 5MB)")
                    buffer.write(chunk)
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")

        # Construct public URL
        relative_path = os.path.join(sub_dir, filename).replace('\\', '/')
        return f"{self.base_url.rstrip('/')}/uploads/{relative_path}"

    def delete_file_by_url(self, file_url: str):
        """
        Delete a file given its public URL.
        """
        if not file_url:
            return
            
        try:
            # Extract relative path from URL (after /uploads/)
            search_str = "/uploads/"
            if search_str in file_url:
                relative_path = file_url.split(search_str)[1]
                file_path = os.path.join(self.upload_dir, relative_path)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    os.remove(file_path)
        except Exception as e:
            # We don't want to crash if delete fails
            pass

upload_service = UploadService()
