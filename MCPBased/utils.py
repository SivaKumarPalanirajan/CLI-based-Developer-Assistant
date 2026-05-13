
import subprocess 
import os 
from langchain_core.messages import ToolMessage
from langgraph.types import Command 
from rich.console import Console 
from rich.syntax import Syntax
from langchain.tools import tool
console=Console()

@tool()
def display_code(files):
    """
    After testing is completed, provide the codes to this function in the form of a dictionary so the user can view it.
    Args:
        files: dictionary containing the filenames and content of the files
    Example:
        {"main.py":"print('Hello')"}
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


async def AGENT_EXECUTION_WITH_RETRIES(AGENT,PROMPT,CONFIG,MAX_RETRIES):
    FAILED=False

    for cnt in range(1,MAX_RETRIES+1):
        try:
            async for chunk in AGENT.astream({"messages":[{"role":"user","content":PROMPT}]},\
                                config=CONFIG,
                                astream_mode="updates"):
                DISPLAY_STEPS(chunk)
                
                if chunk.get("__interrupt__",None) is not None:
                    console.print("[bold yellow] AGENT[/bold yellow]: [cyan]Executing Paused - The agent wants to create files[/cyan]")
                    console.print("[bold green] SYSTEM[/bold green] : [cyan]Approve or Reject?[/cyan]")
                    decision=str(console.input("[bold blue] USER[/bold blue]: ")).lower()
                    if decision is not None:
                        async for chunk in AGENT.astream(
                                Command(
                                    resume={"decisions":[{
                                        "type":decision
                                    }]}),
                                config=CONFIG,
                                astream_mode="updates"):
                            
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