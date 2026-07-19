import re
from typing import Dict, Any, Optional
from logger import setup_logger

logger = setup_logger(__name__)

class Verifier:
    def __init__(self):
        pass

    def verify_docker_output(self, exit_code: int, stdout: str, stderr: str) -> Dict[str, Any]:
        if exit_code == 0:
            return {"success": True, "message": "Execution successful."}
        
        error_info = {"success": False}
        
        # Try to parse Python traceback
        traceback_pattern = re.compile(
            r"File \"(?P<file>.+)\", line (?P<line>\d+)\n(?P<error_type>\w+): (?P<message>.+)"
        )
        match = traceback_pattern.search(stderr)
        
        if match:
            error_info["error_type"] = match.group("error_type")
            error_info["file"] = match.group("file")
            error_info["line"] = int(match.group("line"))
            error_info["message"] = match.group("message")
        else:
            # Fallback for other errors or if traceback parsing fails
            error_info["error_type"] = "UnknownError"
            error_info["message"] = stderr.strip() if stderr else "Execution failed with non-zero exit code."
            
        return error_info
