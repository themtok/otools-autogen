from pydantic import BaseModel, Field
from otools_autogen.tools import Tool, ToolCard
import json
import urllib.request


class NewsFetchToolRequest(BaseModel):
    sections: list[str] = Field(None, description="sections to fetch news from, aviailable sections: US, World, Business, Technology, Entertainment, Sports, Science, Health")
    
class NewsFeedItem(BaseModel):
    title: str= Field(None, description="article title")
    link: str= Field(None, description="article URL")
    og: str= Field(None, description="og:image URL")
    source: str   = Field(None, description="name of news source" )
    source_icon: str = Field(None, description="source logo/icon URL")
    
class NewsFetchToolResponse(BaseModel):
    success: bool
    search_results: dict[str, list[NewsFeedItem]]= Field(None, description="news feed items")
    
        
tool_card=  ToolCard(
                tool_id="NewsFetchTool",
                name="Tool for ",
                description="Fetch available Google News section names, such as World, Sports, and Science",
                inputs=NewsFetchToolRequest,
                outputs=NewsFetchToolResponse,
                user_metadata={},
                demo_input=[NewsFetchToolRequest(
                    sections= ['World']
                ), NewsFetchToolRequest(
                    sections= ['US', 'World', 'Business', 'Technology']
                )])


class NewsFetchTool(Tool):
    @property
    def card(self) -> ToolCard:
        return tool_card
    
    
    async def run(self, inputs: NewsFetchToolRequest) -> NewsFetchToolResponse:
        url = "https://ok.surf/api/v1/news-section"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "sections": inputs.sections
        }
        json_data = json.dumps(data).encode("utf-8")
        request = urllib.request.Request(url, data=json_data, headers=headers, method="POST")
        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")
            response_dict = json.loads(response_body)
            r = {
                "success": True,
                "search_results": response_dict
            }
            return NewsFetchToolResponse.model_validate(r)
    
    
if __name__ == "__main__":
    import asyncio
    async def f():
        t= NewsFetchTool()
        print(await t.run(NewsFetchToolRequest(sections=["World", "US", "Technology"])))
    asyncio.run(f())