import os
import shutil
import subprocess
from typing import List, Dict, Any

class AgentTools:
    def __init__(self, base_path: str):
        self.base_path = base_path

    def list_files(self, path: str = ".") -> List[str]:
        full_path = os.path.join(self.base_path, path)
        files_list = []
        for root, dirs, files in os.walk(full_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.base_path)
                files_list.append(rel_path)
        return files_list

    def read_file(self, file_path: str) -> str:
        full_path = os.path.join(self.base_path, file_path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def create_file(self, file_path: str, content: str):
        full_path = os.path.join(self.base_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def edit_file(self, file_path: str, find_text: str, replace_text: str):
        full_path = os.path.join(self.base_path, file_path)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = content.replace(find_text, replace_text)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    def delete_file(self, file_path: str):
        full_path = os.path.join(self.base_path, file_path)
        if os.path.isfile(full_path):
            os.remove(full_path)
        elif os.path.isdir(full_path):
            shutil.rmtree(full_path)

    def move_file(self, src: str, dst: str):
        full_src = os.path.join(self.base_path, src)
        full_dst = os.path.join(self.base_path, dst)
        os.makedirs(os.path.dirname(full_dst), exist_ok=True)
        shutil.move(full_src, full_dst)

    def execute_project(self, entrypoint: str) -> Dict[str, Any]:
        # This is a placeholder for actual execution, usually handled by DockerExecutor
        # but provided here as a tool for the agent.
        return {"status": "ready_for_execution", "entrypoint": entrypoint}

    def check_project_status(self) -> Dict[str, Any]:
        files = self.list_files()
        return {"file_count": len(files), "files": files}

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {"name": "list_files", "description": "List all files in the project"},
            {"name": "read_file", "description": "Read content of a specific file", "parameters": ["file_path"]},
            {"name": "create_file", "description": "Create a new file with content", "parameters": ["file_path", "content"]},
            {"name": "edit_file", "description": "Edit a file by replacing text", "parameters": ["file_path", "find_text", "replace_text"]},
            {"name": "delete_file", "description": "Delete a file or directory", "parameters": ["file_path"]},
            {"name": "move_file", "description": "Move or rename a file or directory", "parameters": ["src", "dst"]},
            {"name": "execute_project", "description": "Execute the project from entrypoint", "parameters": ["entrypoint"]},
            {"name": "check_project_status", "description": "Check current project status and file list"}
        ]
