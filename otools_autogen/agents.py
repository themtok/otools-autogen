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

import json

from .tools import ToolCard, Tool





from .utils import only_direct, logger, llm_logger


if TYPE_CHECKING:
    from .manager_v2 import Manager, UserRequest, UserResponse
    
    
@dataclass
class QueryAnalyzerRequest():
    user_query: str
    images: list[str]
    image_infos: list[Dict[str, Any]]
    all_tools_names: list[str]
    all_tools_medatada: list[str]


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
class CommandGeneratorRequest():
    initial_query: str
    image_paths: list[str]
    query_analysis: str
    sub_goal: str
    tool_name: str
    tool_metadata: str
    context: str


    

@dataclass
class ContextVerifierRequest():
    question: str
    image_info: str
    available_tools: list[str]
    toolbox_metadata: list[str]
    query_analysis: str
    memory: str
    image_paths: list[str]

@dataclass
class FinalOutputRequest():
    question: str
    image_info: list[str]
    memory: str
    image_paths: list[str]
    query_analysis: str

    
    
    

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

class ToolCommandLLMResponse(BaseModel):
    analysis: str
    explanation: str
    argument: str

class ActionPredictonLLMResponse(BaseModel):
    justification: str
    context: str
    sub_goal: str
    tool_name: str    
    
class ContextVerifierLLMResponse(BaseModel):
    analysis: str
    stop_signal: bool

def get_image_info(image_path: str) -> Dict[str, Any]:
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



    
    
class Orchestrator(BaseAgent):
    def __init__(self, manager:"Manager"):
        super(self.__class__, self).__init__("OrchestratorAgent")
        logger.debug(f"Orchestrator initialized. {str(self)} {self.id}")
        
        self._manager = manager
        
    
    
    async def on_message_impl(self, message:"UserRequest", ctx: MessageContext)->None:
        if message=="bootstrap": return
        from .manager_v2 import UserResponse
        session_id = None
        if not ctx.topic_id is None:
            session_id = ctx.topic_id.source
        to_client_queue = self._manager.get_session(ctx.topic_id.source).to_client_queue

        logger.debug(f"Orchestrator {self.id} received message: {message} with topic id: {session_id}")
        image_infos = [get_image_info(image_path) for image_path in message.files]
        all_tools = self._manager.get_tool_cards()
        all_tools_names = list(all_tools.keys())
        all_tools_metadata = [tool.get_metadata() for tool in all_tools.values()]
        qar = QueryAnalyzerRequest(
            user_query=message.message, 
            images=message.files, 
            image_infos=image_infos,
            all_tools_names=all_tools_names, 
            all_tools_medatada=all_tools_metadata
            )
        query_analysis:QueryAnalysisLLMResponse = await self.send_message(qar, AgentId(type="QueryAnalyzer", key=session_id))

        step_no = 0
        actions_history = {}
        conclusion = False
        while step_no < message.max_steps:
            step_no += 1
            action_predictor_request = ActionPredictorRequest(
                initial_query=message.message,
                image_paths=message.files,
                query_analysis=query_analysis,
                step_count=step_no,
                max_step_count=message.max_steps,
                aviailable_tools=list(self._manager.get_tool_cards().keys()),
                aviailable_tools_metadata=[tool.get_metadata() for tool in self._manager.get_tool_cards().values()],
                actions_history=actions_history
            )
            action_predictor_response:ActionPredictonLLMResponse = await self.send_message(action_predictor_request, AgentId(type="ActionPredictor", key=session_id))
            selected_tool_card:ToolCard = self._manager.get_tool_cards()[action_predictor_response.tool_name]
            selected_tool_id = selected_tool_card.tool_id
            selected_tool_metadata = selected_tool_card.get_metadata()
            cgr = CommandGeneratorRequest(
                initial_query=message.message,
                query_analysis=query_analysis,
                context=action_predictor_response.context,
                sub_goal=action_predictor_response.sub_goal,
                tool_name=action_predictor_response.tool_name,
                tool_metadata=selected_tool_metadata,
                image_paths=message.files
            )
            command_response:ToolCommandLLMResponse = await self.send_message(cgr, AgentId(type="CommandGenerator", key=session_id))
            try:
                parsed_arg = json.loads(command_response.argument)
                invocation_arg = selected_tool_card.inputs.model_validate(parsed_arg)
                tool_result = await self.send_message(invocation_arg, AgentId(type=selected_tool_id, key=session_id))
                to_client_queue.put_nowait(UserResponse(
                    session_id=session_id, 
                    message=action_predictor_response.sub_goal, 
                    command=command_response.argument,
                    tool_used=selected_tool_id, 
                    final=False,
                    conclusion=False,
                    step_no=step_no
                    ))
                actions_history[f"Step {step_no}"] = {
                    "tool_name": action_predictor_response.tool_name,
                    "sub_goal": action_predictor_response.sub_goal,
                    "argument": command_response.argument,
                    "result": tool_result
                }
            except Exception as e:
                actions_history[f"Step {step_no}"] = {
                    "tool_name": action_predictor_response.tool_name,
                    "sub_goal": action_predictor_response.sub_goal,
                    "argument": command_response.argument,
                    "result": f"Error executing tool: {str(e)}"
                }
                to_client_queue.put_nowait(UserResponse(
                    session_id=session_id, 
                    message=f"Error executing tool: {str(e)}", 
                    tool_used=selected_tool_id, 
                    command=command_response.argument,
                    final=False,
                    conclusion=False,
                    step_no=step_no))
                continue
                
            
            cvr = ContextVerifierRequest(
                image_paths=message.files,
                question=message.message,
                image_info=image_infos,
                available_tools=all_tools_names,
                toolbox_metadata=all_tools_metadata,
                query_analysis=query_analysis,
                memory=actions_history
            )
            context_verifier_result = await self.send_message(cvr, AgentId(type="ContextVerifier", key=session_id))
            if context_verifier_result.stop_signal:
                conclusion = True
                break
        final_output_request = FinalOutputRequest(
            question=message.message,
            image_info=image_infos,
            memory=actions_history,
            image_paths=message.files,
            query_analysis=query_analysis
        )
        final_output = await self.send_message(final_output_request, AgentId(type="FinalOutputAgent", key=session_id)) 
        to_client_queue.put_nowait(UserResponse(
            session_id=session_id, 
            message=final_output, 
            tool_used=None, 
            final=True,
            conclusion=conclusion,
            step_no=step_no))         

            
            
class QueryAnalyzer(BaseAgent):
    def __init__(self):
        super().__init__("QueryAnalyzer")
        logger.debug(f"QueryAnalyzer initialized. {str(self)} {self.id}")
        
    @only_direct
    async def on_message_impl(self, message:QueryAnalyzerRequest, ctx: MessageContext)->None:
        logger.debug(f"QueryAnalyzer {self.id} received message: {message}")
        return await self.analyze(message)
    
    async def analyze(self, message:QueryAnalyzerRequest)->QueryAnalysisLLMResponse:
        question = message.user_query
        image_infos_str = "\n".join([f"Image: {info['image_path']}, Width: {info['width']}, Height: {info['height']}" for info in message.image_infos])
        query_prompt = f"""
Task: Analyze the given query with accompanying inputs and determine the skills and tools needed to address it effectively.

Available tools: {message.all_tools_names}

Metadata for the tools: {message.all_tools_medatada}

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
        llm_logger.debug(f"[QueryAnalyzer] LLM prompt: {query_prompt}")

        client = AsyncOpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url=os.getenv("OPENROUTER_BASE_PATH"))
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
        
        llm_logger.debug(f"[QueryAnalyzer] LLM response: {llm_response}")
        return llm_response
        
        
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
        llm_logger.debug(f"[ActionPredictor] LLM prompt: {query_prompt}")
        client = AsyncOpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url=os.getenv("OPENROUTER_BASE_PATH"))
       
        input=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": query_prompt},
                ]
            }]
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=input,
            response_format=ActionPredictonLLMResponse)
        llm_response = completion.choices[0].message.parsed
        
        llm_logger.debug(f"[ActionPredictor] LLM response: {llm_response}")
        
        return llm_response
        
        

class CommandGenerator(BaseAgent):
    def __init__(self):
        super().__init__("CommandGenerator")
        logger.debug(f"CommandGenerator initialized. {str(self)} {self.id}")
    
    @only_direct        
    async def on_message_impl(self, message:CommandGeneratorRequest, ctx: MessageContext)->None:
        logger.debug(f"CommandGenerator {self.id} received UserRequest message: {message} ")
        return await self.generate_command(message)
    
    async def generate_command(self, message:CommandGeneratorRequest)->str:
        query_prompt =  f"""
Task: Generate a precise argument to execute the selected tool based on the given information.

Query: {message.initial_query}
Image: {",".join(message.image_paths)}
Context: {message.context}
Sub-Goal: {message.sub_goal}
Selected Tool: {message.tool_name}
Tool Metadata: {message.tool_metadata}

Instructions:
1. Carefully review all provided information: the query, image path, context, sub-goal, selected tool, and tool metadata.
2. Analyze the tool's input_type_json_schema from the metadata to understand required and optional parameters.
3. Construct a argument for tool execution aligns with the tool's usage pattern and addresses the sub-goal.
4. Ensure all required parameters are included and properly formatted.
5. Use appropriate values for parameters based on the given context, particularly the `Context` field which may contain relevant information from previous steps.

Output Format:
<analysis>: a step-by-step analysis of the context, sub-goal, and selected tool to guide the argument construction.
<explanation>: a detailed explanation of the constructed argument and their parameters.
<argument>: the json object that should be used to execute the tool, which can be one of the following types:
    
```json
<your argument here>
```

Rules:
1. The argument MUST be signle valid json object.
2. Use the exact fileds names as specified in the tool's input_types_json_schema.
3. Enclose string values in quotes, use appropriate data types for other values (e.g., lists, numbers).
4. Do not include any code, json objects or text that is not part of the actual argument.
5. Ensure the argument directly addresses the sub-goal and query.
6. Include ALL required parameters, data, and paths to execute the tool in the argument itself.

Examples (Not to use directly unless relevant):
Example 1:
<analysis>: The tool requires an image path and a list of labels for object detection.
<explanation>: We pass the image path and a list containing "baseball" as the label to detect.
<argument>:
```json
{{"image":"path/to/image", labels:["baseball"])}}
```

Example 2:
<analysis>: The tool requires and name and surname of user together with his age.
<explanation>: We pass name and surname of user together with his age in argument .
<argument>:
```json
{{"image":"path/to/image", labels:["baseball"])}}
```




Some Wrong Examples:
<argument>:
```json
not a valid json //
```
Reason: not a valid json object.

<argument>:
```json
{{"image":"path/to/image"}}
{{"labels":["baseball"]}}
```
Reason: Multiple json objects are not allowed.

Remember: Your <argument> field MUST be valid json object"""
        llm_logger.debug(f"[CommandGenerator] LLM prompt: {query_prompt}")
        client = AsyncOpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url=os.getenv("OPENROUTER_BASE_PATH"))
       
        input=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": query_prompt},
                ]
            }]
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=input,
            response_format=ToolCommandLLMResponse)
        llm_response = completion.choices[0].message.parsed
        llm_logger.debug(f"[CommandGenerator] LLM response: {llm_response}")
        
        logger.debug(f"LLM response: {llm_response}")
        return llm_response
    
    
class ContextVerifier(BaseAgent):
    def __init__(self):
        super().__init__("ContextVerifier")
        logger.debug(f"ContextVerifier initialized. {str(self)} {self.id}")
    
    
    @only_direct        
    async def on_message_impl(self, message:ContextVerifierRequest, ctx: MessageContext)->None:
        logger.debug(f"ContextVerifier {self.id} received message: {message} ")
        return await self.verify(message)
    
    async def verify(self, message:ContextVerifierRequest)->str:
        query_prompt =  f"""
Task: Thoroughly evaluate the completeness and accuracy of the memory for fulfilling the given query, considering the potential need for additional tool usage.

Context:
Query: {message.question}
Image: {message.image_info}
Available Tools: {message.available_tools}
Toolbox Metadata: {message.toolbox_metadata}
Initial Analysis: {message.query_analysis}
Memory (tools used and results): {message.memory}

Detailed Instructions:
1. Carefully analyze the query, initial analysis, and image (if provided):
   - Identify the main objectives of the query.
   - Note any specific requirements or constraints mentioned.
   - If an image is provided, consider its relevance and what information it contributes.

2. Review the available tools and their metadata:
   - Understand the capabilities and limitations and best practices of each tool.
   - Consider how each tool might be applicable to the query.

3. Examine the memory content in detail:
   - Review each tool used and its execution results.
   - Assess how well each tool's output contributes to answering the query.

4. Critical Evaluation (address each point explicitly):
   a) Completeness: Does the memory fully address all aspects of the query?
      - Identify any parts of the query that remain unanswered.
      - Consider if all relevant information has been extracted from the image (if applicable).

   b) Unused Tools: Are there any unused tools that could provide additional relevant information?
      - Specify which unused tools might be helpful and why.

   c) Inconsistencies: Are there any contradictions or conflicts in the information provided?
      - If yes, explain the inconsistencies and suggest how they might be resolved.

   d) Verification Needs: Is there any information that requires further verification due to tool limitations?
      - Identify specific pieces of information that need verification and explain why.

   e) Ambiguities: Are there any unclear or ambiguous results that could be clarified by using another tool?
      - Point out specific ambiguities and suggest which tools could help clarify them.

5. Final Determination:
   Based on your thorough analysis, decide if the memory is complete and accurate enough to generate the final output, or if additional tool usage is necessary.

Response Format:
<analysis>: Provide a detailed analysis of why the memory is sufficient. Reference specific information from the memory and explain its relevance to each aspect of the task. Address how each main point of the query has been satisfied.
<stop_signal>: Whether to stop the problem solving process and proceed to generating the final output.
    * "True": if the memory is sufficient for addressing the query to proceed and no additional available tools need to be used. If ONLY manual verification without tools is needed, choose "True".
    * "False": if the memory is insufficient and needs more information from additional tool usage.
"""
        client = AsyncOpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url=os.getenv("OPENROUTER_BASE_PATH"))
        images_b64content = []
        for image_path in message.image_paths:
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
            response_format=ContextVerifierLLMResponse)
        llm_response = completion.choices[0].message.parsed
        
        llm_logger.debug(f"[ContextVerifier] LLM response: {llm_response}")
        return llm_response

class FinalOutputAgent(BaseAgent):
    def __init__(self):
        super().__init__("FinalOutputAgent")
        logger.debug(f"FinalOutputAgent initialized. {str(self)} {self.id}")
    
    
    @only_direct        
    async def on_message_impl(self, message:FinalOutputRequest, ctx: MessageContext)->None:
        logger.debug(f"FinalOutputAgent {self.id} received message: {message} ")
        return await self.generate(message)
    
    
    async def generate(self, message:FinalOutputRequest)->str:
        query_prompt =  f"""Task: Generate the final output based on the query, image, and tools used in the process.

Context:
Query: {message.question}
Image: {message.image_info}
Actions Taken:
{message.memory}

Instructions:
1. Review the query, image, and all actions taken during the process.
2. Consider the results obtained from each tool execution.
3. Incorporate the relevant information from the memory to generate the step-by-step final output.
4. The final output should be consistent and coherent using the results from the tools.

Output Structure:
Your response should be well-organized and include the following sections:

1. Summary:
   - Provide a brief overview of the query and the main findings.

2. Detailed Analysis:
   - Break down the process of answering the query step-by-step.
   - For each step, mention the tool used, its purpose, and the key results obtained.
   - Explain how each step contributed to addressing the query.

3. Key Findings:
   - List the most important discoveries or insights gained from the analysis.
   - Highlight any unexpected or particularly interesting results.

4. Answer to the Query:
   - Directly address the original question with a clear and concise answer.
   - If the query has multiple parts, ensure each part is answered separately.

5. Additional Insights (if applicable):
   - Provide any relevant information or insights that go beyond the direct answer to the query.
   - Discuss any limitations or areas of uncertainty in the analysis.

6. Conclusion:
   - Summarize the main points and reinforce the answer to the query.
   - If appropriate, suggest potential next steps or areas for further investigation."""
        prompt_generate_final_output = f"""
Context:
Query: {message.question}   
Image: {message.image_info}
Initial Analysis:
{message.query_analysis}
Actions Taken:
{message.memory}

Please generate the concise output based on the query, image information, initial analysis, and actions taken. Break down the process into clear, logical, and conherent steps. Conclude with a precise and direct answer to the query.

Answer:
"""
   
        llm_logger.debug(f"[FinalOutputAgent] LLM prompt: {prompt_generate_final_output}")
        client = AsyncOpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url=os.getenv("OPENROUTER_BASE_PATH"))
        images_b64content = []
        for image_path in message.image_paths:
            with open(image_path, "rb") as image_file:
                images_b64content.append(image_file.read())
        images_part = [{"type": "input_image", "image_url": f"data:image/png;base64,{b64_image}"} for b64_image in images_b64content]
        
        input=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_generate_final_output},
                ]+images_part,
            }]
        completion = await client.chat.completions.create(
            model="gpt-4o",
            messages=input)
        llm_response = completion.choices[0].message.content
        
        llm_logger.debug(f"[FinalOutputAgent] LLM response: {llm_response}")
        return llm_response