import os
import jwt
import ast
import time
import json
import uuid
import torch
import asyncio
import threading
import traceback
from datetime import datetime
from urllib.parse import urlparse 
# from confluent_kafka import Consumer
from langchain_openai import ChatOpenAI
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from langchain_google_genai import ChatGoogleGenerativeAI

# from libs.utils import set_log_file
from main_pipeline import VideoGeneration
from libs.utils import delete_folder_exist

import sys
from pathlib import Path 
FILE = Path(__file__).resolve()
DIR = FILE.parents[0]
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# LOGGER_WORKER = set_log_file(file_name="worker")

# Configuration settings
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
    
    PATH_LOG           = f"{str(DIR)}{os.sep}logs"
    PATH_STATIC        = f"{str(DIR)}{os.sep}static"
    PATH_TEMP          = os.path.join(PATH_STATIC, "temp")
    FOLDER_FINAL_VIDEO = os.getenv('FOLDER_FINAL_VIDEO', "final_video_mvvtv")

    SECRET_KEY     = os.getenv('SECRET_KEY', "MMV")
    token_openai   = os.getenv('API_KEY_OPENAI', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5Ijoic2stcHJvai1QSDNHNnlMVEticmdvaU9ieTA4YlVMNHc0eVYxR3NJa25IeEltTl9VMFI1WmVsOWpKcDI0MzZuNUEwOTdVdTVDeXVFMDJha1RqNVQzQmxia0ZKX3dJTUw2RHVrZzh4eWtsUXdsMTN0b2JfcGVkV1c0T1hsNzhQWGVIcDhOLW1DNjY1ZE1CdUlLMFVlWEt1bzRRUnk2Ylk1dDNYSUEifQ.2qjUENU0rafI6syRlTfnKIsm6O4zuhHRqahUcculn8E')
    API_KEY_OPENAI = jwt.decode(token_openai, SECRET_KEY, algorithms=["HS256"])["api_key"]
    
    token_gem   = os.getenv('API_KEY_GEM', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5IjoiQUl6YVN5Q1BKSHNJYUxXaGdMakllQkZVS3E4VHFrclRFdWhGd2xzIn0.7iN_1kRmOahYrT7i5FUplOYeda1s7QhYzk-D-AlgWgE')
    API_KEY_GEM = jwt.decode(token_gem, SECRET_KEY, algorithms=["HS256"])["api_key"]
    
# DATAW = DBWorker()

class MultiprocessWoker():
    def __init__(self, ):
        # Task queue and results
        # self.VM = VideoMaketing(
        #     api_key_openai=Config.API_KEY_OPENAI,
        #     api_key_gem=Config.API_KEY_GEM,
            
        #     qdrant_url=Config.QDRANT_URL, 
        #     collection_name=Config.COLLECTION_NAME, 
        #     minio_url=Config.MINIO_URL, 
        #     minio_access_key=Config.MINIO_ACCESS_KEY,
        #     minio_secret_key=Config.MINIO_SECRET_KEY,
        #     bucket_name=Config.BUCKET_NAME,
        #     redis_url=Config.REDISSERVER_URL, 
        #     redis_password=Config.REDISSERVER_PASSWORD,
        #     dbmemory_name=Config.DBMEM_NAME,
        #     psyconpg_url=Config.POSTGRES_URL,
        #     dbname=Config.POSTGRES_DBNAME,
        #     psyconpg_user=Config.POSTGRES_USER,
        #     psyconpg_password=Config.POSTGRES_PASSWORD,
        #     table_name=Config.TABLE_NAME,
        #     sparse_model_path=Config.sparse_model_path, 
        #     dense_model_path=Config.dense_model_path
        # )
        self.VG = VideoGeneration(
            redis_url=Config.REDISSERVER_URL, 
            redis_password=Config.REDISSERVER_PASSWORD,

            minio_url=Config.MINIO_URL, 
            minio_access_key=Config.MINIO_ACCESS_KEY,
            minio_secret_key=Config.MINIO_SECRET_KEY,
            bucket_name=Config.BUCKET_NAME,

            api_key_openai=Config.API_KEY_OPENAI, 
            api_key_gem=Config.API_KEY_GEM
        )
    
    
    def is_deleted(self, sess_id: str, type: str, local_path_delete: list, minio_path_delete: list, v_id_delete: list):
        res = self.VG.dataw.get_status(sess_id, type)
        if res["success"]:
            if res["result"]["status"] == "interrupted":
                self.VM.dataw.update_status(sess_id, type, str(datetime.now()), {"local_path_delete": local_path_delete, "minio_path_delete": minio_path_delete}, 0, "deleted")
                return True
        return False

    # Task processor
    async def process_data_consumer(self, consumer_id: int):
        # --------Consumer-----------
        consumer = AIOKafkaConsumer(
            Config.TOPIC_DATA,
            bootstrap_servers=Config.KAFKA_ADDRESS,
            group_id=Config.GROUP_ID_DATA,
            enable_auto_commit=True,
            auto_offset_reset="earliest",
            session_timeout_ms=600000,  # 600 seconds
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        await consumer.start()
        print(f"Consumer {consumer_id} started")
        
        while True:
            try:
                # Process messages
                async for message in consumer:
                    # await asyncio.sleep(1)
                    print(f"Consumer {consumer_id} received: {message.value} from partition {message.partition}")
                    
                    data = message.value
                    
                    # check status
                    res = self.VG.dataw.get_status(data["sess_id"], "data")
                    if res["success"]:
                        if res["result"]["status"] in ["deleted", "interrupted"] :
                            print(f"Message {data} has been deleted!")
                            continue
                    else:
                        print(f"The session ID {data['sess_id']} not found!")
                        continue
                    self.VG.dataw.update_status(data["sess_id"], "data", str(datetime.now()), res, 1, "pending")
                    
                    #----preprocess data----
                    datatf = await self.VG.get_data(sess_id=data["sess_id"], url=data["url"])
                    #//////////////////////
                    if datatf["success"]:
                        data_info = {
                            "sess_id": data["sess_id"],
                            "collection_name": Config.COLLECTION_NAME,
                            "bucket_name": Config.BUCKET_NAME
                        }
                        data_info["img_path"] = datatf["img_path"]
                        
                        #----upload data to database----
                        res_upload_data = self.VG.dataw.upload_data(**data_info)
                        if self.is_deleted(data["sess_id"], "data", datatf["list_path_delete"], list(res_upload_data["img_path_new"].values()), []):    # because delete file in buck auto merge folder and file name so that just get all the path have basename in the bucket
                            continue
                        #///////////////////////////////
                        if res_upload_data["success"]:
                            print("Upload data success!")
                            res_upload_data.update(datatf)
                            self.VG.dataw.update_status(data["sess_id"], "data", str(datetime.now()), res_upload_data, 100, "done")
                    else:
                        self.VG.dataw.update_status(data["sess_id"], "data", str(datetime.now()), {"local_path_delete": [], "minio_path_delete": [], "v_id_delete": []}, 0, "deleted")
                
                    delete_folder_exist(*datatf["list_path_delete"])
                    
            except asyncio.CancelledError:
                print(f"Consumer {consumer_id} is shutting down")
                await consumer.stop()
                break
            except Exception as e:
                tb_str = traceback.format_exc()
                print(f"Error in consumer {consumer_id}: {tb_str}")
                self.VG.dataw.update_status(data["sess_id"], "data", str(datetime.now()), {"success": False, "error": str(e)}, 100, "error")
                await asyncio.sleep(1)  # Prevent tight loop in case of errors
        await consumer.stop()
        
    # Task processor
    async def process_video_consumer(self, consumer_id: int):
        # --------Consumer-----------
        consumer = AIOKafkaConsumer(
            Config.TOPIC_QUERY,
            bootstrap_servers=Config.KAFKA_ADDRESS,
            group_id=Config.GROUP_ID_QUERY,
            enable_auto_commit=True,
            auto_offset_reset="earliest",
            session_timeout_ms=300000,  # 300 seconds
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await consumer.start()
        print(f"Consumer {consumer_id} started")
        
        while True:
            try:
                # Process messages
                async for message in consumer:
                    # await asyncio.sleep(1)
                    print(f"Consumer {consumer_id} received: {message.value} from partition {message.partition}")
                    
                    data = message.value
                    
                    # check status
                    columns = ["status"]
                    res = self.VG.dataw.get_status(data["sess_id"], "video")
                    if res["success"]:
                        if res["result"]["status"] in ["deleted", "interrupted"] :
                            print(f"Message {data} has been deleted!")
                            continue
                    else:
                        print(f"The session ID {data['sess_id']} not found!")
                        continue
                    self.VG.dataw.update_status(data["sess_id"], "video", str(datetime.now()), res, 1, "pending")
                    
                    res_mv = await self.VG.run(sess_id=data["sess_id"], title_updated=data["title"], img_des=ast.literal_eval(data["descriptions"]), vipath=ast.literal_eval(data["image_paths"]), img_abbreviation=ast.literal_eval(data["abbreviations"]))
                    if res_mv["success"]:
                        path_final_video = res_mv["result_path"]
                        res = self.VG.dataw.upload_file2bucket(bucket_name=Config.BUCKET_NAME, folder_name=data["sess_id"], list_file_path=[path_final_video])
                        if res["success"]:
                            print("Upload final video success!")
                            res["result_path"] = res["list_path_new"][0]
                            self.VG.dataw.update_status(data["sess_id"], "video", str(datetime.now()), res, 100, "done")
                    else:
                        self.VG.dataw.update_status(data["sess_id"], "video", str(datetime.now()), {"local_path_delete": [], "minio_path_delete": [], "v_id_delete": []}, 0, "deleted")

                    delete_folder_exist(*res_mv["list_path_delete"])
                    
            except asyncio.CancelledError:
                print(f"Consumer {consumer_id} is shutting down")
                await consumer.stop()
                break
            except Exception as e:
                tb_str = traceback.format_exc()
                print(f"Error in consumer {consumer_id}: {tb_str}")
                self.VG.dataw.update_status(data["sess_id"], "video", str(datetime.now()), {"success": False, "error": str(e)}, 100, "error")
                await asyncio.sleep(1)  # Prevent tight loop in case of errors
        await consumer.stop()

if __name__=="__main__":
    
    MTW = MultiprocessWoker()
    asyncio.run(MTW.process_data_consumer(consumer_id=0))