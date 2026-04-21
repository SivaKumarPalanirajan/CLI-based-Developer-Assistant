from langchain.tools import tool
from langchain.agents.middleware import HumanInTheLoopMiddleware,TodoListMiddleware
from langchain.agents import create_agent
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver 
import os 
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from prompts import build_system_prompt
from utils import AGENT_EXECUTION_WITH_RETRIES,create_dir,create_file,view_dir,test_script,save_project_in_container,DISPLAY_STEPS,display_code
from rich.console import Console 
from rich.align import Align
from rich.table import Table


MAIN_DIR="AgentScripts"
CUR_DIR=os.path.curdir
config_main_agent={"configurable":{"thread_id":"Main-run"}}

load_dotenv()
groq_api=os.environ["GROQ_API_KEY"]
model=ChatGroq(model="openai/gpt-oss-20b",api_key=groq_api)
inmemory=InMemorySaver()

console=Console()

console.print(Align.center("[bold yellow] CODING ASSISTANT v1.0 [/bold yellow]"))
features_list=Table(title="Available Features")
features_list.add_column("Features")
features_list.add_row("View Directories")
features_list.add_row('Create Directories')
features_list.add_row('Create files')
features_list.add_row('Create files inside a docker container')
features_list.add_row('Execute scripts inside a docker container')
features_list.add_row('To-Do List for simplification of tasks')
features_list.add_row('Human-in-the-loop control for script generation')
features_list.add_row("Retry loops for automatic error/bug correction")
console.print(Align.center(features_list))

console.print("[bold green] SYSTEM[/bold green]: [cyan] Do you want to allow the Agent to access the current directory? [/cyan]Approve or Reject?")
ACCESS_TO_DIR=str(console.input("[bold blue] USER[/bold blue]: "))

if ACCESS_TO_DIR:
    if {"Okay":'yes',"yes":"yes","no":"no","approve":"yes","reject":"no"}.get(str(ACCESS_TO_DIR.lower()))=="yes":
        txt_file_agent=create_agent(
            model=model,
            tools=[create_file,create_dir,view_dir,test_script,save_project_in_container,display_code],
            system_prompt=build_system_prompt(MAIN_DIR),
            middleware=[HumanInTheLoopMiddleware(
                interrupt_on={
                    "create_file":
                    {
                        "allowed_decisions":["approve","reject"]
                    },
                    "create_dir":False,
                    "view_dir":False,
                }
            ),TodoListMiddleware()]
            ,
            checkpointer=inmemory
        )


        input_prompt=str(console.input("[bold green] SYSTEM[/bold green]: [cyan]What would you like to create today? [/cyan]"))

        if input_prompt:
            STATUS=AGENT_EXECUTION_WITH_RETRIES(txt_file_agent,input_prompt,config_main_agent,MAX_RETRIES=3)
            
            if STATUS:
                console.print("[bold green] SYSTEM[/bold green]:[red] Agent Execution failed [/red]")
            
                    
    else:
        console.print("[bold green] SYSTEM[/bold green]:[red] Directory access required to use the Agent [/red]")