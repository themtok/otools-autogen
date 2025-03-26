from abc import ABC, abstractmethod
from dataclasses import dataclass
from pydantic import BaseModel
from autogen_core import BaseAgent, MessageContext
from .utils import only_direct, logger



@dataclass
class ToolCard:
    name: str
    description: str
    demo_input: list
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
    
    
    
def create_tool_class(tool: Tool) -> type[BaseAgent]:
        async def on_message_impl(self, message, ctx: MessageContext):
            parsed_message = None
            if isinstance(message, tool.card.inputs):
                parsed_message = message
            else:
                parsed_message = tool.card.inputs.model_validate(message)
            out = await tool.run(parsed_message) 
            parsed_response = tool.card.outputs.model_validate(out)                           
            return parsed_response

        on_message_impl.__annotations__ = {
            "message": tool.card.inputs,
            "ctx": MessageContext,
            "return": None,
        }

        on_message_impl = only_direct(on_message_impl)

        def __init__(self):
            logger.debug(f"Tool initialization {tool.card.name} agent. {str(self)}")
            super(self.__class__, self).__init__(f"Tool: {tool.card.name} agent.")

        class_dict = {
            "__init__": __init__,
            "on_message_impl": on_message_impl
        }

        ToolCls = type(tool.card.name, (BaseAgent,), class_dict)

        return ToolCls