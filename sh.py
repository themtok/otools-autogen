from shiny.express import ui, render
from otools_autogen.manager_v2 import Manager, UserRequest, UserResponse
from news_fetch_tool import NewsFetchTool
from diet_planner_tool import DietPlanningTool
from wikipedia_search_tool import WikipediaSearch


m:Manager = None

async def init_manager():
    global m
    if m is None:
        m = Manager()
        m.register_tool("DietComposerTool", DietPlanningTool)
        m.register_tool("WikipediaSearchTool", WikipediaSearch)
        m.register_tool("NewsFetchTool", NewsFetchTool)
        await m.start()
        

ui.page_opts(
    title="Hello Shiny Chat",
    fillable=True,
    fillable_mobile=True,
)

# Create a chat instance and display it 
chat = ui.Chat(id="chat")  
chat.ui()  

async def stream_respone(user_input):
    sid = await m.send_message(UserRequest(message=user_input, files=[]))
    async for msg in m.stream(sid):
        mm: UserResponse = msg
        msg =f"""
**Message**: {mm.message}  
**Tool**: {mm.tool_used}  
**Step**: {mm.step_no}  
**Conclusion**: {mm.conclusion}  
**Final**: {mm.final}
""" 
        yield msg




@chat.on_user_submit  
async def handle_user_input(user_input: str):  
    await init_manager()
    await chat.append_message_stream(stream_respone(user_input=user_input))

    
    