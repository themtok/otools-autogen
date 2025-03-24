from autogen_core import DefaultTopicId, MessageContext, RoutedAgent, default_subscription, message_handler



from abc import ABC, abstractmethod
from pydantic import BaseModel
from dataclasses import dataclass


@dataclass
class ToolCard:
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
    




class MyTool(Tool):
    class MyToolInput(BaseModel):
        input: str
    
    class MyToolOutput(BaseModel):
        output: str
    
    def __init__(self):
        self._card = ToolCard(description="This tool is a simple echo tool that returns the input as the output.",
                             inputs=self.MyToolInput,
                             outputs=self.MyToolOutput,
                             user_metadata={"author": "Your Name", "version": "0.0.1"})
        
    @property
    def card(self) -> ToolCard:
        return self._card
    
    async def run(self, inputs: BaseModel) -> BaseModel:
        return self.MyToolOutput(output=inputs.input)

from typing import Type



def create_modifier_class(tool: Tool) -> Type:
    # Define the method
    async def handle_message(self, message, ctx):
        parsed_message = None
        if isinstance(message, tool.card.inputs):
            parsed_message = message
        else:
            parsed_message = tool.card.inputs.parse_obj(message)
        print(f"Received message: {parsed_message}")
        out = tool.card.outputs(output="oout")
        
        await self.publish_message(out, DefaultTopicId())  # type: ignore

    # Add type annotations manually
    handle_message.__annotations__ = {
        "message": tool.card.inputs,
        "ctx": MessageContext,
        "return": None,
    }

    # Decorate the method
    handle_message = message_handler(handle_message)

    # Define __init__ with proper super call
    def __init__(self):
        super(self.__class__, self).__init__("A modifier agent.")

    # Build the class dict
    class_dict = {
        "__init__": __init__,
        "handle_message": handle_message,
    }

    # Dynamically create the class
    ModifierCls = type("Modifier", (RoutedAgent,), class_dict)

    # Apply the class decorator
    ModifierCls = default_subscription(ModifierCls)

    return ModifierCls

tool_cls = create_modifier_class(tool=MyTool())


from autogen_core import AgentId, SingleThreadedAgentRuntime
runtime = SingleThreadedAgentRuntime()
async def main():
    await tool_cls.register(
        runtime,
        "modifier",
        lambda: tool_cls(),
    )
    input = MyTool.MyToolInput(input="hello")
    runtime.start()
    await runtime.publish_message(input,topic_id=DefaultTopicId())
    await runtime.publish_message("dadsd",topic_id=DefaultTopicId())

    await runtime.stop_when_idle()

import asyncio

asyncio.run(main())