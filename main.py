import asyncio
from pydantic import BaseModel
from otools_autogen.manager_v2 import Manager, ToolCard, UserRequest, Tool, UserResponse
from dotenv import load_dotenv
from colorama import Fore, Back, Style
import wikipedia
from wikipedia_search_tool import WikipediaSearch
from otools_autogen.manager_v2 import UserRequest, UserResponse
from search_engine_tool import SearchEngineTool
from page_content_extractor import PageContentExtractionTool
from diet_planner_tool import DietPlanningTool
from news_fetch_tool import NewsFetchTool
from generalist import GeneralistTool
import yappi
from api_caller_tool import APICallerTool
from news_api_tool import NewsAPITool
from critic_tool import CriticTool

load_dotenv()



        
        
async def m():
        m = Manager()
        
        m.register_tool("WikipediaSearchTool", WikipediaSearch)
        m.register_tool("SearchEngineTool", SearchEngineTool)
        m.register_tool("PageContentExtractionTool", PageContentExtractionTool)
        m.register_tool("NewsAPITool", NewsAPITool)
        m.register_tool("GeneralistTool", GeneralistTool)
        m.register_tool("APICallerTool", APICallerTool)
        m.register_tool("CriticTool", CriticTool)



        
        
        await m.start()
        print("Manager started.")
        sid = await m.send_message(UserRequest(message="What is the best investment currently?",
                                               files=[],
                                               max_steps=10))
        print(f"---------------Session id: {sid}")
        async for msg in m.stream(sid):
            mm:UserResponse = msg
            print(Fore.GREEN + f"Type: {mm.type}" + Style.RESET_ALL)
            print(Fore.GREEN + f"Response message: {mm.message}" + Style.RESET_ALL)
            print(Fore.BLUE + f"Response tool_used: {mm.tool_used}" + Style.RESET_ALL)
            print(Fore.RED + f"Response command: {mm.command}" + Style.RESET_ALL)
            print(Fore.RED + f"Response Step#: {mm.step_no}" + Style.RESET_ALL)
            print(Fore.RED + f"Response conclusion: {mm.conclusion}" + Style.RESET_ALL)
            print(Fore.RED + f"Response final: {mm.final}" + Style.RESET_ALL)

            

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