import asyncio
from pydantic import BaseModel
from otools_autogen.manager_v2 import Manager, ToolCard, UserRequest, Tool, UserRequest2
from dotenv import load_dotenv
load_dotenv()


async def m():
        m = Manager()
        class MyTool(Tool):
            class MyToolInput(BaseModel):
                message: str
                
            class MyToolOutput(BaseModel):
                message: str
            @property
            def card(self) -> ToolCard:
                return ToolCard(
                    name="Diet composer tool",
                    description="Tool for composing a diet. It is able to generate a diet based on the user's preferences.",
                    inputs=MyTool.MyToolInput,
                    outputs=MyTool.MyToolOutput,
                    user_metadata={}
                )

            async def run(self, inputs: MyToolInput) -> BaseModel:
                print(f"Running MyTool with input: {inputs.message}")
                return MyTool.MyToolOutput(message="out")
        
        m.register_tool("Diet composer tool",MyTool)
        
        await m.start()
        print("Manager started.")
        sid = await m.send_message(UserRequest(message="Compose diet for diabetic", files=[]))
        print(f"---------------Session id: {sid}")


        # sid2 = await m.send_message(UserRequest(message="Hello", files=["file1", "file2"]))
        # print(f"----------------Session id: {sid2}")
        # await m.send_message(UserRequest2(message="Hello2", files=["file1", "file2"]), session_id=sid2)
        # await m.send_message(message="dupa", session_id=sid2)
        
        await m.stop(True)



asyncio.run(m())