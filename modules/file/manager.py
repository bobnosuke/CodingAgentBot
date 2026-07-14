"""
File management for CoderAgent
Handles file storage, retrieval, and compression
"""
import os
import zipfile
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from logger import setup_logger
from config import Config

logger = setup_logger(__name__)


class FileManager:
    """Manages file storage and retrieval for coding sessions"""
    
    def __init__(self, base_storage_dir: Path = None):
        """
        Initialize file manager
        
        Args:
            base_storage_dir: Base directory for file storage
        """
        self.base_storage_dir = base_storage_dir or Config.STORAGE_DIR
        self.base_storage_dir.mkdir(exist_ok=True)
    
    def create_session_directory(self, session_uuid: str) -> Path:
        """
        Create a directory for a session
        
        Args:
            session_uuid: Session UUID
        
        Returns:
            Path to session directory
        """
        session_dir = self.base_storage_dir / session_uuid
        session_dir.mkdir(exist_ok=True)
        
        logger.info(f"Created session directory: {session_dir}")
        return session_dir
    
    def save_file(self, session_uuid: str, filename: str, content: str) -> Path:
        """
        Save a file to session directory
        
        Args:
            session_uuid: Session UUID
            filename: Name of the file
            content: File content
        
        Returns:
            Path to saved file
        """
        try:
            session_dir = self.create_session_directory(session_uuid)
            file_path = session_dir / filename
            
            # Ensure filename is safe
            if ".." in filename or filename.startswith("/"):
                raise ValueError(f"Invalid filename: {filename}")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"Saved file: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise
    
    def get_file(self, session_uuid: str, filename: str) -> Optional[str]:
        """
        Retrieve a file from session directory
        
        Args:
            session_uuid: Session UUID
            filename: Name of the file
        
        Returns:
            File content or None if not found
        """
        try:
            session_dir = self.base_storage_dir / session_uuid
            file_path = session_dir / filename
            
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            return content
        
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise
    
    def list_files(self, session_uuid: str) -> List[str]:
        """
        List all files in a session directory
        
        Args:
            session_uuid: Session UUID
        
        Returns:
            List of filenames
        """
        try:
            session_dir = self.base_storage_dir / session_uuid
            
            if not session_dir.exists():
                return []
            
            files = [f.name for f in session_dir.iterdir() if f.is_file()]
            return sorted(files)
        
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def create_zip(self, session_uuid: str, zip_filename: str = None) -> Path:
        """
        Create a ZIP file of all session files
        
        Args:
            session_uuid: Session UUID
            zip_filename: Name of the ZIP file (default: session_uuid.zip)
        
        Returns:
            Path to created ZIP file
        """
        try:
            session_dir = self.base_storage_dir / session_uuid
            
            if not session_dir.exists():
                raise FileNotFoundError(f"Session directory not found: {session_dir}")
            
            zip_filename = zip_filename or f"{session_uuid}.zip"
            zip_path = self.base_storage_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in session_dir.iterdir():
                    if file_path.is_file():
                        arcname = file_path.name
                        zipf.write(file_path, arcname=arcname)
            
            logger.info(f"Created ZIP file: {zip_path}")
            return zip_path
        
        except Exception as e:
            logger.error(f"Error creating ZIP: {e}")
            raise
    
    def save_metadata(self, session_uuid: str, metadata: Dict) -> Path:
        """
        Save session metadata
        
        Args:
            session_uuid: Session UUID
            metadata: Metadata dictionary
        
        Returns:
            Path to metadata file
        """
        try:
            session_dir = self.create_session_directory(session_uuid)
            metadata_path = session_dir / "metadata.json"
            
            # Add timestamp
            metadata["saved_at"] = datetime.utcnow().isoformat()
            
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved metadata: {metadata_path}")
            return metadata_path
        
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            raise
    
    def get_metadata(self, session_uuid: str) -> Optional[Dict]:
        """
        Retrieve session metadata
        
        Args:
            session_uuid: Session UUID
        
        Returns:
            Metadata dictionary or None if not found
        """
        try:
            session_dir = self.base_storage_dir / session_uuid
            metadata_path = session_dir / "metadata.json"
            
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            return metadata
        
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return None
    
    def cleanup_session(self, session_uuid: str) -> None:
        """
        Clean up session directory
        
        Args:
            session_uuid: Session UUID
        """
        try:
            session_dir = self.base_storage_dir / session_uuid
            
            if session_dir.exists():
                import shutil
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up session directory: {session_dir}")
        
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")
    
    def get_session_size(self, session_uuid: str) -> int:
        """
        Get total size of session files in bytes
        
        Args:
            session_uuid: Session UUID
        
        Returns:
            Total size in bytes
        """
        try:
            session_dir = self.base_storage_dir / session_uuid
            
            if not session_dir.exists():
                return 0
            
            total_size = 0
            for file_path in session_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size
        
        except Exception as e:
            logger.error(f"Error calculating session size: {e}")
            return 0
