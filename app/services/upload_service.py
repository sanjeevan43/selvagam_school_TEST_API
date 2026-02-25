import os
import uuid
from fastapi import UploadFile
from app.core.config import get_settings

settings = get_settings()

class UploadService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.base_url = settings.BASE_URL

    async def save_file(self, file: UploadFile, sub_dir: str, custom_filename: str = None) -> str:
        """
        Save an uploaded file to a subdirectory and return the public URL.
        """
        # Ensure sub-directory exists
        target_dir = os.path.join(self.upload_dir, sub_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # Generate filename if not provided
        if custom_filename:
            extension = os.path.splitext(file.filename)[1]
            filename = f"{custom_filename}{extension}"
        else:
            filename = f"{uuid.uuid4()}_{file.filename}"

        file_path = os.path.join(target_dir, filename)
        
        # Read and save content
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Construct public URL
        # For Windows compatibility we replace \ with /
        relative_path = os.path.join(sub_dir, filename).replace('\\', '/')
        return f"{self.base_url}/uploads/{relative_path}"

    def delete_file(self, file_url: str):
        """
        Delete a file given its public URL.
        """
        if not file_url:
            return
            
        try:
            # Extract relative path from URL
            search_str = "/uploads/"
            if search_str in file_url:
                relative_path = file_url.split(search_str)[1]
                file_path = os.path.join(self.upload_dir, relative_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_url}: {e}")

upload_service = UploadService()
