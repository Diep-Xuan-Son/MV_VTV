import jwt
import os
import cv2
import asyncio
import base64
import re as regex
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage


PROMPT_GET_DESCRIPTION = """
The user query: {query}

Doing these tasks below to analyze the scene:
1. Describe the scene content and what makes it engaging. The description is about the topic that the user want to introduce
2. Rate its viral potential (1-10) based on visual appeal and content
3. Suggest a catchy title that captures the scene's essence
4. Suggest relevant hashtags for social media
Format the response as JSON like below: 
{{
    "description_vi": <value of description in vietnamese>, 
    "viralPotential_vi": <value of viralPotential in vietnamese>, 
    "suggestedTitle_vi": <value of suggestedTitle in vietnamese>, 
    "suggestedHashtags_vi": [<list value of suggestedHashtags in vietnamese>]
}}

# RULE
- The respone must be English fields and Vietnamese values of fields
"""

class ImageAnalyzationWorker(object):
    def __init__(self,):
        SECRET_KEY  = os.getenv('SECRET_KEY', "MMV")
        token_gem   = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5IjoiQUl6YVN5Q1BKSHNJYUxXaGdMakllQkZVS3E4VHFrclRFdWhGd2xzIn0.7iN_1kRmOahYrT7i5FUplOYeda1s7QhYzk-D-AlgWgE'
        api_key_gem = jwt.decode(token_gem, SECRET_KEY, algorithms=["HS256"])["api_key"]

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-001",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            # other params...
            api_key=api_key_gem,
        )

    async def get_description(self, query: str, image_path: str):
        image = cv2.imread(image_path)
        _, buffer = cv2.imencode('.png', image)
        base64Image = base64.b64encode(buffer).decode('utf-8')

        prompt = PROMPT_GET_DESCRIPTION
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a marketing expert that analyze the scene and identify potential viral moment. The scene represents a significant scene change or important moment."),
            HumanMessage(content=[{"type":"text", "text":prompt.format(query=query)}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64Image}"}}])
        ])

        chain = prompt | self.llm 
        response = await chain.ainvoke({})
        pattern = r'{.*}'
        clean_answer = regex.findall(pattern, response.content.replace("```", "").strip(), regex.DOTALL)
        if isinstance(clean_answer, list):
            if len(clean_answer):
                clean_answer = clean_answer[0]
            else:
                clean_answer = '{"description_vi": ""}'
        result = eval(clean_answer)
        return result

if __name__=="__main__":
    IAW = ImageAnalyzationWorker()
    query = "Chuyện một doanh nhân đưa trà Việt sang Paris"
    image_path = "./data_test/uong-tra.jpg"

    result = asyncio.run(IAW.get_description(query, image_path))
    print(result)