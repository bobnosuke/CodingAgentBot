
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

    async def build_image(self, session_id: str) -> str:
        image_name = f"coderagent-exec:{session_id}"
        try:
            logger.info(f"Building Docker image {image_name}...")
            # Ensure Dockerfile.exec and requirements.txt are in the build context
            # For simplicity, assuming they are in project_root
            await asyncio.to_thread(
                self.client.images.build,
                path=self.project_root,
                dockerfile=self.dockerfile_path,
                tag=image_name,
                rm=True
            )
            logger.info(f"Successfully built Docker image {image_name}")
            return image_name
        except docker.errors.BuildError as e:
            logger.error(f"Docker image build failed: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during Docker image build: {e}")
            raise

    async def execute_code(
        self,
        session_id: str,
        files: List[Dict[str, str]],
        entrypoint_file: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        
        image_name = "coderagent-exec:latest"
        container_name = f"coderagent-container-{session_id}"
        session_dir = os.path.join(self.project_root, session_id)

        # 1. Create session directory and write files
        os.makedirs(session_dir, exist_ok=True)
        for file_data in files:
            file_path = os.path.join(session_dir, file_data["path"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_data["content"])
        logger.info(f"Wrote {len(files)} files to {session_dir}")

        # 2. Run the container
        try:
            logger.info(f"Running container {container_name} from image {image_name}...")
            container = await asyncio.to_thread(
                self.client.containers.run,
                image_name,
                command=f"python {entrypoint_file}",
                name=container_name,
                volumes={
                    os.path.abspath(session_dir): {
                        'bind': '/app',
                        'mode': 'rw'
                    }
                },
                detach=True,
                remove=True
            )

            # Wait for container to finish or timeout
            result = container.wait(timeout=timeout)
            logs = container.logs().decode('utf-8')

            exit_code = result['StatusCode']
            logger.info(f"Container {container_name} exited with code {exit_code}")
            
            return {"exit_code": exit_code, "logs": logs}

        except docker.errors.ContainerError as e:
            logs = e.container.logs().decode('utf-8')
            logger.error(f"Container error: {e}\nLogs: {logs}")
            return {"exit_code": e.exit_status, "logs": logs}
        except docker.errors.ImageNotFound:
            logger.error(f"Docker image {image_name} not found. Please build it first.")
            raise
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            raise
        except asyncio.TimeoutError:
            logger.warning(f"Container {container_name} timed out after {timeout} seconds. Killing...")
            container.kill()
            logs = container.logs().decode('utf-8')
            return {"exit_code": -1, "logs": logs + "\nExecution timed out."}
        except Exception as e:
            logger.error(f"An unexpected error occurred during code execution: {e}")
            raise
        finally:
            # 3. Clean up session directory
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up session directory {session_dir}")


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

