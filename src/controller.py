import ast
import json
import uuid
import uvicorn
from itertools import chain
from dataclasses import dataclass, field
from string import ascii_letters, digits, punctuation

from app import *
from langchain_core.prompts import ChatPromptTemplate
# from prompts import PROMPT_CHECK_MAKING_VIDEO, PROMPT_GET_MEMORY
from langchain_core.messages import HumanMessage, SystemMessage
from models import InputUrl, InputGen, Status

@app.post("/api/getData")
@HTTPException() 
async def getData(inputs: InputUrl = Body(...)):
    result = await VG.get_data(sess_id=inputs.sess_id, url=inputs.url)
    VG.update_status(inputs.sess_id, "data", str(datetime.datetime.now()), result, 100, "done")
    if not result["success"]:
        VG.update_status(inputs.sess_id, "data", str(datetime.datetime.now()), result, 0, "error")
        return JSONResponse(status_code=500, content=result["error"])
    return JSONResponse(status_code=201, content=result)

@app.post("/api/createVideo")
@HTTPException() 
async def createVideo(inputs: InputGen = Body(...)):
    print(inputs)
    result = await VG.run(inputs.sess_id, inputs.title, ast.literal_eval(inputs.descriptions), ast.literal_eval(inputs.image_paths))
    VG.update_status(inputs.sess_id, "video", str(datetime.datetime.now()), result, 100, "done")
    if not result["success"]:
        VG.update_status(inputs.sess_id, "video", str(datetime.datetime.now()), result, 0, "error")
        return JSONResponse(status_code=500, content=result["error"])
    return JSONResponse(status_code=201, content=result)

@app.post("/api/getStatus")
@HTTPException() 
async def getStatus(inputs: Status = Body(...)):
    result = VG.get_status(session_id=inputs.sess_id, type=inputs.type)
    if not result["success"]:
        return JSONResponse(status_code=500, content=result["error"])
    return JSONResponse(status_code=200, content=result['result'])
    
if __name__=="__main__":
    host = "0.0.0.0"
    port = 8387
    uvicorn.run("controller:app", host=host, port=port, log_level="info", reload=False)
    
    
    
"""
1xx: Informational
100	Continue	Server received the request headers.
101	Switching Protocols	Protocol switch is accepted (rare).

2xx: Success
200	OK	Request succeeded, and response returned.
201	Created	New resource was successfully created.
202	Accepted	Request accepted, processing later.
204	No Content	Request succeeded, but no content to return.

3xx: Redirection
301	Moved Permanently	Resource has a new permanent URI.
302	Found (Redirect)	Resource temporarily moved.
304	Not Modified	Client's cached version is still valid.

4xx: Client Errors
400	Bad Request	Malformed syntax or invalid parameters.
401	Unauthorized	Missing or invalid authentication.
403	Forbidden	Authenticated, but no permission.
404	Not Found	Resource not found.
405	Method Not Allowed	Method not allowed for this endpoint.
409	Conflict	Conflict in request (e.g., duplicate).
422	Unprocessable Entity	Semantic error in request (e.g., FastAPI validation).

5xx: Server Errors
500	Internal Server Error	Server-side error.
501	Not Implemented	Feature not supported.
503	Service Unavailable	Server is down or overloaded.
"""