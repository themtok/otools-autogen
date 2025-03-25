from dataclasses import dataclass
from pydantic import BaseModel
from abc import ABC, abstractmethod
import asyncio

from autogen_core._default_subscription import DefaultSubscription


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
    def __init__(self):
        self._tools = {}
        self.to_agent_queue = asyncio.Queue()
        self.to_agent_queue = asyncio.Queue()
        
    
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
            super(self.__class__, self).__init__(f"Tool: {tool.card.name} agent.")

        class_dict = {
            "__init__": __init__,
            "handle_message": handle_message
        }

        ToolCls = type(tool.card.name, (RoutedAgent,), class_dict)

        return ToolCls


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
    asyncio.run(manager.stop())
    