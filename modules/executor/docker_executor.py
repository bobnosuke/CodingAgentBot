import asyncio
import docker
import os
import shutil
from typing import Dict, Any, List, Optional
from logger import setup_logger

logger = setup_logger(__name__)

class DockerExecutor:
    def __init__(self, project_root: str = "./"):
        self.client = docker.from_env()
        self.project_root = project_root
        self.dockerfile_path = os.path.join(project_root, "Dockerfile.exec")
        self.requirements_path = os.path.join(project_root, "requirements.txt")
        
    def get_image_name(self, session_id):
        # Use session_id as tag to avoid conflicts and handle per-session requirements
        return f"coderagent-exec:{session_id}"
        
    def image_exists(self, session_id: str):
        image_name = self.get_image_name(session_id)
        try:
            self.client.images.get(image_name)
            return True
        except docker.errors.ImageNotFound:
            return False

    async def build_image(self, session_id: str) -> str:
        image_name = self.get_image_name(session_id)  
        try:
            logger.info(
                f"Building Docker image {image_name}..."
            )
            def build():
                return self.client.images.build(
                    path=self.project_root,
                    dockerfile=self.dockerfile_path,
                    tag=image_name,
                    rm=True
                )
            image, logs = await asyncio.to_thread(build)
            for log in logs:
                if "stream" in log:
                    print(
                        f"[Docker Build:{session_id}] "
                        f"{log['stream'].strip()}"
                    )
            logger.info(
                f"Successfully built {image_name}"
            )
            return image_name
    
        except Exception as e:
            logger.error(
                f"Build failed: {e}",
                exc_info=True
            )
            raise

    async def execute_code(
        self,
        session_id: str,
        files: List[Dict[str, str]],
        entrypoint_file: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
    
        image_name = self.get_image_name(session_id)
        container_name = f"coderagent-container-{session_id}"
        session_dir = os.path.join(self.project_root,session_id)
        os.makedirs(session_dir,exist_ok=True)
    
        # ファイル書き込み
        for file_data in files:
            file_path = os.path.join(session_dir,file_data["path"])
            directory = os.path.dirname(file_path)
    
            if directory:
                os.makedirs(directory,exist_ok=True)
            with open(file_path,"w",encoding="utf-8") as f:
                f.write(file_data["content"])
        logger.info(f"Wrote {len(files)} files to {session_dir}")
        
        container = None
        try:
            logger.info(f"Creating container {container_name}")
            container = await asyncio.to_thread(
                self.client.containers.create,
                image_name,
                command=[
                    "python",
                    entrypoint_file
                ],
                name=container_name,
                volumes={
                    os.path.abspath(session_dir):
                    {
                        "bind":"/app",
                        "mode":"rw"
                    }
                }
            )
    
            logger.info("Starting container...")
            await asyncio.to_thread(container.start)
            result = await asyncio.to_thread(container.wait,timeout=timeout)
            logs = await asyncio.to_thread(container.logs)
            logs = logs.decode("utf-8",errors="ignore")
            exit_code = result["StatusCode"]
            return {"exit_code": exit_code,"logs": logs}
        except Exception as e:
            logger.error(f"Docker execution error: {e}",exc_info=True)
            if container:
                try:
                    logs = container.logs().decode("utf-8",errors="ignore")
                except:
                    logs = str(e)
            else:
                logs = str(e)
            return {"exit_code": -1,"logs": logs}
        finally:
            if container:
                try:
                    await asyncio.to_thread(container.remove,force=True)
                except:
                    pass
            logger.info(f"Keeping project directory: {session_dir}")

# Example Usage (for testing)
async def main():
    executor = DockerExecutor()
    session_id = "test_session_123"
    
    # Build image once
    await executor.build_image(session_id)

    files_to_execute = [
        {"path": "main.py", "content": "print(\"Hello from Docker!\")"}
    ]
    result = await executor.execute_code(session_id, files_to_execute, "main.py")
    print(f"Result: {result}")

    files_with_error = [
        {"path": "main.py", "content": "import non_existent_module\nprint(\"This will fail\")"}
    ]
    result = await executor.execute_code(session_id, files_with_error, "main.py")
    print(f"Result with error: {result}")

if __name__ == "__main__":
    # This part needs to be run in an async context
    # For quick testing, you might use:
    # import nest_asyncio
    # nest_asyncio.apply()
    # asyncio.run(main())
    print("Run main() in an async context for testing.")

