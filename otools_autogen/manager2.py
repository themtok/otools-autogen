from autogen_core import DefaultTopicId, MessageContext, RoutedAgent, default_subscription, message_handler

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import List

from autogen_core import (
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    message_handler,
)
from autogen_core._default_subscription import DefaultSubscription
from autogen_core._default_topic import DefaultTopicId
from autogen_core.models import (
    SystemMessage,
)

from abc import ABC, abstractmethod
from pydantic import BaseModel
from dataclasses import dataclass


@dataclass
class AgentDiscoveryMessage:
    pass

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
        self.__class__
        return self._card
    
    async def run(self, inputs: BaseModel) -> BaseModel:
        return self.MyToolOutput(output=inputs.input)

from typing import Type



def create_modifier_class(tool: Tool, prefix="dasd") -> Type:
    # Define the method
    async def handle_message(self, message, ctx):
        parsed_message = None
        if isinstance(message, tool.card.inputs):
            parsed_message = message
        else:
            parsed_message = tool.card.inputs.parse_obj(message)
        print(f"---> {self.__class__} Received message: {parsed_message}")
        out = tool.card.outputs(output="oout")
        
        await self.publish_message(out, DefaultTopicId())  # type: ignore

    async def handle_discovery_message(self, message, ctx):
        await self.publish_message(tool.card, DefaultTopicId())


     # Add type annotations manually
    handle_discovery_message.__annotations__ = {
        "message": AgentDiscoveryMessage,
        "ctx": MessageContext,
        "return": None,
    }

    # Add type annotations manually
    handle_message.__annotations__ = {
        "message": tool.card.inputs,
        "ctx": MessageContext,
        "return": None,
    }

    # Decorate the method
    handle_message = message_handler(handle_message)

    handle_discovery_message = message_handler(handle_discovery_message)


    # Define __init__ with proper super call
    def __init__(self):
        print(f"__init__  A agent. {str(self)}")
        super(self.__class__, self).__init__("A modifier agent.")

    # Build the class dict
    class_dict = {
        "__init__": __init__,
        "handle_message": handle_message,
        "handle_discovery_message": handle_discovery_message  
    }

    # Dynamically create the class
    ModifierCls = type(prefix+"Tool", (RoutedAgent,), class_dict)

    # Apply the class decorator
    # ModifierCls = default_subscription(ModifierCls)

    return ModifierCls

tool_cls = create_modifier_class(tool=MyTool(),prefix="One")
tool_cls2 = create_modifier_class(tool=MyTool(),prefix="Two")
global_agent = create_modifier_class(tool=MyTool(),prefix="Global")



from autogen_core import AgentId, SingleThreadedAgentRuntime
runtime = SingleThreadedAgentRuntime()
async def main():
    await tool_cls.register(
        runtime=runtime,
        type="specialist_agent_type",
        factory=lambda: tool_cls(),
    )

    specialist_subscription = DefaultSubscription(agent_type="specialist_agent_type")
    await runtime.add_subscription(specialist_subscription)

    await tool_cls2.register(
       runtime=runtime,
        type="specialist_agent_type2",
        factory=lambda: tool_cls2(),
    )
    specialist_subscription2 = DefaultSubscription(agent_type="specialist_agent_type2")
    await runtime.add_subscription(specialist_subscription2)


    global_agent_type = await global_agent.register(
        runtime=runtime,
        type="global_agent",
        factory=lambda: global_agent(),
    )

    await runtime.add_subscription(DefaultSubscription(topic_type='*',agent_type=global_agent_type))
    # await runtime.add_subscription(DefaultSubscription(agent_type="global_agent", topic_type="default"))
    # await runtime.add_subscription(DefaultSubscription(agent_type="global_agent", topic_type="default"))
    


    input = MyTool.MyToolInput(input="hello")
    runtime.start()
    await runtime.publish_message(input,topic_id=DefaultTopicId(source="one"))
    # await runtime.publish_message(input,topic_id=DefaultTopicId(source="one"))
    # await runtime.publish_message(input,topic_id=DefaultTopicId(source="one"))
    await runtime.publish_message(input,topic_id=DefaultTopicId(source="two"))
    await runtime.publish_message(input,topic_id=DefaultTopicId(source="three"))

    await runtime.publish_message(input,topic_id=DefaultTopicId(source="four"))




    await runtime.stop_when_idle()

import asyncio

asyncio.run(main())