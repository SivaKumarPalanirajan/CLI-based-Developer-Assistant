from fastmcp import FastMCP 
import subprocess 
import os 
from langchain.tools import tool 
from langchain_core.messages import ToolMessage
from langgraph.types import Command 
from rich.console import Console 
from rich.syntax import Syntax

console=Console()
mcp=FastMCP('AIAssistantServer')

container_name='python-sandbox'

def write_file_to_container(container, filename, content):
    process = subprocess.Popen(
        ["docker", "exec", "-i", container, "sh", "-c", f"cat > /app/{filename}"],
        stdin=subprocess.PIPE,
        text=True
    )
    process.communicate(content)


@mcp.tool()
def save_files_in_container(files: dict):
    """
    Write the files inside the docker container before testing
    Args:
        files: a dictionary which contains filenames and content of the files as a string
    Example:
      files={"main.py":"print('Hello')"}
    """
    try:
        subprocess.run(["docker", "exec", container_name, "rm", "-rf", "/app/*"])

        for filename, content in files.items():
            write_file_to_container(container_name, filename, content)

        return "Files written successfully"
    except Exception as e: 
        return f"Couldn't save the files inside docker container due to - {e}"

     
@mcp.tool()
def run_script_inside_docker_container(filename: str):
    """ 
    To execute a script inside the docker container
    Args:
        filename: Name of the file that is present inside the container which is to be tested
    """
    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "python", f"/app/{filename}"],
            capture_output=True,
            text=True,
            timeout=15
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return f"Couldn't execute the script {filename} inside docker container due to - {e}"

@mcp.tool()
def view_dir_locally(dir:str)->str:
    """ 
    View the contents of a local directory (Not directories inside docker container)
    Args:
        dir: Name of the directory
    Returns:
        Contents of the directory if it is present else None
    """
    try:
        contents=os.listdir(dir)
        return f"The directory {dir} has {contents}"

    except Exception as e:
        return f"The directory {dir} can't be viewed due to {e}"

@mcp.tool()
def create_dir_locally(dir:str)->str:
    """ 
    Create a local directory
    Args:
        dir: Name of the directory
    Returns:
        Information about whether the directory is created or not
    """
    try:
        os.makedirs(os.path.join(dir),exist_ok=True)
        return f"The directory {dir} has been created"

    except Exception as e:
        return f"The directory {dir} couldn't be created in local directory due to {e}"

@mcp.tool()
def create_file_locally(filename:str,info:str)->str:
    """
    Create a file in the local directory inside the folder which was created
    The filename will contain the directory which was created to save the file inside - "directory/filename"
    Args:
        filename: Path of the new file which is to be created with file extension
        info: Information to be stored inside the file
    Returns:
        Information about whether the file is created or not
    """
    try:
        with open(f"{filename}",'w') as f:
            f.write(str(info))
        console.print(f"[bold green] SYSTEM[/bold green]: [cyan]File {filename} saved[/cyan]")
        return f"The file {filename} has been created"
    except Exception as e:
        return f"The file {filename} couldn't be created inside local directory due to {e}"

@mcp.tool()
def read_file_locally(filepath:str)->str:
    """
    Given a single filepath, read the contents of the single file that is present locally
    Args:
        filepath: path of the specific file
    Returns:
        Contents of the file as a string or a Message that the filepath doesn't exist
    """
    try:
        if os.path.exists(filepath):
            with open(filepath,'r',encoding='utf-8') as f:
                content=f.read()
            return content
        else:
            return f"{filepath} doesn't exist, verify the filepath once again"
    except Exception as e:
        return f"Error occured while trying to read the file: {e} " 

if __name__=='__main__':
    mcp.run(transport='stdio')