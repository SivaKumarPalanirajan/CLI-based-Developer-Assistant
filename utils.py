
import subprocess 
import os 
from langchain.tools import tool 
from langchain_core.messages import ToolMessage
from langgraph.types import Command 
from rich.console import Console 
from rich.syntax import Syntax

console=Console()
def write_file_to_container(container, filename, content):
    process = subprocess.Popen(
        ["docker", "exec", "-i", container, "sh", "-c", f"cat > /app/{filename}"],
        stdin=subprocess.PIPE,
        text=True
    )
    process.communicate(content)


@tool()
def save_project_in_container(files: dict):
    """
    Write the project inside the docker container before testing
    Args:
        files: a dictionary which contains filenames and content of the files as a string
    Example:
      files={"main.py":"print('Hello')"}
    """
    try:
        subprocess.run(["docker", "exec", "python_sandbox", "rm", "-rf", "/app/*"])

        for filename, content in files.items():
            write_file_to_container("python_sandbox", filename, content)

        return "Files written successfully"
    except Exception as e: 
        return f"Couldn't save the files inside docker container due to - {e}"

     
@tool()
def test_script(filename: str):
    """ 
    To Test the script by executing the runner file inside the docker container
    Args:
        filename: Name of the file that is present inside the container which is to be tested
    """
    try:
        result = subprocess.run(
            ["docker", "exec", "python_sandbox", "python", f"/app/{filename}"],
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
        return f"Couldn't test the script {filename} inside docker container due to - {e}"

@tool()
def view_dir(dir:str)->str:
    """ 
    View the contents of a directory (Not directories inside docker container)
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


@tool()
def create_dir(dir:str)->str:
    """ 
    Create a directory locally
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

@tool()
def display_code(files):
    """
    After testing is completed, provide the codes to this function in the form of a dictionary so the user can view it.
    Args:
        files: dictionary containing the filenames and content of the files
    Example:
        files={"main.py":"print('Hello')"}
    """
    try:
        for filename,filecontent in files.items():
            console.print("[bold yellow] AGENT[/bold yellow]:")
            console.print("FileName: ",filename)
            console.print("Content:")
            code = Syntax(filecontent, "python", theme="monokai", line_numbers=True)
            console.print(code)
        return "Successfully displayed the codes to the user"
    except Exception as e:
        return f"The codes couldn't be displayed to the user due to - {e}"
    
@tool()
def create_file(filename:str,info:str)->str:
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


def DISPLAY_STEPS(chunk):
    if "__interrupt__" in chunk:
        stage = "WAITING_FOR_APPROVAL"

    elif "tools" in chunk:
        for msg in chunk["tools"]['messages']:
            if isinstance(msg,ToolMessage):
                console.print(f"""[bold yellow] AGENT[/bold yellow]: [cyan]Executed tool {chunk['tools']["messages"][0].name} - {chunk['tools']["messages"][0].content} [/cyan]""",end="\n")  
            stage = "TOOL EXECUTION COMPLETE"

    elif "model" in chunk:
        stage = "MODEL GENERATING"
        console.print("[bold yellow] AGENT[/bold yellow]: [cyan]Generating...[/cyan]",end="\n")


def AGENT_EXECUTION_WITH_RETRIES(AGENT,PROMPT,CONFIG,MAX_RETRIES):
    FAILED=False

    for cnt in range(1,MAX_RETRIES+1):
        try:
            for chunk in AGENT.stream({"messages":[{"role":"user","content":PROMPT}]},\
                                config=CONFIG,
                                stream_mode="updates"):
                DISPLAY_STEPS(chunk)
                
                if chunk.get("__interrupt__",None) is not None:
                    console.print("[bold yellow] AGENT[/bold yellow]: [cyan]Executing Paused - The agent wants to create files[/cyan]")
                    console.print("[bold green] SYSTEM[/bold green] : [cyan]Approve or Reject?[/cyan]")
                    decision=str(console.input("[bold blue] USER[/bold blue]: ")).lower()
                    if decision is not None:
                        for chunk in AGENT.stream(
                                Command(
                                    resume={"decisions":[{
                                        "type":decision
                                    }]}),
                                config=CONFIG,
                                stream_mode="updates"):
                            
                            DISPLAY_STEPS(chunk)
                        FAILED=False
                        if decision=='approve':
                            console.print("[bold green] SYSTEM[/bold green]: [cyan]Agent has saved the scripts[/cyan]")
                        else:
                            console.print("[bold green] SYSTEM[/bold green]: [cyan]Script creation cancelled[/cyan]")
            break
        except Exception as e:
            FAILED=True
            console.print(f"[bold green] SYSTEM[/bold green]: [red] Error Occured in Agent execution - {e} [/red]")
            console.print(f"[bold green] SYSTEM[/bold green]: [cyan] Retrying ------------------------------- ({cnt}) [/cyan]")
        
    return FAILED