from dataclasses import dataclass
from pydantic import BaseModel
from abc import ABC, abstractmethod
import asyncio
from functools import wraps

from autogen_core._default_subscription import DefaultSubscription
from autogen_core._default_topic import DefaultTopicId
import uuid
import enum
from typing import Any, Optional
from autogen_core import (
    AgentId,
    MessageContext,
    RoutedAgent,
    BaseAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    message_handler,
)
from .tools import create_tool_class, Tool, ToolCard

import logging

from autogen_core import TRACE_LOGGER_NAME

from .agents import Orchestrator, QueryAnalyzer, ActionPredictor, CommandGenerator, ContextVerifier, FinalOutputAgent
from .utils import only_direct, logger

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(TRACE_LOGGER_NAME)
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)








@dataclass
class UserRequest:
    message: str
    files: list[str]
    max_steps: int = 5

#class for the response from the agent
@dataclass
class UserResponse:
    type: str
    session_id: str
    message: str
    tool_used: str
    final: bool
    conclusion: bool
    step_no: int
    command: Optional[str] = None


       
            


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
        
    def register_tool(self, tool_name,tool: type[Tool]):
        self._tools[tool_name] = tool()
    
    def get_tool(self, tool_name: str) -> Tool:
        return self._tools[tool_name]
    
    def get_session(self, session_id: str) -> "Manager.Session":
        return self._sessions[session_id]
    
    def get_tool_cards(self) -> dict:
        return {tool_name: tool.card for tool_name, tool in self._tools.items()}

    async def  _init_session(self, session_id: str):
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
        await self.runtime.publish_message("bootstrap", DefaultTopicId(source=session_id))   
        return session_id

        
        

    async def send_message(self, message: UserRequest, session_id: str = None):
        if session_id not in self._sessions:
            session_id = await self._init_session(session_id)
        _session = self._sessions[session_id]
        await self.runtime.publish_message(message=message,topic_id=DefaultTopicId(source=session_id))
        return session_id
    
    async def stream(self, session_id):
        if session_id not in self._sessions:
            raise RuntimeError("Invalid session")

        queue = self._sessions[session_id].to_client_queue

        while True:
            msg:UserResponse = await queue.get()
            yield msg
            if msg.final:
                break

    async def start(self):
        self.runtime = SingleThreadedAgentRuntime()
        await self._add_internal_agents(self.runtime)
        for tool_id, tool in self._tools.items():
            tool_cls = create_tool_class(tool)
            await tool_cls.register(
                runtime=self.runtime,
                type=tool_id,
                factory=lambda cls=tool_cls: cls()
            )
            subscr = DefaultSubscription(agent_type=tool_id)
            await self.runtime.add_subscription(subscr)
        
        
        self.runtime.start()
         

    async def stop(self,when_idle=False):
        if when_idle:
            await self.runtime.stop_when_idle()
        else:
            await self.runtime.stop()


    async def _add_internal_agents(self, runtime):
        internal_agents = [
            ("QueryAnalyzer", QueryAnalyzer),
            ("ActionPredictor", ActionPredictor),
            ("CommandGenerator", CommandGenerator),
            ("ContextVerifier", ContextVerifier),
            ("FinalOutputAgent", FinalOutputAgent),
        ]
        
        for agent_name, agent_cls in internal_agents:
            agent_type = await agent_cls.register(
                runtime=runtime,
                type=agent_name,
                factory=lambda cls=agent_cls: cls()
            )
            subscr = DefaultSubscription(agent_type=agent_type)
            await runtime.add_subscription(subscr)
            
            
        
        from .agents import Orchestrator
        orch_agent_type = await Orchestrator.register(
            runtime=runtime,
            type="OrchestratorAgent",
            factory=lambda: Orchestrator(self)
        )
        
        orch_subscr = DefaultSubscription(agent_type=orch_agent_type)
        await runtime.add_subscription(orch_subscr)
       

        