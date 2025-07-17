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
from confluent_kafka.admin import AdminClient
from multiprocess_worker import Config, MultiprocessWoker, AIOKafkaProducer

os.environ["TOKENIZERS_PARALLELISM"] = "false"

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]

check_folder_exist(path_log=Config.PATH_LOG, path_static=Config.PATH_STATIC)
# LOGGER_APP = set_log_file(file_name="app")

SECRET_KEY     = os.getenv('SECRET_KEY', "MMV")
TOKEN_OPENAI   = os.getenv('API_OPENAI_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5Ijoic2stcHJvai1QSDNHNnlMVEticmdvaU9ieTA4YlVMNHc0eVYxR3NJa25IeEltTl9VMFI1WmVsOWpKcDI0MzZuNUEwOTdVdTVDeXVFMDJha1RqNVQzQmxia0ZKX3dJTUw2RHVrZzh4eWtsUXdsMTN0b2JfcGVkV1c0T1hsNzhQWGVIcDhOLW1DNjY1ZE1CdUlLMFVlWEt1bzRRUnk2Ylk1dDNYSUEifQ.2qjUENU0rafI6syRlTfnKIsm6O4zuhHRqahUcculn8E')
API_KEY_OPENAI = jwt.decode(TOKEN_OPENAI, SECRET_KEY, algorithms=["HS256"])["api_key"]

SECRET_KEY  = os.getenv('SECRET_KEY', "MMV")
TOKEN_GEM   = os.getenv('API_GEM_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5IjoiQUl6YVN5Q1BKSHNJYUxXaGdMakllQkZVS3E4VHFrclRFdWhGd2xzIn0.7iN_1kRmOahYrT7i5FUplOYeda1s7QhYzk-D-AlgWgE')
API_KEY_GEM = jwt.decode(TOKEN_GEM, SECRET_KEY, algorithms=["HS256"])["api_key"]

REDIS_URL = "redis://:root@localhost:8389"

# VG = VideoGeneration(redis_url=REDIS_URL, api_key_openai=API_KEY_OPENAI, api_key_gem=API_KEY_GEM)

MULTIW = MultiprocessWoker()

@asynccontextmanager
async def lifespan(app: FastAPI): 
    # Start the consumers
    consumer_tasks = []
    for i in range(Config.NUM_DATA_CONSUMERS):
        consumer_id = f"data_{i}"
        consumer_task = asyncio.create_task(
            MULTIW.process_data_consumer(consumer_id=consumer_id)
        )
        consumer_tasks.append(consumer_task)

    for i in range(Config.NUM_QUERY_CONSUMERS):
        consumer_id = f"query_{i}"
        consumer_task = asyncio.create_task(
            MULTIW.process_video_consumer(consumer_id=consumer_id)
        )
        consumer_tasks.append(consumer_task)

    # Create a producer for sending messages
    producer = AIOKafkaProducer(
        bootstrap_servers=Config.KAFKA_ADDRESS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    app.state.producer = producer
    
    # Create admin client kafka
    kafka_client = AdminClient({'bootstrap.servers': Config.KAFKA_ADDRESS})
    app.state.kafka_client = kafka_client
    
    yield

    # Shutdown: Cancel all consumer tasks and stop the producer
    for task in consumer_tasks:
        task.cancel()
    
    await producer.stop()
    
    # Wait for all tasks to be cancelled
    await asyncio.gather(*consumer_tasks, return_exceptions=True)
    print("All consumer tasks have been cancelled")


# Create FastAPI application
app = FastAPI(
    title="Chat Bot API",
    description="High-concurrency API for calling chat bot",
    version="1.0.0",
    lifespan=lifespan
)
app.mount("/static", StaticFiles(directory=Config.PATH_STATIC), name="static")
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)