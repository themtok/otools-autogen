import asyncio
from datetime import datetime
from pydantic import BaseModel
from otools_autogen.runtime import Runtime, ToolCard, UserRequest, Tool, UserResponse
from dotenv import load_dotenv
from colorama import Fore, Back, Style
import wikipedia
from wikipedia_search_tool import WikipediaSearch
from otools_autogen.runtime import UserRequest, UserResponse
from search_engine_tool import SearchEngineTool
from page_content_extractor import PageContentExtractionTool
from diet_planner_tool import DietPlanningTool
from news_fetch_tool import NewsFetchTool
from generalist import GeneralistTool
import yappi
from api_caller_tool import APICallerTool
from news_api_tool import NewsAPITool
from critic_tool import CriticTool
import logging
import os

load_dotenv()

logger = logging.getLogger("otools_autogen")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)


timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"logs/otools_autogen_llm_{timestamp}.log"

os.makedirs(os.path.dirname(log_filename), exist_ok=True)



llm_logger = logging.getLogger("otools_autogen_llm")
llm_logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_filename,encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

llm_logger.addHandler(file_handler)
# llm_logger.addHandler(console_handler)

        
        
async def m():
        m = Runtime()
        
        m.register_tool("WikipediaSearchTool", WikipediaSearch)
        m.register_tool("SearchEngineTool", SearchEngineTool)
        m.register_tool("PageContentExtractionTool", PageContentExtractionTool)
        m.register_tool("NewsAPITool", NewsAPITool)
        m.register_tool("GeneralistTool", GeneralistTool)
        m.register_tool("APICallerTool", APICallerTool)
        m.register_tool("CriticTool", CriticTool)



        
        
        await m.start()
        print("Manager started.")
        sid = await m.send_message(UserRequest(message="Is happiness of countries really related to their GDP? If yes, how? If no, why not?",
                                               files=[],
                                               max_steps=10))
        print(f"---------------Session id: {sid}")
        async for msg in m.stream(sid):
            mm:UserResponse = msg
            print(Fore.GREEN + f"===================================" + Style.RESET_ALL)
            print(Fore.GREEN + f"Type: {mm.type}" + Style.RESET_ALL)
            print(Fore.GREEN + f"Message: {mm.message}" + Style.RESET_ALL)
            print(Fore.BLUE + f"Tool_used: {mm.tool_used}" + Style.RESET_ALL)
            print(Fore.RED + f"Tool command: {mm.command}" + Style.RESET_ALL)
            print(Fore.RED + f"Current Step#: {mm.step_no}" + Style.RESET_ALL)
            print(Fore.RED + f"Conclusion: {mm.conclusion}" + Style.RESET_ALL)
            print(Fore.RED + f"Final: {mm.final}" + Style.RESET_ALL)
            print(Fore.GREEN + f"===================================" + Style.RESET_ALL)

            

        # sid2 = await m.send_message(UserRequest(message="Hello", files=["file1", "file2"]))
        # print(f"----------------Session id: {sid2}")
        # await m.send_message(UserRequest2(message="Hello2", files=["file1", "file2"]), session_id=sid2)
        # await m.send_message(message="dupa", session_id=sid2)
        
        await m.stop(True)


# yappi.set_clock_type("wall")  # or "cpu"
# yappi.start()

asyncio.run(m())


# yappi.stop()
# yappi.get_func_stats().print_all()