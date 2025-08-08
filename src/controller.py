import ast
import json
import uuid
import uvicorn
import re as regex
from itertools import chain
from datetime import datetime
from dataclasses import dataclass, field
from string import ascii_letters, digits, punctuation

from app import *
from langchain_core.prompts import ChatPromptTemplate
# from prompts import PROMPT_CHECK_MAKING_VIDEO, PROMPT_GET_MEMORY
from langchain_core.messages import HumanMessage, SystemMessage
from models import InputUrl, InputGen, Status

from libs.utils import logging, formatter
LOGGER = logging.getLogger("controller")
FILE_HANDLER = logging.FileHandler(f"{Config.PATH_LOG}{os.sep}controller_{datetime.now().strftime('%Y_%m_%d')}.log")
FILE_HANDLER.setFormatter(formatter)
LOGGER.addHandler(FILE_HANDLER)

@app.post("/api/getData")
@HTTPException() 
async def getData(inputs: InputUrl = Body(...)):
    urls = regex.findall(r'https?://[^\s]+', inputs.url)
    url = urls[-1] if urls else None
    result = await MULTIW.VG.get_data(sess_id=inputs.sess_id, url=url)
    VG.dataw.update_status(inputs.sess_id, "data", str(datetime.now()), result, 100, "done")
    if not result["success"]:
        VG.dataw.update_status(inputs.sess_id, "data", str(datetime.now()), result, 0, "error")
        return JSONResponse(status_code=500, content=result["error"])
    return JSONResponse(status_code=201, content=result)

@app.post("/api/createVideo")
@HTTPException() 
async def createVideo(inputs: InputGen = Body(...)):
    LOGGER.info(inputs)
    result = await MULTIW.VG.run(inputs.sess_id, inputs.title, ast.literal_eval(inputs.descriptions), ast.literal_eval(inputs.image_paths))
    VG.dataw.update_status(inputs.sess_id, "video", str(datetime.now()), result, 100, "done")
    if not result["success"]:
        VG.dataw.update_status(inputs.sess_id, "video", str(datetime.now()), result, 0, "error")
        return JSONResponse(status_code=500, content=result["error"])
    return JSONResponse(status_code=201, content=result)

@app.post("/api/getDataCache")
@HTTPException() 
async def getData(inputs: InputUrl = Body(...)):
    if MULTIW.VG.dataw.redisClient.hexists(str(inputs.sess_id), "data"):
        return JSONResponse(status_code=409, content=str(f"The session_id is duplicated!"))

    urls = regex.findall(r'https?://[^\s]+', inputs.url)
    url = urls[-1] if urls else None
    inputs.url = url
    producer = app.state.producer
    await producer.send_and_wait(
        Config.TOPIC_DATA,
        value=inputs.__dict__,
        key=inputs.sess_id.encode() if inputs.sess_id else None
    )

    if not MULTIW.VG.dataw.redisClient.hexists(str(inputs.sess_id), "data"):
        if MULTIW.VG.dataw.redisClient.hexists("session", "existed"):
            list_sess = eval(MULTIW.VG.dataw.redisClient.hget("session", "existed"))
        else:
            list_sess = []
        if inputs.sess_id not in list_sess:
            list_sess.append(inputs.sess_id)
        MULTIW.VG.dataw.redisClient.hset("session", "existed", str(list_sess))

    MULTIW.VG.dataw.update_status(inputs.sess_id, "data", str(datetime.now()), {}, 0, "pending")
    return JSONResponse(status_code=201, content=str(f"Message delivered to {Config.TOPIC_DATA}"))

@app.post("/api/createVideoCache")
@HTTPException() 
async def createVideoCache(inputs: InputGen = Body(...)):
    LOGGER.info(inputs)
    producer = app.state.producer
    await producer.send_and_wait(
        Config.TOPIC_QUERY,
        value=inputs.__dict__,
        key=inputs.sess_id.encode() if inputs.sess_id else None
    )

    if not MULTIW.VG.dataw.redisClient.hexists(str(inputs.sess_id), "data"):
        if MULTIW.VG.dataw.redisClient.hexists("session", "existed"):
            list_sess = eval(MULTIW.VG.dataw.redisClient.hget("session", "existed"))
        else:
            list_sess = []
        if inputs.sess_id not in list_sess:
            list_sess.append(inputs.sess_id)
        MULTIW.VG.dataw.redisClient.hset("session", "existed", str(list_sess))

    MULTIW.VG.dataw.update_status(inputs.sess_id, "video", str(datetime.now()), {}, 0, "pending")
    return JSONResponse(status_code=201, content=str(f"Message delivered to {Config.TOPIC_QUERY}"))

@app.post("/api/getStatus")
@HTTPException() 
async def getStatus(inputs: Status = Body(...)):
    result = MULTIW.VG.dataw.get_status(session_id=inputs.sess_id, type=inputs.type)
    if not result["success"]:
        return JSONResponse(status_code=500, content=result["error"])
    return JSONResponse(status_code=200, content=result['result'])

@app.post("/api/deleteSession")
@HTTPException() 
async def deleteSession(inputs: Status = Body(...)):
    if not MULTIW.VG.dataw.redisClient.hexists(str(inputs.sess_id), inputs.type):
        return JSONResponse(status_code=501, content=str(f"The session_id doesn't exist!"))

    MULTIW.VG.dataw.redisClient.hdel(str(inputs.sess_id), inputs.type)
    return JSONResponse(status_code=200, content="Delete complete!")
    


if __name__=="__main__":
    host = "0.0.0.0"
    port = 8507
    uvicorn.run("controller:app", host=host, port=port, log_level="info", reload=False, workers=1)
    
    
    
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