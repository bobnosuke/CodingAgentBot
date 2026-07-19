import os
import json
from typing import List, Dict, Any, Optional
from config import Config
from logger import setup_logger

logger = setup_logger(__name__)




class WorkspaceManager:
    """Manages user workspaces and their files."""

    def __init__(self):
        self.base_dir = Config.STORAGE_DIR

    def _get_user_projects_dir(self, user_id: int) -> str:
        """Returns the base directory for a user's projects."""
        return os.path.join(self.base_dir, "users", str(user_id), "projects")

    def _get_project_dir(self, user_id: int, project_id: str) -> str:
        """Returns the directory for a specific project."""
        return os.path.join(self._get_user_projects_dir(user_id), project_id)

    async def create_project(self, user_id: int, project_name: str, db_session_id: int) -> Dict[str, Any]:
        """Creates a new project for the user."""
        projects_dir = self._get_user_projects_dir(user_id)
        os.makedirs(projects_dir, exist_ok=True)

        # Generate a unique project ID (e.g., timestamp or UUID)
        project_id = str(int(os.times().elapsed * 1000))
        project_path = self._get_project_dir(user_id, project_id)
        os.makedirs(project_path, exist_ok=True)

        project_info = {
            "id": project_id,
            "name": project_name,
            "created_at": os.times().elapsed,
            "updated_at": os.times().elapsed,
            "files_dir": os.path.join(project_path, "files"),
            "db_session_id": db_session_id
        }
        os.makedirs(project_info["files_dir"], exist_ok=True)

        info_file_path = os.path.join(project_path, "project_info.json")
        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(project_info, f, indent=4)
        
        logger.info(f"Project created: user_id={user_id}, project_id={project_id}, name={project_name}")
        return project_info

    async def get_project(self, user_id: int, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves project information by ID."""
        project_path = self._get_project_dir(user_id, project_id)
        info_file_path = os.path.join(project_path, "project_info.json")
        
        if os.path.exists(info_file_path):
            with open(info_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    async def list_projects(self, user_id: int) -> List[Dict[str, Any]]:
        """Lists all projects for a given user."""
        projects_dir = self._get_user_projects_dir(user_id)
        if not os.path.exists(projects_dir):
            return []

        projects = []
        for project_id in os.listdir(projects_dir):
            project_info = await self.get_project(user_id, project_id)
            if project_info:
                projects.append(project_info)
        return projects

    async def rename_project(self, user_id: int, project_id: str, new_name: str) -> Optional[Dict[str, Any]]:
        """Renames a project."""
        project_info = await self.get_project(user_id, project_id)
        if project_info:
            project_info["name"] = new_name
            project_info["updated_at"] = os.times().elapsed
            info_file_path = os.path.join(self._get_project_dir(user_id, project_id), "project_info.json")
            with open(info_file_path, "w", encoding="utf-8") as f:
                json.dump(project_info, f, indent=4)
            logger.info(f"Project renamed: user_id={user_id}, project_id={project_id}, new_name={new_name}")
            return project_info
        return None

    async def delete_project(self, user_id: int, project_id: str) -> bool:
        """Deletes a project and all its contents."""
        project_path = self._get_project_dir(user_id, project_id)
        if os.path.exists(project_path):
            import shutil
            shutil.rmtree(project_path)
            logger.info(f"Project deleted: user_id={user_id}, project_id={project_id}")
            return True
        return False

    async def cleanup_old_projects(self):
        """Deletes projects older than a configured number of days."""
        from datetime import datetime, timedelta
        from config import Config
        import shutil

        logger.info("Starting old project cleanup...")
        cutoff_date = datetime.utcnow() - timedelta(days=Config.SESSION_CACHE_CLEANUP_DAYS)

        users_dir = os.path.join(self.base_dir, "users")
        if not os.path.exists(users_dir):
            logger.info("No user directories found for cleanup.")
            return

        for user_id_str in os.listdir(users_dir):
            user_projects_dir = self._get_user_projects_dir(int(user_id_str))
            if not os.path.exists(user_projects_dir):
                continue

            for project_id in os.listdir(user_projects_dir):
                project_path = self._get_project_dir(int(user_id_str), project_id)
                info_file_path = os.path.join(project_path, "project_info.json")

                if os.path.exists(info_file_path):
                    with open(info_file_path, "r", encoding="utf-8") as f:
                        project_info = json.load(f)
                    
                    # Convert os.times().elapsed to datetime for comparison
                    # This assumes os.times().elapsed is a timestamp (seconds since epoch)
                    # If it's not, this conversion needs adjustment.
                    # For now, assuming it's a float timestamp.
                    project_updated_at = datetime.fromtimestamp(project_info["updated_at"])

                    if project_updated_at < cutoff_date:
                        logger.info(f"Deleting old project {project_id} for user {user_id_str} (last updated: {project_updated_at})")
                        try:
                            shutil.rmtree(project_path)
                        except Exception as e:
                            logger.error(f"Error deleting project directory {project_path}: {e}", exc_info=True)
                else:
                    # If project_info.json is missing, consider deleting the directory if it's old
                    # This is a fallback for potentially corrupted project directories
                    try:
                        dir_mtime = datetime.fromtimestamp(os.path.getmtime(project_path))
                        if dir_mtime < cutoff_date:
                            logger.warning(f"Deleting project directory {project_path} with missing info file (last modified: {dir_mtime})")
                            shutil.rmtree(project_path)
                    except Exception as e:
                        logger.error(f"Error deleting potentially corrupted project directory {project_path}: {e}", exc_info=True)
        logger.info("Old project cleanup finished.")

    async def get_project_by_session_id(self, user_id: int, db_session_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves project information by associated database session ID."""
        projects_dir = self._get_user_projects_dir(user_id)
        if not os.path.exists(projects_dir):
            return None

        for project_id in os.listdir(projects_dir):
            project_path = self._get_project_dir(user_id, project_id)
            info_file_path = os.path.join(project_path, "project_info.json")
            if os.path.exists(info_file_path):
                with open(info_file_path, "r", encoding="utf-8") as f:
                    project_info = json.load(f)
                # Assuming project_info.json stores the db_session_id
                # This needs to be added when creating a project
                if project_info.get("db_session_id") == db_session_id:
                    return project_info
        return None
