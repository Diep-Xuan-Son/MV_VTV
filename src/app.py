import jwt
import time
import redis
import asyncio
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Union, Tuple, Optional, Type
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import FastAPI, Request, Depends, Body, HTTPException, status, Query, File, UploadFile, Form

from libs.utils import *
from main_pipeline import VideoGeneration

os.environ["TOKENIZERS_PARALLELISM"] = "false"

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]
PATH_LOG = f"{str(ROOT)}{os.sep}logs"
PATH_STATIC = f"{str(ROOT)}{os.sep}static"
check_folder_exist(path_log=PATH_LOG, path_static=PATH_STATIC)
# LOGGER_APP = set_log_file(file_name="app")

SECRET_KEY     = os.getenv('SECRET_KEY', "MMV")
TOKEN_OPENAI   = os.getenv('API_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5Ijoic2stcHJvai1QSDNHNnlMVEticmdvaU9ieTA4YlVMNHc0eVYxR3NJa25IeEltTl9VMFI1WmVsOWpKcDI0MzZuNUEwOTdVdTVDeXVFMDJha1RqNVQzQmxia0ZKX3dJTUw2RHVrZzh4eWtsUXdsMTN0b2JfcGVkV1c0T1hsNzhQWGVIcDhOLW1DNjY1ZE1CdUlLMFVlWEt1bzRRUnk2Ylk1dDNYSUEifQ.2qjUENU0rafI6syRlTfnKIsm6O4zuhHRqahUcculn8E')
API_KEY_OPENAI = jwt.decode(TOKEN_OPENAI, SECRET_KEY, algorithms=["HS256"])["api_key"]
VG = VideoGeneration(api_key_openai=API_KEY_OPENAI)

# Create FastAPI application
app = FastAPI(
    title="Chat Bot API",
    description="High-concurrency API for calling chat bot",
    version="1.0.0",
    # lifespan=lifespan
)
app.mount("/static", StaticFiles(directory=PATH_STATIC), name="static")
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)