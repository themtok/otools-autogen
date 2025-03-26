from dataclasses import dataclass
from pydantic import BaseModel
from abc import ABC, abstractmethod
import asyncio

from autogen_core._default_subscription import DefaultSubscription
from collections import defaultdict
from autogen_core._default_topic import DefaultTopicId
import uuid
import enum
from typing import Any
from autogen_core import (
    MessageContext,
    RoutedAgent,
    BaseAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    message_handler,
)


import logging

from autogen_core import TRACE_LOGGER_NAME

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(TRACE_LOGGER_NAME)
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)

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


def create_tool_class(tool: Tool) -> type[RoutedAgent]:
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

@dataclass
class MessageBase:
    pass

@dataclass
class UserRequest(MessageBase):
    message: str
    files: list[str]

#class for the response from the agent
@dataclass
class UserResponse(MessageBase):
    session_id: str
    message: str

@dataclass
class UserRequest2(MessageBase):
    message: str
    files: list[str]


class Orchestrator(BaseAgent):
    def __init__(self, manager: "Manager"):
        super(self.__class__, self).__init__("OrchestratorAgent")
        print(f">>>>__init__  Orchestrator agent. {str(self)}")
        self._manager = manager
    
    
    async def on_message_impl(self, message:Any, ctx: MessageContext)->None:
        session_id = ctx.topic_id.source
        print(f"=============Orchestrator received UserRequest message: {message} with topic id: {ctx.topic_id}")
        await self.publish_message(UserResponse(session_id="123", message="Response"), topic_id=DefaultTopicId(source=session_id))

class Manager:
    class SessionState(enum.Enum):
        WAITING = 1
        PROCESSING = 2


    @dataclass
    class Session:
        session_id: str
        to_client_queue: asyncio.Queue
        state: "Manager.SessionState"



    def __init__(self):
        self._tools = {}
        self._sessions = {}

    def _init_session(self, session_id: str):
        if session_id is None:
            session_id = str(uuid.uuid4())
        else:
            if session_id in self._sessions:
                raise ValueError(f"Session with id {session_id} already exists.")
        self._sessions[session_id] = Manager.Session(
            session_id=session_id,
            to_client_queue=asyncio.Queue(),
            state=Manager.SessionState.WAITING
        )
        return session_id

        
        

    async def send_message(self, message: UserRequest, session_id: str = None):
        if session_id not in self._sessions:
            session_id = self._init_session(session_id)
        session = self._sessions[session_id]
        await self.runtime.publish_message(message=message,topic_id=DefaultTopicId(source=session_id))
        return session_id
    

    async def start(self):
        self.runtime = SingleThreadedAgentRuntime()
        await self._add_internal_agents(self.runtime)
        self.runtime.start()

    async def stop(self,when_idle=False):
        if when_idle:
            await self.runtime.stop_when_idle()
        else:
            await self.runtime.stop()


    async def _add_internal_agents(self, runtime):
        
                
        orch_agent_type = await Orchestrator.register(
            runtime=runtime,
            type="OrchestratorAgent",
            factory=lambda: Orchestrator(self)
        )
        
        orch_subscr = DefaultSubscription(agent_type=orch_agent_type)
        # orch_subscr = TypeSubscription(agent_type=orch_agent_type)
        await self.runtime.add_subscription(orch_subscr)

        orch_agent_type = await Orchestrator.register(
            runtime=runtime,
            type="OrchestratorAgent2",
            factory=lambda: Orchestrator(self)
        )
        
        orch_subscr = DefaultSubscription(agent_type=orch_agent_type)
        # orch_subscr = TypeSubscription(agent_type=orch_agent_type)
        await self.runtime.add_subscription(orch_subscr)

        



if __name__ == "__main__":
    async def m():
        m = Manager()
        await m.start()
        print("Manager started.")
        sid = await m.send_message(UserRequest(message="Hello", files=["file1", "file2"]))
        print(f"---------------Session id: {sid}")
        await m.send_message(UserRequest2(message="Hello2", files=["file1", "file2"]), session_id=sid)


        sid2 = await m.send_message(UserRequest(message="Hello", files=["file1", "file2"]))
        print(f"----------------Session id: {sid2}")
        await m.send_message(UserRequest2(message="Hello2", files=["file1", "file2"]), session_id=sid2)
        await m.send_message(message="dupa", session_id=sid2)


        await m.stop(True)



    asyncio.run(m())

        