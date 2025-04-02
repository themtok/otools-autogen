from pydantic import BaseModel, Field
from otools_autogen.tools import Tool, ToolCard
import json
from duckduckgo_search import DDGS
import trafilatura


class PageContentExtractionRequest(BaseModel):
    link: str = Field(None, description="Link to the page to extract content from")
    
class PageContentExtractionResult(BaseModel):
    success: bool = Field(description="If page content extraction was successful this will be True")
    markdown_content: str= Field(None, description="Extracted content in markdown format")
    
    
tool_card= ToolCard(
                tool_id="PageContentExtractionTool",
                description="Tool for extracting content from the page. Returns content in markdown format. Is able to accept only one link at a time.",
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
        if downloaded is None:
            return PageContentExtractionResult.model_validate({
                "success": False,
                "markdown_content": None
            })
        r = trafilatura.extract(downloaded,output_format="markdown")
        if r is None:
            return PageContentExtractionResult.model_validate({
                "success": False,
                "markdown_content": None
            })
        return PageContentExtractionResult.model_validate({
            "success": True,
            "markdown_content": r
        })
        
if __name__ == "__main__":
    async def m():
        tool = PageContentExtractionTool()
        r= await tool.run(PageContentExtractionRequest(link="https://news.google.com/read/CBMicEFVX3lxTFBtcUowRUt6QXZKRzZ4RktCcWlBcFRTbkVHSDFzWV94aG5NdFgxQVFmSVhCWHBSMXY4dWJaSFA3by0tb1dqcVZ3MWFIRDd0TWF3LXRaWWlndW0tZ1cwdVBpb3dIOTVEMk45Qk9XakVGRnA?hl=en-US&gl=US&ceid=US%3Aen"))
        print(r)
    import asyncio
    asyncio.run(m())
    
    