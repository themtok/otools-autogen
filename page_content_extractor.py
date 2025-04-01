from pydantic import BaseModel, Field
from otools_autogen.tools import Tool, ToolCard
import json
from duckduckgo_search import DDGS
import trafilatura


class PageContentExtractionRequest(BaseModel):
    link: str = Field(None, description="Link to the page to extract content from")
    
class PageContentExtractionResult(BaseModel):
    markdown_content: str= Field(None, description="Extracted content in markdown format")
    
    
tool_card= ToolCard(
                tool_id="PageContentExtractionTool",
                description="Tool for extracting content from the page. Returns content in markdown format.",
                name="Page Content Extraction",
                inputs=PageContentExtractionRequest,
                outputs=PageContentExtractionResult,
                user_metadata={},
                demo_input=[
                    PageContentExtractionRequest(link="https://en.wikipedia.org/wiki/Python_(programming_language)"),
                    PageContentExtractionRequest(link="https://www.python.org/")          
                ])

class PageContentExtractionTool(Tool):
    @property
    def card(self) -> ToolCard:
        return tool_card
    
    
    async def run(self, inputs: PageContentExtractionRequest) -> PageContentExtractionResult:
        import trafilatura
        downloaded = trafilatura.fetch_url(inputs.link)
        r = trafilatura.extract(downloaded,output_format="markdown")
        return PageContentExtractionResult.model_validate({
            "markdown_content": r
        })
        
if __name__ == "__main__":
    async def m():
        tool = PageContentExtractionTool()
        r= await tool.run(PageContentExtractionRequest(link="https://en.wikipedia.org/wiki/Python_(programming_language)"))
        print(r)
    import asyncio
    asyncio.run(m())
    
    