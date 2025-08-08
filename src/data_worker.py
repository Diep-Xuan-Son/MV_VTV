import sys
from pathlib import Path 
FILE = Path(__file__).resolve()
DIR = FILE.parents[0]
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
    
import os 
import time
import uuid
import json 
import redis
import traceback
import numpy as np
from tqdm import tqdm
from minio import Minio
from datetime import datetime
from urllib.parse import urlparse 
from confluent_kafka.admin import NewTopic

from libs.config import Config
from libs.utils import MyException, logging, formatter
LOGGER = logging.getLogger("data_worker")
FILE_HANDLER = logging.FileHandler(f"{Config.PATH_LOG}{os.sep}data_worker_{datetime.now().strftime('%Y_%m_%d')}.log")
FILE_HANDLER.setFormatter(formatter)
LOGGER.addHandler(FILE_HANDLER)

class DBWorker(object):
    def __init__(self, 
                 minio_url="localhost:9000", 
                 minio_access_key="demo",
                 minio_secret_key="demo123456",
                 bucket_name="data_mmv",
                 
                 redis_url="redis://:root@localhost:6669", 
                 redis_password="RedisAuth",
                 
                 check_connection=False, 
                 cache=False):

        #----setup Minio----
        self.minio_client = Minio(
                                endpoint=minio_url,
                                access_key=minio_access_key,
                                secret_key=minio_secret_key,
                                secure=False,
                            )
        
        #----setup cache redis----
        # self.dbmemory_name = dbmemory_name
        url_redis = urlparse(redis_url)
        self.redisClient = redis.StrictRedis(host=url_redis.hostname,
                                            port=url_redis.port,
                                            password=redis_password,
                                            db=0)
        
        self.init_db(bucket_name=bucket_name)
            
    def create_bucket(self, bucket_name: str):
        bucket_name = bucket_name.replace("_", "-")
        found = self.minio_client.bucket_exists(bucket_name=bucket_name)
        if found:
            return {"success": False, "error": f"Bucket {bucket_name} already exists, skip creating!"}
        self.minio_client.make_bucket(bucket_name=bucket_name)
        return {"success": True}

    def upload_file2bucket(self, bucket_name: str, folder_name: str, list_file_path: list):
        bucket_name = bucket_name.replace("_", "-")
        found = self.minio_client.bucket_exists(bucket_name=bucket_name)
        if not found:
            return {"success": False, "error": f"Bucket {bucket_name} does not exist!"}
        # objects_exist = self.get_file_name_bucket(bucket_name, folder_name)["data"]
        # objects_exist = [x.object_name for x in objects_exist]
        list_path_new = []
        for i, fp in enumerate(list_file_path):
            fn = os.path.basename(fp)
            object_name = os.path.join(folder_name, fn)
            list_path_new.append(object_name)
            # if object_name in objects_exist:
                # LOGGER_RETRIEVAL.info(f"File {fn} exists!")
                # continue
            self.minio_client.fput_object(
                bucket_name=bucket_name, object_name=object_name, file_path=fp,
            )
        return {"success": True, "list_path_new": list_path_new}
    
    def download_file(self, bucket_name: str, object_name: str, folder_local: str):
        bucket_name = bucket_name.replace("_", "-")
        fn = os.path.basename(object_name)
        file_path = os.path.join(folder_local, fn)
        response = self.minio_client.fget_object(bucket_name=bucket_name, object_name=object_name, file_path=file_path)
        return {"success": True, "file_path": file_path}

    def delete_file_bucket(self, bucket_name: str, folder_name: str, list_file_name: list):
        bucket_name = bucket_name.replace("_", "-")
        found = self.minio_client.bucket_exists(bucket_name=bucket_name)
        if not found:
            return {"success": False, "error": f"Bucket {bucket_name} does not exist!"}
        for i, fn in enumerate(list_file_name):
            self.minio_client.remove_object(bucket_name=bucket_name, object_name=os.path.join(folder_name, os.path.basename(fn)))
        return {"success": True}

    def delete_folder_bucket(self, bucket_name: str, folder_name: str):
        bucket_name = bucket_name.replace("_", "-")
        objects_to_delete = self.get_file_name_bucket(bucket_name, folder_name)["data"]
        for obj in objects_to_delete:
            self.minio_client.remove_object(bucket_name=bucket_name, object_name=obj.object_name)
        return {"success": True}

    def get_file_name_bucket(self, bucket_name: str, folder_name: str):
        bucket_name = bucket_name.replace("_", "-")
        found = self.minio_client.bucket_exists(bucket_name=bucket_name)
        if not found:
            return {"success": False, "error": f"Bucket {bucket_name} does not exist!"}
        return {"success": True, "data": self.minio_client.list_objects(bucket_name, prefix=folder_name, recursive=True)}
    
    def create_topic(self, client: object, topic_name: str, num_partitions: int=1, replication_factor: int=1, retention: str="3600000", cleanup_policy: str="delete", message_size: str="1048588"):
        # Check if topic already exists
        existing_topics = client.list_topics(timeout=10).topics
        if topic_name not in existing_topics:
            # Define the topic you want to create
            config={
                'retention.ms': str(retention),  # 1 hour
                'cleanup.policy': cleanup_policy,
                'max.message.bytes': message_size
            }
            new_topic = NewTopic(topic=topic_name, num_partitions=num_partitions, replication_factor=replication_factor, config=config)
            # Create the topic
            fs = client.create_topics([new_topic])
            # Wait for topic creation to finish and check for errors
            for topic, f in fs.items():
                try:
                    f.result()  # Block until topic creation completes
                    message = f"Topic '{topic}' created successfully."
                    LOGGER.info(message)
                    return {"success": True, "message": message}
                except Exception as e:
                    tb_str = traceback.format_exc()
                    LOGGER.error(f"Failed to create topic '{topic}': {tb_str}")
                    return {"success": False, "error": e}
        else:
            error_ms = f"Topic '{topic_name}' already exists."
            LOGGER.error(error_ms)
            return {"success": False, "error": error_ms}
        
    def delete_topic(self, client: object, topic_name: str):
        # Check if topic already exists
        existing_topics = client.list_topics(timeout=10).topics
        if topic_name in existing_topics:
            # Delete the topic
            fs = client.delete_topics([topic_name], operation_timeout=30)
            for topic, f in fs.items():
                try:
                    f.result()  # Wait for deletion to complete
                    message = f"Topic '{topic}' deleted."
                    LOGGER.info(message)
                    return {"success": True, "message": message}
                except Exception as e:
                    tb_str = traceback.format_exc()
                    LOGGER.error(f"Failed to delete topic '{topic}': {tb_str}")
                    return {"success": False, "error": e}
        else:
            error_ms = f"Topic '{topic_name}' doesn't exists."
            LOGGER.error(error_ms)
            return {"success": False, "error": error_ms}
    
    def produce_message(self, producer: object, topic: str, messages: list[dict]):
        # Delivery report callback to confirm message delivery
        def delivery_report(err, msg):
            if err is not None:
                LOGGER.error(f"❌ Delivery failed: {err}")
            else:
                LOGGER.info(f"✅ Message delivered to {msg.topic()} [{msg.partition()}]")
        
        for message in messages:
            message_json = json.dumps(message)
            # Send the message (encoded to UTF-8)
            producer.produce(topic=topic, key=message["sess_id"], value=message_json.encode('utf-8'), callback=delivery_report)
            producer.poll(0)  # Triggers delivery callbacks
        
        producer.flush()
        return {"success": True, "message": f"Message delivered to {topic}"}
    
    @MyException()  
    def init_db(self, bucket_name: str):
        #----create db minio----
        res = self.create_bucket(bucket_name=bucket_name)
        if not res["success"]:
            LOGGER.error(res["error"])
        #///////////////////////
        return {"success": True}
    
    @MyException()
    def delete_db(self, collection_name: str, bucket_name: str, db_name: str, table_name: str):
        # ----delete db qdrant----
        res = self.delete_collection(collection_name=collection_name)
        if not res["success"]:
            LOGGER.error(res["error"])
        #/////////////////////////
        
        self.cur.execute(f'''DROP TABLE IF EXISTS {table_name}''')
        self.cur.execute(f'''DROP TABLE IF EXISTS tasks''')
        return {"success": True}
    
    def update_status(self, session_id: str, type: str, created_at: str, result: dict, percent: float, status: str):
        status = {
            "session_id": session_id,
            "type": type,
            "created_at": created_at,
            "result": json.dumps(result),
            "percent": percent,
            "status": status
        }
        self.redisClient.hset(session_id, type, json.dumps(status))
        self.redisClient.expire(session_id, 1800)
        
    def get_status(self, session_id: str, type: str):
        status = {}
        if self.redisClient.exists(session_id):
            status = json.loads(self.redisClient.hget(session_id, type))
        else:
            {"success": False, "error": "session id doesn't exist"}
        return {"success": True, "result": status}
    
    @MyException()        
    def upload_data(self,
                    sess_id: str,
                    collection_name: str, 
                    bucket_name: str, 
                    img_path: dict, 
                    **kwargs):
        bucket_name = bucket_name.replace("_", "-")

        # print(img_path)
        img_path_new = {}
        for i, (vid, file_name) in enumerate(tqdm(img_path.items())):
            #----upload file to minio----
            if file_name:
                LOGGER.info("----upload to minio----")
                res = self.upload_file2bucket(bucket_name=bucket_name, folder_name=sess_id, list_file_path=[file_name])
                if not res["success"]:
                    LOGGER.error(res["error"])
                    img_path_new[vid] = ""
                    return res
                else:
                    img_path_new[vid] = os.path.join(sess_id, os.path.basename(file_name))
            #////////////////////////////
            else:
                img_path_new[vid] = ""
        self.update_status(sess_id, "data", str(datetime.now()), {}, 95, "pending")
        # print(list_path_new)
        
        return {"success": True, "img_path_new": img_path_new}
        
if __name__=="__main__":
    dtw = DBWorker()
    
    bucket_name = "data_mmv"
    dtw.init_db(bucket_name=bucket_name)
    exit()
    
    # from libs.utils import MyException, check_folder_exist
    # dir_temp_video = f"{DIR}{os.sep}static{os.sep}temp"
    # check_folder_exist(dir_temp_video=dir_temp_video)
    
    v_id = "id_video.mp4"
    overview = "Video này trình bày hai phần nội dung chính liên quan đến lĩnh vực thiết kế. Phần đầu tiên cho thấy một nhóm các nhà thiết kế đang làm việc chăm chỉ trên một dự án, có thể là thiết kế nội thất hoặc kiến trúc, thể hiện sự tỉ mỉ và chuyên nghiệp trong quá trình sáng tạo và hợp tác. Phần thứ hai giới thiệu một không gian nội thất hiện đại và sang trọng, có thể là một spa hoặc phòng tắm cao cấp, với sự kết hợp hoàn hảo giữa các vật liệu tự nhiên và kiến trúc hiện đại, tạo ra một bầu không khí thư giãn và tinh tế. Tổng thể, video mang đến cái nhìn sâu sắc về quy trình thiết kế và không gian sống đẳng cấp."
    list_path = ["./src/static/temp/aaa/5.mp4"]
    list_des = ["test upload video 5"]
    list_htime = [0]
    category = ["other", "service", "staff"]
    # res = dtw.upload_data(collection_name=collection_name, bucket_name=bucket_name, v_id=v_id, overview=overview, list_path=list_path, list_des=list_des, list_htime=list_htime, category=category)
    
    # dtw.add_vector(collection_name=collection_name, v_id=v_id, v_name=v_id, root_path=list_path[0], overview=overview, list_path=list_path, list_des=list_des, list_htime=list_htime, category=category, group_id="group1")
    
    # dtw.retrieve(collection_name=collection_name, text_querys=["sự tỉ mỉ và chuyên nghiệp"], categories=["other"])
    
    
    data = {
        "3.mp4": {
            "overview": "Video cận cảnh quá trình cấy tóc thẩm mỹ tại MQ Spa, tập trung vào sự tỉ mỉ và chuyên nghiệp của kỹ thuật viên. Màu sắc tương phản giữa găng tay tím và da đầu tạo điểm nhấn thị giác.",
            "list_path": ["./src/static/videos_splitted/spa/3_splitted_0.mp4"]*9,
            "list_des": ["Video cận cảnh quá trình cấy tóc thẩm mỹ tại MQ Spa, tập trung vào sự tỉ mỉ và chuyên nghiệp của kỹ thuật viên. Màu sắc tương phản giữa găng tay tím và da đầu tạo điểm nhấn thị giác."]*9,
            "list_htime": [10]*9,
            "category": ["opening_scene", "reception_scene", "consultation_scene", 'service_scene', "interior_scene", "staff_scene", "customer_scene", "product_scene", "closing_scene"]
        },
        "2.mp4": {
            "overview": 'Video này giới thiệu dịch vụ massage tại MQ Spa, tập trung vào trải nghiệm thư giãn và chuyên nghiệp. Hình ảnh cận cảnh các động tác massage nhẹ nhàng, dầu massage bóng bẩy và không gian yên tĩnh tạo cảm giác thư thái, thu hút người xem muốn trải nghiệm dịch vụ.',
            "list_path": ["./src/static/short_videos/spa/2.mp4"]*9,
            "list_des": ['Video này giới thiệu dịch vụ massage tại MQ Spa, tập trung vào trải nghiệm thư giãn và chuyên nghiệp. Hình ảnh cận cảnh các động tác massage nhẹ nhàng, dầu massage bóng bẩy và không gian yên tĩnh tạo cảm giác thư thái, thu hút người xem muốn trải nghiệm dịch vụ.']*9,
            "list_htime": [10]*9,
            "category": ["opening_scene", "reception_scene", "consultation_scene", 'service_scene', "interior_scene", "staff_scene", "customer_scene", "product_scene", "closing_scene"]
        },
        "6.mp4": {
            "overview": 'Video giới thiệu về trải nghiệm thư giãn độc đáo tại MQ Spa, nơi khách hàng có thể tận hưởng liệu pháp floatation therapy trong một không gian yên tĩnh, ánh sáng dịu nhẹ, giúp giảm căng thẳng và tái tạo năng lượng. Video giới thiệu MQ Spa với hình ảnh một người phụ nữ đang thư giãn trong bồn tắm nổi, ánh sáng tím và xanh tạo cảm giác yên bình và thư thái. Sự tập trung vào trải nghiệm cá nhân và không gian spa sang trọng có thể thu hút sự chú ý của khán giả. Cảnh quay cận cảnh một người phụ nữ đang thư giãn trong không gian spa với ánh sáng dịu nhẹ màu hồng và xanh lam. Sự tập trung vào biểu cảm thanh thản và không gian yên bình tạo nên sự hấp dẫn, gợi cảm giác thư giãn và tái tạo năng lượng.',
            "list_path": ["./src/static/videos_splitted/spa/6_splitted_0.mp4", "./src/static/videos_splitted/spa/6_splitted_1.mp4", "./src/static/videos_splitted/spa/6_splitted_0.mp4"]*3,
            "list_des": ['Video giới thiệu về trải nghiệm thư giãn độc đáo tại MQ Spa, nơi khách hàng có thể tận hưởng liệu pháp floatation therapy trong một không gian yên tĩnh, ánh sáng dịu nhẹ, giúp giảm căng thẳng và tái tạo năng lượng.', 'Video giới thiệu MQ Spa với hình ảnh một người phụ nữ đang thư giãn trong bồn tắm nổi, ánh sáng tím và xanh tạo cảm giác yên bình và thư thái. Sự tập trung vào trải nghiệm cá nhân và không gian spa sang trọng có thể thu hút sự chú ý của khán giả.', 'Cảnh quay cận cảnh một người phụ nữ đang thư giãn trong không gian spa với ánh sáng dịu nhẹ màu hồng và xanh lam. Sự tập trung vào biểu cảm thanh thản và không gian yên bình tạo nên sự hấp dẫn, gợi cảm giác thư giãn và tái tạo năng lượng.']*3,
            "list_htime": [10]*9,
            "category": ["opening_scene", "reception_scene", "consultation_scene", 'service_scene', "interior_scene", "staff_scene", "customer_scene", "product_scene", "closing_scene"]
        },
        "1.mp4": {
            "overview": 'Video giới thiệu dịch vụ massage Shiatsu tại MQ Spa. Cảnh quay tập trung vào sự thư giãn và thoải mái mà khách hàng trải nghiệm trong quá trình massage, với ánh sáng dịu nhẹ và không gian yên tĩnh. Các động tác massage chuyên nghiệp được thể hiện, nhấn mạnh lợi ích về sức khỏe và làn da.',
            "list_path": ["./src/static/short_videos/spa/1.mp4"]*9,
            "list_des": ['Video giới thiệu dịch vụ massage Shiatsu tại MQ Spa. Cảnh quay tập trung vào sự thư giãn và thoải mái mà khách hàng trải nghiệm trong quá trình massage, với ánh sáng dịu nhẹ và không gian yên tĩnh. Các động tác massage chuyên nghiệp được thể hiện, nhấn mạnh lợi ích về sức khỏe và làn da.']*9,
            "list_htime": [10]*9,
            "category": ["opening_scene", "reception_scene", "consultation_scene", 'service_scene', "interior_scene", "staff_scene", "customer_scene", "product_scene", "closing_scene"]
        },
        "4.mp4": {
            "overview": 'Video giới thiệu về liệu trình spa tại MQ Spa, tập trung vào trải nghiệm thư giãn và chăm sóc da mặt. Góc quay từ trên xuống tạo cảm giác sang trọng và chuyên nghiệp, làm nổi bật sự thoải mái của khách hàng.',
            "list_path": ["./src/static/videos_splitted/spa/4_splitted_0.mp4"]*9,
            "list_des": ['Video giới thiệu về liệu trình spa tại MQ Spa, tập trung vào trải nghiệm thư giãn và chăm sóc da mặt. Góc quay từ trên xuống tạo cảm giác sang trọng và chuyên nghiệp, làm nổi bật sự thoải mái của khách hàng.']*9,
            "list_htime": [10]*9,
            "category": ["opening_scene", "reception_scene", "consultation_scene", 'service_scene', "interior_scene", "staff_scene", "customer_scene", "product_scene", "closing_scene"]
        },
        "5.mp4": {
            "overview": "Cảnh này giới thiệu 'Phòng Mưa' tại MQ Spa, một không gian độc đáo và thư giãn. Hiệu ứng mưa nhân tạo tạo ra một bầu không khí thanh bình và hấp dẫn, hứa hẹn một trải nghiệm spa khác biệt và đáng nhớ. Video này cho thấy cận cảnh quá trình trị liệu bùn khoáng tại MQ Spa, tập trung vào sự tỉ mỉ và chuyên nghiệp của kỹ thuật viên. Màu sắc tự nhiên của bùn khoáng kết hợp với ánh sáng dịu nhẹ tạo nên cảm giác thư giãn và sang trọng.",
            "list_path": ["./src/static/videos_splitted/spa/5_splitted_0.mp4", "./src/static/videos_splitted/spa/5_splitted_1.mp4", "./src/static/videos_splitted/spa/5_splitted_1.mp4"]*3,
            "list_des": ["Cảnh này giới thiệu 'Phòng Mưa' tại MQ Spa, một không gian độc đáo và thư giãn. Hiệu ứng mưa nhân tạo tạo ra một bầu không khí thanh bình và hấp dẫn, hứa hẹn một trải nghiệm spa khác biệt và đáng nhớ.", 'Video này cho thấy cận cảnh quá trình trị liệu bùn khoáng tại MQ Spa, tập trung vào sự tỉ mỉ và chuyên nghiệp của kỹ thuật viên. Màu sắc tự nhiên của bùn khoáng kết hợp với ánh sáng dịu nhẹ tạo nên cảm giác thư giãn và sang trọng.', 'Video này cho thấy cận cảnh quá trình trị liệu bùn khoáng tại MQ Spa, tập trung vào sự tỉ mỉ và chuyên nghiệp của kỹ thuật viên. Màu sắc tự nhiên của bùn khoáng kết hợp với ánh sáng dịu nhẹ tạo nên cảm giác thư giãn và sang trọng.']*3,
            "list_htime": [10]*9,
            "category": ["opening_scene", "reception_scene", "consultation_scene", 'service_scene', "interior_scene", "staff_scene", "customer_scene", "product_scene", "closing_scene"]
        },
        "7.mp4": {
            "overview": 'Video giới thiệu về MQ Spa, tập trung vào không gian sang trọng và dịch vụ chăm sóc sức khỏe toàn diện. Sự tương tác giữa hai người phụ nữ tạo cảm giác gần gũi, tin cậy, khuyến khích người xem tìm hiểu thêm về spa. Video này giới thiệu trải nghiệm tại MQ Spa, nơi khách hàng được tận hưởng các liệu pháp làm đẹp và thư giãn hiện đại. Điểm nhấn là công nghệ tiên tiến và sự thoải mái, sang trọng trong không gian spa. Video này giới thiệu các dịch vụ đa dạng của MQ Spa, từ phục hồi chấn thương, điều trị các bệnh về da đến giảm cân. Điểm hấp dẫn là sự tập trung vào các vấn đề sức khỏe cụ thể và giải pháp mà spa cung cấp. Video giới thiệu về MQ Spa, tập trung vào trải nghiệm thư giãn và sang trọng mà spa mang lại. Bối cảnh tươi sáng, hiện đại và người đại diện thương hiệu thân thiện tạo cảm giác gần gũi, thu hút.',
            "list_path": ["./src/static/videos_splitted/spa/7_splitted_0.mp4", "./src/static/videos_splitted/spa/7_splitted_1.mp4", "./src/static/videos_splitted/spa/7_splitted_2.mp4", "./src/static/videos_splitted/spa/7_splitted_3.mp4"]*2 + ["./src/static/videos_splitted/spa/7_splitted_3.mp4"],
            "list_des": ['Video giới thiệu về MQ Spa, tập trung vào không gian sang trọng và dịch vụ chăm sóc sức khỏe toàn diện. Sự tương tác giữa hai người phụ nữ tạo cảm giác gần gũi, tin cậy, khuyến khích người xem tìm hiểu thêm về spa.', 'Video này giới thiệu trải nghiệm tại MQ Spa, nơi khách hàng được tận hưởng các liệu pháp làm đẹp và thư giãn hiện đại. Điểm nhấn là công nghệ tiên tiến và sự thoải mái, sang trọng trong không gian spa.', 'Video này giới thiệu các dịch vụ đa dạng của MQ Spa, từ phục hồi chấn thương, điều trị các bệnh về da đến giảm cân. Điểm hấp dẫn là sự tập trung vào các vấn đề sức khỏe cụ thể và giải pháp mà spa cung cấp.', 'Video giới thiệu về MQ Spa, tập trung vào trải nghiệm thư giãn và sang trọng mà spa mang lại. Bối cảnh tươi sáng, hiện đại và người đại diện thương hiệu thân thiện tạo cảm giác gần gũi, thu hút.']*2 + ['Video giới thiệu về MQ Spa, tập trung vào trải nghiệm thư giãn và sang trọng mà spa mang lại. Bối cảnh tươi sáng, hiện đại và người đại diện thương hiệu thân thiện tạo cảm giác gần gũi, thu hút.'],
            "list_htime": [10]*9,
            "category": ["opening_scene", "reception_scene", "consultation_scene", 'service_scene', "interior_scene", "staff_scene", "customer_scene", "product_scene", "closing_scene"]
        },
    }
    
    # for k, v in data.items():
    #     dtw.add_vector(collection_name=collection_name, v_id=k, v_name=v_id, root_path=list_path[0], overview=v["overview"], list_path=v["list_path"], list_des=v["list_des"], list_htime=v["list_htime"], category=v["category"], group_id="group1")
        
    dtw.retrieve(collection_name=collection_name, text_querys=["Màu sắc tương phản giữa găng tay tím và da đầu tạo điểm nhấn thị giác", "dầu massage bóng bẩy và không gian yên tĩnh tạo cảm giác thư thái", "liệu pháp floatation therapy trong một không gian yên tĩnh, ánh sáng dịu nhẹ", "dịch vụ massage Shiatsu tại MQ Spa", "tập trung vào trải nghiệm thư giãn và chăm sóc da mặt", "'Phòng Mưa' tại MQ Spa, một không gian độc đáo và thư giãn", "Sự tương tác giữa hai người phụ nữ tạo cảm giác gần gũi, tin cậy, khuyến khích người xem tìm hiểu thêm về spa", "các dịch vụ đa dạng của MQ Spa, từ phục hồi chấn thương, điều trị các bệnh về da đến giảm cân", "không gian spa với ánh sáng dịu nhẹ màu hồng và xanh lam"], categories=["opening_scene", "reception_scene", "consultation_scene", 'service_scene', "interior_scene", "staff_scene", "customer_scene", "product_scene", "closing_scene"])