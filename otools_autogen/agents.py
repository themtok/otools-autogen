from dataclasses import dataclass
from pydantic import BaseModel
import asyncio
from PIL import Image
import os
from dotenv import load_dotenv
import asyncio
from openai import AsyncOpenAI
from typing import Any, TYPE_CHECKING, Dict
from autogen_core import (
    AgentId,
    MessageContext,
    BaseAgent)





from .utils import only_direct, logger


if TYPE_CHECKING:
    from .manager_v2 import Manager, UserRequest
    
    
@dataclass
class QueryAnalyzerRequest():
    user_query: str
    images: list[str]
    all_tools_names: list[str]
    all_tools_description: list[str]

@dataclass
class QueryAnalyzerResponse():
    message: str


@dataclass
class ActionPredictorRequest():
    initial_query: str
    image_paths: list[str]
    query_analysis: str
    step_count: int
    max_step_count: int
    aviailable_tools: list[str]
    aviailable_tools_metadata: list[str]
    actions_history: list[str]
    

@dataclass
class ActionPredictorResponse():
    message: str
    

@dataclass
class CommandGeneratorRequest():
    initial_query: str
    image_paths: list[str]
    query_analysis: str
    sub_goal: str
    tool_name: str
    tool_metadata: str
    context: str

    
@dataclass
class CommangGeneratorResponse():
    message: str
    
@dataclass
class CommandExecutorResponse():
    message: str
    
@dataclass
class ContextVerifierResponse():
    message: str
    
class QueryAnalysisLLMResponse(BaseModel):
        concise_summary: str
        required_skills: str
        relevant_tools: str
        additional_considerations: str

        def __str__(self):
            return f"""
    Concise Summary: {self.concise_summary}

    Required Skills:
    {self.required_skills}

    Relevant Tools:
    {self.relevant_tools}

    Additional Considerations:
    {self.additional_considerations}
    """

class ToolCommand(BaseModel):
    analysis: str
    explanation: str
    command: str

class NextStepLLMResponse(BaseModel):
    justification: str
    context: str
    sub_goal: str
    tool_name: str    

class QueryAnalyzer(BaseAgent):
    def __init__(self):
        super().__init__("QueryAnalyzer")
        logger.debug(f"QueryAnalyzer initialized. {str(self)} {self.id}")
        
    @only_direct
    async def on_message_impl(self, message:QueryAnalyzerRequest, ctx: MessageContext)->None:
        logger.debug(f"QueryAnalyzer {self.id} received message: {message}")
        await self.analyze(message)
        return QueryAnalyzerResponse(message="QueryAnalyzer response")
    
    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        image_info = {}
        if image_path and os.path.isfile(image_path):
            image_info["image_path"] = image_path
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                image_info.update({
                    "width": width,
                    "height": height
                })
            except Exception as e:
                print(f"Error processing image file: {str(e)}")
        return image_info
    
    async def analyze(self, message:QueryAnalyzerRequest)->QueryAnalysisLLMResponse:
        question = message.user_query
        
        
        image_infos = [self.get_image_info(image_path) for image_path in message.images]
        image_infos_str = "\n".join([f"Image: {info['image_path']}, Width: {info['width']}, Height: {info['height']}" for info in image_infos])
        
        
        query_prompt = f"""
Task: Analyze the given query with accompanying inputs and determine the skills and tools needed to address it effectively.

Available tools: {message.all_tools_names}

Metadata for the tools: {message.all_tools_description}

Image: {image_infos_str}

Query: {question}

Instructions:
1. Carefully read and understand the query and any accompanying inputs.
2. Identify the main objectives or tasks within the query.
3. List the specific skills that would be necessary to address the query comprehensively.
4. Examine the available tools in the toolbox and determine which ones might relevant and useful for addressing the query. Make sure to consider the user metadata for each tool, including limitations and potential applications (if available).
5. Provide a brief explanation for each skill and tool you've identified, describing how it would contribute to answering the query.

Your response should include:
1. A concise summary of the query's main points and objectives, as well as content in any accompanying inputs.
2. A list of required skills, with a brief explanation for each.
3. A list of relevant tools from the toolbox, with a brief explanation of how each tool would be utilized and its potential limitations.
4. Any additional considerations that might be important for addressing the query effectively.

Please present your analysis in a clear, structured format.
"""
        client = AsyncOpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))
        images_b64content = []
        for image_path in message.images:
            with open(image_path, "rb") as image_file:
                images_b64content.append(image_file.read())
        images_part = [{"type": "input_image", "image_url": f"data:image/png;base64,{b64_image}"} for b64_image in images_b64content]
        
        input=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": query_prompt},
                ]+images_part,
            }]
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=input,
            response_format=QueryAnalysisLLMResponse)
        llm_response = completion.choices[0].message.parsed
        
        logger.debug(f"LLM response: {llm_response}")
        return llm_response
        
        
           

        
        
    
    
    
class Orchestrator(BaseAgent):
    def __init__(self, manager:"Manager"):
        super(self.__class__, self).__init__("OrchestratorAgent")
        logger.debug(f"Orchestrator initialized. {str(self)} {self.id}")
        
        self._manager = manager
    
    async def on_message_impl(self, message:"UserRequest", ctx: MessageContext)->None:
        session_id = None
        if not ctx.topic_id is None:
            session_id = ctx.topic_id.source
        logger.debug(f"Orchestrator {self.id} received message: {message} with topic id: {session_id}")
        query_analysis = await self.query_analyze(message, session_id)
        step_no = 0
        actions_history = []
        while step_no < message.max_steps:
            step_no += 1
            action_predictor_request = ActionPredictorRequest(
                initial_query=message.message,
                image_paths=message.files,
                query_analysis=query_analysis,
                step_count=step_no,
                max_step_count=message.max_steps,
                aviailable_tools=list(self._manager.get_tool_cards().keys()),
                aviailable_tools_metadata=[tool.description for tool in self._manager.get_tool_cards().values()],
                actions_history=actions_history
            )
            action_predictor_response = await self.send_message(action_predictor_request, AgentId(type="ActionPredictor", key=session_id))
                
        
        
    async def query_analyze(self,message:"UserRequest", session_id:str)->None:
        all_tools = self._manager.get_tool_cards()
        all_tools_names = list(all_tools.keys())
        all_tools_description = [tool.description for tool in all_tools.values()]
        qar = QueryAnalyzerRequest(user_query=message.message, images=message.files, all_tools_names=all_tools_names, all_tools_description=all_tools_description)
        response = await self.send_message(qar, AgentId(type="QueryAnalyzer", key=session_id))
        
    


        
        
        
class ActionPredictor(BaseAgent):
    def __init__(self):
        super().__init__("ActionPredictor")
        logger.debug(f"ActionPredictor initialized. {str(self)} {self.id}")
    @only_direct
    async def on_message_impl(self, message:ActionPredictorRequest, ctx: MessageContext)->None:
        logger.debug(f"ActionPredictor {self.id} received UserRequest message: {message}")
        return await self.predict(message)
    
    async def predict(self, message:ActionPredictorRequest)->str:
        query_prompt = f"""
Task: Determine the optimal next step to address the given query based on the provided analysis, available tools, and previous steps taken.

Context:
Query: {message.initial_query}
Image: {",".join(message.image_paths)}
Query Analysis: {message.query_analysis}

Available Tools:
{message.aviailable_tools}

Tool Metadata:
{message.aviailable_tools_metadata}

Previous Steps and Their Results:
{message.actions_history}

Current Step: {message.step_count} in {message.max_step_count} steps
Remaining Steps: {message.max_step_count - message.step_count}

Instructions:
1. Analyze the context thoroughly, including the query, its analysis, any image, available tools and their metadata, and previous steps taken.

2. Determine the most appropriate next step by considering:
   - Key objectives from the query analysis
   - Capabilities of available tools
   - Logical progression of problem-solving
   - Outcomes from previous steps
   - Current step count and remaining steps

3. Select ONE tool best suited for the next step, keeping in mind the limited number of remaining steps.

4. Formulate a specific, achievable sub-goal for the selected tool that maximizes progress towards answering the query.

Output Format:
<justification>: detailed explanation of why the selected tool is the best choice for the next step, considering the context and previous outcomes.
<context>: MUST include ALL necessary information for the tool to function, structured as follows:
    * Relevant data from previous steps
    * File names or paths created or used in previous steps (list EACH ONE individually)
    * Variable names and their values from previous steps' results
    * Any other context-specific information required by the tool
<sub_goal>: a specific, achievable objective for the tool, based on its metadata and previous outcomes. It MUST contain any involved data, file names, and variables from Previous Steps and Their Results that the tool can act upon.
<tool_name>: MUST be the exact name of a tool from the available tools list.

Rules:
- Select only ONE tool for this step.
- The sub-goal MUST directly address the query and be achievable by the selected tool.
- The Context section MUST include ALL necessary information for the tool to function, including ALL relevant file paths, data, and variables from previous steps.
- The tool name MUST exactly match one from the available tools list: {message.aviailable_tools}.
- Avoid redundancy by considering previous steps and building on prior results.

Example (do not copy, use only as reference):
<justification>: [Your detailed explanation here]
<context>: Image path: "example/image.jpg", Previous detection results: [list of objects]
<sub_goal>: Detect and count the number of specific objects in the image "example/image.jpg"
<tool_name>: Object_Detector_Tool
"""
        client = AsyncOpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))
       
        input=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": query_prompt},
                ]
            }]
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=input,
            response_format=NextStepLLMResponse)
        llm_response = completion.choices[0].message.parsed
        
        logger.debug(f"LLM response: {llm_response}")
        return llm_response
        
        

class CommandGenerator(BaseAgent):
    def __init__(self):
        super().__init__("CommandGenerator")
        logger.debug(f"CommandGenerator initialized. {str(self)} {self.id}")
    
    @only_direct        
    async def on_message_impl(self, message:CommandGeneratorRequest, ctx: MessageContext)->None:
        logger.debug(f"CommandGenerator {self.id} received UserRequest message: {message} ")
        return CommangGeneratorResponse(message="CommandGenerator response")
    
    async def generate_command(self, message:CommandGeneratorRequest)->str:
        query_prompt =  f"""
Task: Generate a precise command to execute the selected tool based on the given information.

Query: {message.initial_query}
Image: {",".join(message.image_paths)}
Context: {message.context}
Sub-Goal: {message.sub_goal}
Selected Tool: {message.tool_name}
Tool Metadata: {message.tool_metadata}

Instructions:
1. Carefully review all provided information: the query, image path, context, sub-goal, selected tool, and tool metadata.
2. Analyze the tool's input_types from the metadata to understand required and optional parameters.
3. Construct a command or series of commands that aligns with the tool's usage pattern and addresses the sub-goal.
4. Ensure all required parameters are included and properly formatted.
5. Use appropriate values for parameters based on the given context, particularly the `Context` field which may contain relevant information from previous steps.
6. If multiple steps are needed to prepare data for the tool, include them in the command construction.

Output Format:
<analysis>: a step-by-step analysis of the context, sub-goal, and selected tool to guide the command construction.
<explanation>: a detailed explanation of the constructed command(s) and their parameters.
<command>: the Python code to execute the tool, which can be one of the following types:
    a. A single line command with `execution = tool.execute()`.
    b. A multi-line command with complex data preparation, ending with `execution = tool.execute()`.
    c. Multiple lines of `execution = tool.execute()` calls for processing multiple items.
```python
<your command here>
```

Rules:
1. The command MUST be valid Python code and include at least one call to `tool.execute()`.
2. Each `tool.execute()` call MUST be assigned to the 'execution' variable in the format `execution = tool.execute(...)`.
3. For multiple executions, use separate `execution = tool.execute()` calls for each execution.
4. The final output MUST be assigned to the 'execution' variable, either directly from `tool.execute()` or as a processed form of multiple executions.
5. Use the exact parameter names as specified in the tool's input_types.
6. Enclose string values in quotes, use appropriate data types for other values (e.g., lists, numbers).
7. Do not include any code or text that is not part of the actual command.
8. Ensure the command directly addresses the sub-goal and query.
9. Include ALL required parameters, data, and paths to execute the tool in the command itself.
10. If preparation steps are needed, include them as separate Python statements before the `tool.execute()` calls.

Examples (Not to use directly unless relevant):
xample 1 (Single line command):
<analysis>: The tool requires an image path and a list of labels for object detection.
<explanation>: We pass the image path and a list containing "baseball" as the label to detect.
<command>:
```python
execution = tool.execute(image="path/to/image", labels=["baseball"])
```

Example 2 (Multi-line command with data preparation):
<analysis>: The tool requires an image path, multiple labels, and a threshold for object detection.
<explanation>: We prepare the data by defining variables for the image path, labels, and threshold, then pass these to the tool.execute() function.
<command>:
```python
image = "path/to/image"
labels = ["baseball", "football", "basketball"]
threshold = 0.5
execution = tool.execute(image=image, labels=labels, threshold=threshold)
```

Example 3 (Multiple executions):
<analysis>: We need to process multiple images for baseball detection.
<explanation>: We call the tool for each image path, using the same label and threshold for all.
<command>:
```python
execution = tool.execute(image="path/to/image1", labels=["baseball"], threshold=0.5)
execution = tool.execute(image="path/to/image2", labels=["baseball"], threshold=0.5)
execution = tool.execute(image="path/to/image3", labels=["baseball"], threshold=0.5)
```

Some Wrong Examples:
<command>:
```python
execution1 = tool.execute(query="...")
execution2 = tool.execute(query="...")
```
Reason: only `execution = tool.execute` is allowed, not `execution1` or `execution2`.

<command>:
```python
urls = [
    "https://example.com/article1",
    "https://example.com/article2"
]

execution = tool.execute(url=urls[0])
execution = tool.execute(url=urls[1])
```
Reason: The command should process multiple items in a single execution, not separate executions for each item.

Remember: Your <command> field MUST be valid Python code including any necessary data preparation steps and one or more `execution = tool.execute(` calls, without any additional explanatory text. The format `execution = tool.execute` must be strictly followed, and the last line must begin with `execution = tool.execute` to capture the final output.
"""
    
class CommandExecutor(BaseAgent):
    def __init__(self):
        super().__init__("CommandExecutor")
        logger.debug(f"CommandExecutor initialized. {str(self)} {self.id}")
    @only_direct    
    async def on_message_impl(self, message:Any, ctx: MessageContext)->None:
        logger.debug(f"CommandExecutor {self.id} received  message: {message}")
        return CommandExecutorResponse(message="CommandExecutor response")
    
class ContextVerifier(BaseAgent):
    def __init__(self):
        super().__init__("ContextVerifier")
        logger.debug(f"ContextVerifier initialized. {str(self)} {self.id}")
    @only_direct        
    async def on_message_impl(self, message:Any, ctx: MessageContext)->None:
        logger.debug(f"ContextVerifier {self.id} received message: {message} ")
        return ContextVerifierResponse(message="ContextVerifier response")

        