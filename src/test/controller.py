import asyncio
import uvicorn
import json
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

class MultiprocessWoker():
    def __init__(self, ):
        self.results_store: dict[str, OutputDataWorker] = {}
    async def process_data_consumer(self, consumer_id: int):
         # --------Consumer-----------
        consumer = AIOKafkaConsumer(
            "video_upload",
            bootstrap_servers="localhost:9094",
            group_id="data_consumer",
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
                    print(f"Consumer {consumer_id} received: {message.key}-{message.value} from partition {message.partition}")
                    await asyncio.sleep(10)

            except asyncio.CancelledError:
                print(f"Consumer {consumer_id} is shutting down")
                await consumer.stop()
                break
            # except KeyboardInterrupt:  # handle manual interruption (Ctrl+C)
            #     print("KeyboardInterrupt in read from stdout detected, exiting...")
            #     await consumer.stop()
            #     break
            except Exception as e:
                tb_str = traceback.format_exc()
                print(f"Error in consumer {consumer_id}: {tb_str}")
                await asyncio.sleep(1)  # Prevent tight loop in case of errors
            
        await consumer.stop()

MULTIW = MultiprocessWoker()


@asynccontextmanager
async def lifespan(app: FastAPI): 
    # Start the consumers
    consumer_tasks = []
    for i in range(1):
        consumer_id = f"data_{i}"
        consumer_task = asyncio.create_task(
            MULTIW.process_data_consumer(consumer_id=consumer_id)
        )
        consumer_tasks.append(consumer_task)
        
        
    # Create a producer for sending messages
    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9094",
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    app.state.producer = producer
    
    # Create admin client kafka
    kafka_client = AdminClient({'bootstrap.servers': "localhost:9094"})
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__=="__main__":
    host = "0.0.0.0"
    port = 8386
    uvicorn.run("controller:app", host=host, port=port, log_level="info", reload=False, workers=3)
