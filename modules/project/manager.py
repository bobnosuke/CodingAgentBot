import os
import json
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import Config
from logger import setup_logger

logger = setup_logger(__name__)

class ProjectManager:
    """Manages user projects with backup structure: main/, backup/, logs/, metadata.json"""

    def __init__(self):
        self.base_dir = Config.STORAGE_DIR

    def _get_user_projects_dir(self, user_id: int) -> str:
        return os.path.join(self.base_dir, "users", str(user_id), "projects")

    def _get_project_dir(self, user_id: int, project_id: str) -> str:
        return os.path.join(self._get_user_projects_dir(user_id), project_id)

    async def create_project(self, user_id: int, project_name: str, db_session_id: int) -> Dict[str, Any]:
        projects_dir = self._get_user_projects_dir(user_id)
        os.makedirs(projects_dir, exist_ok=True)

        import uuid
        project_id = str(uuid.uuid4())
        project_path = self._get_project_dir(user_id, project_id)
        os.makedirs(project_path, exist_ok=True)

        # Create new structure
        os.makedirs(os.path.join(project_path, "main"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "backup"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "logs"), exist_ok=True)

        project_info = {
            "id": project_id,
            "name": project_name,
            "user_id": user_id,
            "db_session_id": db_session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 0
        }
        
        info_file_path = os.path.join(project_path, "metadata.json")
        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(project_info, f, indent=4)
        
        logger.info(f"Project created with backup structure: user_id={user_id}, project_id={project_id}")
        return project_info

    async def save_project_files(self, user_id: int, project_id: str, files: List[Dict[str, str]]):
        project_path = self._get_project_dir(user_id, project_id)
        main_dir = os.path.join(project_path, "main")
        backup_dir = os.path.join(project_path, "backup")
        metadata_path = os.path.join(project_path, "metadata.json")
        
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        version = metadata.get("version", 0)
        
        # Backup logic
        if version > 0:
            # Move current main to backup
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree(main_dir, backup_dir)
        
        # Save to main
        for file_data in files:
            file_path = os.path.join(main_dir, file_data["path"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_data["content"])
        
        # If first save, main and backup are same
        if version == 0:
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree(main_dir, backup_dir)

        # Update metadata
        metadata["version"] = version + 1
        metadata["updated_at"] = datetime.now().isoformat()
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

    async def get_project(self, user_id: int, project_id: str) -> Optional[Dict[str, Any]]:
        project_path = self._get_project_dir(user_id, project_id)
        metadata_path = os.path.join(project_path, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    async def delete_project(self, user_id: int, project_id: str) -> bool:
        project_path = self._get_project_dir(user_id, project_id)
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
            return True
        return False
