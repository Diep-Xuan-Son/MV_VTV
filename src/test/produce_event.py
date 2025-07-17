import asyncio
import uvicorn
import json
import random
import traceback
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from confluent_kafka.admin import AdminClient
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Union, Tuple, Optional, Type
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import FastAPI, Request, Depends, Body, HTTPException, status, Query, File, UploadFile, Form

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

async def produce():
    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9094",
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()

    try:
        for i in range(10):
            message = {
                "sess_id": i
            }
            print(message)
            await producer.send_and_wait(
                "video_upload",
                value=message,
                key=f"sess_id_{i}".encode(),
                partition=random.randrange(0, 3)
            )
    except asyncio.CancelledError:
        print(f"producer {1} is shutting down")
        await producer.stop()

    finally:
        print(f"producer {1} is shutting down")
        await producer.stop()


# async def send_message(message):


if __name__=="__main__":
    asyncio.run(produce())
    # message = InputDataWorker(sess_id=inputs.sess_id, v_id=v_id, name=name_v, path_file=path_file, overview=inputs.overview, category=inputs.category, mute=inputs.mute)
    

