import os
import json
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
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
        """Saves a list of files to the project's main directory, creating a backup."""
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
        """Retrieves project information by ID."""
        project_path = self._get_project_dir(user_id, project_id)
        metadata_path = os.path.join(project_path, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
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
            project_info["updated_at"] = datetime.now().isoformat()
            info_file_path = os.path.join(self._get_project_dir(user_id, project_id), "metadata.json")
            with open(info_file_path, "w", encoding="utf-8") as f:
                json.dump(project_info, f, indent=4)
            logger.info(f"Project renamed: user_id={user_id}, project_id={project_id}, new_name={new_name}")
            return project_info
        return None

    async def delete_project(self, user_id: int, project_id: str) -> bool:
        """Deletes a project and all its contents."""
        project_path = self._get_project_dir(user_id, project_id)
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
            logger.info(f"Project deleted: user_id={user_id}, project_id={project_id}")
            return True
        return False

    async def cleanup_old_projects(self):
        """Deletes projects older than a configured number of days."""
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
                info_file_path = os.path.join(project_path, "metadata.json")

                if os.path.exists(info_file_path):
                    with open(info_file_path, "r", encoding="utf-8") as f:
                        project_info = json.load(f)
                    
                    project_updated_at = datetime.fromisoformat(project_info["updated_at"])

                    if project_updated_at < cutoff_date:
                        logger.info(f"Deleting old project {project_id} for user {user_id_str} (last updated: {project_updated_at})")
                        try:
                            shutil.rmtree(project_path)
                        except Exception as e:
                            logger.error(f"Error deleting project directory {project_path}: {e}", exc_info=True)
                else:
                    # If metadata.json is missing, consider deleting the directory if it's old
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
            info_file_path = os.path.join(project_path, "metadata.json")
            if os.path.exists(info_file_path):
                with open(info_file_path, "r", encoding="utf-8") as f:
                    project_info = json.load(f)
                if project_info.get("db_session_id") == db_session_id:
                    return project_info
        return None

    async def get_project_main_path(self, user_id: int, project_id: str) -> Optional[str]:
        project_path = self._get_project_dir(user_id, project_id)
        main_path = os.path.join(project_path, "main")
        if os.path.exists(main_path):
            return main_path
        return None

    async def zip_project_files(self, source_dir: str, output_zip: str):
        shutil.make_archive(os.path.splitext(output_zip)[0], 'zip', source_dir)

    async def get_file_content(self, user_id: int, project_id: str, file_path: str) -> Optional[str]:
        project_main_path = await self.get_project_main_path(user_id, project_id)
        if not project_main_path:
            return None
        full_file_path = os.path.join(project_main_path, file_path)
        if os.path.exists(full_file_path) and os.path.isfile(full_file_path):
            with open(full_file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    async def get_file_context(self, user_id: int, project_id: str, file_path: str, line: int, range_lines: int) -> Optional[str]:
        content = await self.get_file_content(user_id, project_id, file_path)
        if not content:
            return None
        
        lines = content.splitlines()
        start_line = max(0, line - 1 - range_lines // 2)
        end_line = min(len(lines), line - 1 + range_lines // 2 + 1)
        
        context_lines = []
        for i in range(start_line, end_line):
            context_lines.append(f"{i+1}: {lines[i]}")
        
        return "\n".join(context_lines)

    async def apply_patch(self, user_id: int, project_id: str, file_path: str, patch_content: str) -> bool:
        project_main_path = await self.get_project_main_path(user_id, project_id)
        if not project_main_path:
            return False
        full_file_path = os.path.join(project_main_path, file_path)
        
        if not os.path.exists(full_file_path) or not os.path.isfile(full_file_path):
            logger.error(f"File not found for patching: {full_file_path}")
            return False

        try:
            with open(full_file_path, "r", encoding="utf-8") as f:
                original_content = f.read()
            
            # Simple patch application (line-by-line diff format)
            # This is a very basic implementation and might need a more robust diff/patch library
            original_lines = original_content.splitlines(keepends=True)
            patch_lines = patch_content.splitlines(keepends=True)
            
            new_lines = []
            original_idx = 0
            patch_idx = 0

            while patch_idx < len(patch_lines):
                patch_line = patch_lines[patch_idx]
                if patch_line.startswith("-"):
                    # Line to be removed
                    if original_idx < len(original_lines) and original_lines[original_idx].strip() == patch_line[1:].strip():
                        original_idx += 1
                    else:
                        logger.warning(f"Patch mismatch: Line to remove not found in original. {patch_line.strip()}")
                        return False # Mismatch, abort patch
                elif patch_line.startswith("+"):
                    # Line to be added
                    new_lines.append(patch_line[1:])
                else:
                    # Context line or unchanged line
                    if original_idx < len(original_lines) and original_lines[original_idx].strip() == patch_line.strip():
                        new_lines.append(original_lines[original_idx])
                        original_idx += 1
                    else:
                        logger.warning(f"Patch mismatch: Context line not found in original. {patch_line.strip()}")
                        return False # Mismatch, abort patch
                patch_idx += 1
            
            # Add remaining original lines if any
            while original_idx < len(original_lines):
                new_lines.append(original_lines[original_idx])
                original_idx += 1

            with open(full_file_path, "w", encoding="utf-8") as f:
                f.write("".join(new_lines))
            
            logger.info(f"Patch applied to {file_path} for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error applying patch to {file_path}: {e}", exc_info=True)
            return False

