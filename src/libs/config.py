import os
import torch
import jwt

import sys
from pathlib import Path 
FILE = Path(__file__).resolve()
DIR = FILE.parents[0]
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

class Config:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()

    # GPU settings
    CUDA_AVAILABLE      = torch.cuda.is_available()
    NUM_GPUS            = torch.cuda.device_count() if CUDA_AVAILABLE else 0
    NUM_DATA_CONSUMERS  = 1
    NUM_QUERY_CONSUMERS = 1
    BATCH_SIZE          = 8
    DBMEM_NAME          = "memory"
    NUM_WORKER          = int(os.getenv('NUM_WORKER', "1"))
    
    REDISSERVER_URL      = os.getenv('REDISSERVER_URL', "http://localhost:8502")
    REDISSERVER_PASSWORD = os.getenv('REDISSERVER_PASSWORD', 'RedisAuth')
    
    # POSTGRES_URL      = os.getenv('POSTGRES_URL', "http://localhost:6670")
    # POSTGRES_DBNAME   = os.getenv('POSTGRES_DBNAME', "mmv")
    # POSTGRES_USER     = os.getenv('POSTGRES_USER', "demo")
    # POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', "demo123456")
    # TABLE_NAME        = os.getenv('TABLE_NAME', "videos")
    
    KAFKA_ADDRESS      = os.getenv('KAFKA_ADDRESS', 'localhost:8504')
    TOPIC_DATA         = os.getenv('TOPIC_DATA', "url")
    TOPIC_QUERY        = os.getenv('USER_QUERY', "query")
    GROUP_ID_DATA      = os.getenv('GROUP_ID_DATA', "data_consumer")
    GROUP_ID_QUERY     = os.getenv('GROUP_ID_QUERY', "query_consumer")
    
    # QDRANT_URL      = os.getenv('QDRANT_URL', "http://localhost:7000")
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', "mvvtv")
    
    MINIO_URL        = os.getenv('MINIO_URL', "localhost:8500")
    BUCKET_NAME      = os.getenv('BUCKET_NAME', "data_mvvtv")
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', "demo")
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', "demo123456")
    
    # sparse_model_path   = f"./weights/all_miniLM_L6_v2_with_attentions"
    # dense_model_path    = f"./weights/Vietnamese_Embedding"
    # model_hl_path       = './weights/model_highlight.ckpt'
    # model_slowfast_path = './weights/SLOWFAST_8x8_R50.pkl'
    # model_clip_path     = './weights/ViT-B-32.pt'
    
    PATH_LOG           = f"{str(ROOT)}{os.sep}logs"
    PATH_STATIC        = f"{str(ROOT)}{os.sep}static"
    PATH_TEMP          = os.path.join(PATH_STATIC, "temp")
    FOLDER_FINAL_VIDEO = os.getenv('FOLDER_FINAL_VIDEO', "final_video_mvvtv")

    SECRET_KEY     = os.getenv('SECRET_KEY', "MMV")
    token_openai   = os.getenv('API_KEY_OPENAI', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5Ijoic2stcHJvai1OTDJUa0cyWVRZOFJwcTNPLURmSjg5WHY2MG5qbDZCcklhYWs5TC12SFZOaHVaa3Zsc2FRc3pVQmUzbV9xbmRsSlowOVZJU1UzRlQzQmxia0ZKVzctVEtCSkFiSlZXTFJtMGREWGg0a2thSlhoWm9TYkEtbXdWQkMzcWdkSjY4YXJDSUZycVlfYU9BZXN3NXFSc0IzX2ZGUlNLWUEifQ.JSvIHYuDugxQlE0qRKcVxYB3UbiKddEcqPFYlZoRnSs')
    API_KEY_OPENAI = jwt.decode(token_openai, SECRET_KEY, algorithms=["HS256"])["api_key"]
    
    token_gem   = os.getenv('API_KEY_GEM', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5IjoiQUl6YVN5Q1BKSHNJYUxXaGdMakllQkZVS3E4VHFrclRFdWhGd2xzIn0.7iN_1kRmOahYrT7i5FUplOYeda1s7QhYzk-D-AlgWgE')
    API_KEY_GEM = jwt.decode(token_gem, SECRET_KEY, algorithms=["HS256"])["api_key"]
    

