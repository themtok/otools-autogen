from dataclasses import dataclass
from pydantic import BaseModel
from abc import ABC, abstractmethod
import asyncio

from autogen_core._default_subscription import DefaultSubscription
from collections import defaultdict
from autogen_core._default_topic import DefaultTopicId

from typing import Any


from autogen_core import (
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    message_handler,
)

@dataclass
class ToolCard:
    name: str
    description: str
    inputs: type[BaseModel]
    outputs: type[BaseModel]
    user_metadata: dict


class Tool(ABC):
    @property
    @abstractmethod
    def card(self) -> ToolCard:
        pass
    
    @abstractmethod
    async def run(self, inputs: BaseModel) -> BaseModel:
        pass



class DefaultManager():
    
    #class for the message from the user
    @dataclass
    class UserMessage:
        session_id: str
        message: str
        files: list[str]
    
    #class for the response from the agent
    @dataclass
    class UserResponse:
        session_id: str
        message: str
        
        
        
    @dataclass
    class SessionProxyMessage:
        message: str
        final: bool
    
    
    def __init__(self):
        self._tools = {}
        self.session_input_queues = defaultdict(asyncio.Queue)   # session_id -> input queue
        self.session_output_queues = defaultdict(asyncio.Queue)  # session_id -> output queue
        self.session_locks = defaultdict(asyncio.Lock)           # session_id -> lock
        self.session_tasks = {}
        self.from_runtime_queue = asyncio.Queue()
        
    async def send(self, session_id: str, message: UserMessage) -> None:
        input_queue = self.session_input_queues[session_id]
        await input_queue.put(message)

        if session_id not in self.session_tasks:
            self.session_tasks[session_id] = asyncio.create_task(
                self._process_session(session_id)
            )
            
            
    async def get_reply(self, session_id: str):
        return await self.session_output_queues[session_id].get()

    def is_session_busy(self, session_id:str):
        return self.session_locks[session_id].locked()
    
    def is_final_message(self, session_id:str, message:SessionProxyMessage) -> bool:
        return message.final

    async def _process_session(self, session_id:str):
        lock = self.session_locks[session_id]
        input_queue = self.session_input_queues[session_id]
        output_queue = self.session_output_queues[session_id]

        async with lock:
            while True:
                message = await input_queue.get()

                try:
                    response = await self.on_ext_message(session_id, message)
                    await output_queue.put(response)
                except Exception as e:
                    pass
                if self.is_final_message(session_id, message):
                    break    
        
    
        
   
                
    async def on_ext_message(self, session_id, message):
        await self.runtime.publish_message(message,topic_id=DefaultTopicId(source=session_id))
    
    
        
    def register_tool(self, tool: type[Tool]):
        self._tools[tool.__name__] = tool()
    
    def get_tool(self, tool_name: str) -> Tool:
        return self._tools[tool_name]
    
    def get_tool_cards(self) -> dict:
        return {tool_name: tool.card for tool_name, tool in self._tools.items()}
    
    
    def create_tool_class(self, tool: Tool) -> type[RoutedAgent]:
        async def handle_message(self, message, ctx: MessageContext):
            parsed_message = None
            if isinstance(message, tool.card.inputs):
                parsed_message = message
            else:
                parsed_message = tool.card.inputs.model_validate(message)
            out = await tool.run(parsed_message) 
            parsed_response = tool.card.outputs.model_validate(out)                           
            await self.publish_message(parsed_response, ctx.topic_id)  # type: ignore

        handle_message.__annotations__ = {
            "message": tool.card.inputs,
            "ctx": MessageContext,
            "return": None,
        }

        handle_message = message_handler(handle_message)

        def __init__(self):
            print(f"__init__  {tool.card.name} agent. {str(self)}")
            super(self.__class__, self).__init__(f"Tool: {tool.card.name} agent.")

        class_dict = {
            "__init__": __init__,
            "handle_message": handle_message
        }

        ToolCls = type(tool.card.name, (RoutedAgent,), class_dict)

        return ToolCls


    async def _add_internal_agets(self, runtime):
        class SessionProxyAgent(RoutedAgent):
            def __init__(self, from_runtime_queue):
                super(self.__class__, self).__init__("Session proxy agent.")
                print(f"__init__  SessionProxyAgent agent. {str(self)}")
                self.from_runtime_queue = from_runtime_queue
            
            @message_handler
            async def handle_message(self, message: DefaultManager.SessionProxyMessage, ctx)->None:
                print(f"SessionProxyAgent received message: {message}")
                await self.from_runtime_queue.put((ctx.session_id, message))
                
        session_proxy_agent_type = await SessionProxyAgent.register(
            runtime=runtime,
            type="SessionProxyAgent",
            factory=lambda: SessionProxyAgent(self.from_runtime_queue)
        )
        
        session_proxy_subscr = DefaultSubscription(agent_type=session_proxy_agent_type)
        await self.runtime.add_subscription(session_proxy_subscr)
        
        
    
    async def run(self):
        self.runtime = SingleThreadedAgentRuntime()
        for tool_name, tool in self._tools.items():
            tool_cls = self.create_tool_class(tool)
            await tool_cls.register(
                runtime=self.runtime,
                type=tool.card.name,
                factory=lambda: tool_cls()
            )
            subscr = DefaultSubscription(agent_type=tool.card.name)
            await self.runtime.add_subscription(subscr)
        await self._add_internal_agets(self.runtime)
        self.runtime.start()

    async def stop(self,when_idle=False):
        if when_idle:
            await self.runtime.stop_when_idle()
        else:
            await self.runtime.stop()
            
    


    



    
if __name__ == "__main__":
    class MyTool(Tool):
        @property
        def card(self) -> ToolCard:
            return ToolCard(
                name="MyTool",
                description="A tool that does something",
                inputs=BaseModel,
                outputs=BaseModel,
                user_metadata={}
            )

        async def run(self, inputs: BaseModel) -> BaseModel:
            return BaseModel()
    
    manager = DefaultManager()
    manager.register_tool(MyTool)
    asyncio.run(manager.run())
    asyncio.run(manager.send("session1", "hello") )