import asyncio
from pydantic import BaseModel
from otools_autogen.manager_v2 import Manager, ToolCard, UserRequest, Tool, UserResponse
from dotenv import load_dotenv
from colorama import Fore, Back, Style
import wikipedia
load_dotenv()


class WikipediaSearchRequest(BaseModel):
    query: str
    max_length_of_response:int=2000
    
class WikipediaSearchResponse(BaseModel):
    success: bool
    search_results: str
    

class WikipediaSearch(Tool):
        @property
        def card(self) -> ToolCard:
            return ToolCard(
                tool_id="WikipediaSearchTool",
                name="Wikipedia search tool",
                description="Tool for searching wikipedia.",
                inputs=WikipediaSearchRequest,
                outputs=WikipediaSearchResponse,
                user_metadata={},
                demo_input=[WikipediaSearchRequest(
                    query="Python"
                ), WikipediaSearchRequest(
                    query="Washington"
                )])
            
        async def run(self, inputs: WikipediaSearchRequest) -> WikipediaSearchResponse:
            search_results = wikipedia.search(inputs.query)
            if not search_results:
                return WikipediaSearchResponse(success=False, search_results=None)
            page = wikipedia.page(search_results[0])
            text = page.content

            if inputs.max_length_of_response is not None:
                text = text[:inputs.max_length_of_response]
            return WikipediaSearchResponse(success=True, search_results=text) 
        
        
        
async def m():
        m = Manager()
        class DietPlanningTool(Tool):
            class DietPlanningToolInput(BaseModel):
                age: int
                weight: float
                gender: str
                height: float
                activity_level: str
                health_condition: str
                deaseases: str
                
            class DietPlanningToolOutput(BaseModel):
                diet_plan: str
            @property
            def card(self) -> ToolCard:
                return ToolCard(
                    tool_id="DietComposerTool",
                    name="Diet composer tool",
                    description="Tool for composing a diet. It is able to generate a diet based on the user's preferences.",
                    inputs=DietPlanningTool.DietPlanningToolInput,
                    outputs=DietPlanningTool.DietPlanningToolOutput,
                    user_metadata={},
                    demo_input=[DietPlanningTool.DietPlanningToolInput(
                            age=30,
                            weight=70.5,
                            gender="male",
                            height=175.0,
                            activity_level="moderate",
                            health_condition="good",
                            deaseases="none"
                        ), DietPlanningTool.DietPlanningToolInput(
                           age=50,  
                            weight=121.5,
                            gender="male",
                            height=203.0,
                            activity_level="low",
                            health_condition="moderate",
                            deaseases="diabetes"
                        )]
                                
                        
                )

            async def run(self, inputs: DietPlanningToolInput) -> BaseModel:
                print(f"Running MyTool with input: {inputs}")
                diet_plan_for_diabetic = """
                Breakfast: 1 cup of oatmeal with 1/2 cup of blueberries and 1/4 cup of walnuts
                Snack: 1 medium apple
                Lunch: 1 cup of vegetable soup with 1/2 turkey sandwich on whole wheat bread
                Snack: 1/4 cup of almonds
                Dinner: 4 oz of grilled salmon with 1 cup of quinoa and 1 cup of steamed broccoli
                Day2 - Breakfast: 1 cup of Greek yogurt with 1/2 cup of strawberries and 1/4 cup of granola
                Snack: 1 medium orange
                Lunch: 1 cup of lentil soup with 1/2 turkey sandwich on whole wheat bread
                Snack: 1/4 cup of cashews
                Dinner: 4 oz of grilled chicken with 1 cup of brown rice and 1 cup of steamed asparagus
                Day3 - Breakfast: 1 cup of cottage cheese with 1/2 cup of pineapple and 1/4 cup of almonds
                Snack: 1 medium pear
                Lunch: 1 cup of minestrone soup with 1/2 turkey sandwich on whole wheat bread
                Snack: 1/4 cup of peanuts
                Dinner: 4 oz of grilled shrimp with 1 cup of quinoa and 1 cup of steamed green beans
                Day4 - Breakfast: 1 cup of oatmeal with 1/2 cup of blueberries and 1/4 cup of walnuts
                Snack: 1 medium apple
                Lunch: 1 cup of vegetable soup with 1/2 turkey sandwich on whole wheat bread
                Snack: 1/4 cup of almonds
                Dinner: 4 oz of grilled salmon with 1 cup of quinoa and 1 cup of steamed broccoli
                Day5 - Breakfast: 1 cup of Greek yogurt with 1/2 cup of strawberries and 1/4 cup of granola
                Snack: 1 medium orange
                Lunch: 1 cup of lentil soup with 1/2 turkey sandwich on whole wheat bread
                Snack: 1/4 cup of cashews
                Dinner: 4 oz of grilled chicken with 1 cup of brown rice and 1 cup of steamed asparagus
                Day6 - Breakfast: 1 cup of cottage cheese with 1/2 cup of pineapple and 1/4 cup of almonds
                Snack: 1 medium pear
                Lunch: 1 cup of minestrone soup with 1/2 turkey sandwich on whole wheat bread
                Snack: 1/4 cup of peanuts
                Dinner: 4 oz of grilled shrimp with 1 cup of quinoa and 1 cup of steamed green beans
                Day7 - Breakfast: 1 cup of oatmeal with 1/2 cup of blueberries and 1/4 cup of walnuts
                Snack: 1 medium apple
                Lunch: 1 cup of vegetable soup with 1/2 turkey sandwich on whole wheat bread
                Snack: 1/4 cup of almonds
                Dinner: 4 oz of grilled salmon with 1 cup of quinoa and 1 cup of steamed broccoli
                """
                return DietPlanningTool.DietPlanningToolOutput(diet_plan=diet_plan_for_diabetic)
        
        m.register_tool("DietComposerTool", DietPlanningTool)
        m.register_tool("WikipediaSearchTool", WikipediaSearch)

        
        
        await m.start()
        print("Manager started.")
        sid = await m.send_message(UserRequest(message="What happened on 11.09.2001", files=[]))
        print(f"---------------Session id: {sid}")
        async for msg in m.stream(sid):
            mm:UserResponse = msg
            print(Fore.GREEN + f"Response message: {mm.message}" + Style.RESET_ALL)
            print(Fore.BLUE + f"Response tool_used: {mm.tool_used}" + Style.RESET_ALL)
            print(Fore.RED + f"Response final: {mm.final}" + Style.RESET_ALL)

            

        # sid2 = await m.send_message(UserRequest(message="Hello", files=["file1", "file2"]))
        # print(f"----------------Session id: {sid2}")
        # await m.send_message(UserRequest2(message="Hello2", files=["file1", "file2"]), session_id=sid2)
        # await m.send_message(message="dupa", session_id=sid2)
        
        await m.stop(True)



asyncio.run(m())