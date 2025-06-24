import os
import jwt
import json
import time
import redis
# import torch
import asyncio
import threading
import re as regex
from datetime import datetime
from urllib.parse import urlparse 
from langchain_openai import ChatOpenAI

from tts_worker import TTS
from multi_agent import MultiAgent
from get_data_url import extract_data
from video_editor_worker import VideoEditorWorker
from image_analyzation_worker import ImageAnalyzationWorker
from libs.utils import MyException, check_folder_exist, delete_folder_exist

import sys
from pathlib import Path 
FILE = Path(__file__).resolve()
DIR = FILE.parents[0]
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

class VideoGeneration(object):
    def __init__(self, 
                 tts_model_path: str='./weights/style_tts2/model.pth',
                 tts_config_path: str='./weights/style_tts2/config.yml',
                 nltk_data_path: str='./weights/nltk_data',
                 redis_url="redis://:root@localhost:8389",

                 api_key_openai: str='',
                 api_key_gem: str=''
                 ):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=api_key_openai,  # if you prefer to pass api key in directly instaed of using env vars
            # base_url="...",
            # organization="...",
            # other params...,
            streaming=True
        )

        llm41 = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=api_key_openai,  # if you prefer to pass api key in directly instaed of using env vars
            # base_url="...",
            # organization="...",
            # other params...,
            streaming=True
        )

        self.MA41 = MultiAgent(llm41)
        self.MA = MultiAgent(self.llm)
        self.IAW = ImageAnalyzationWorker(api_key_gem)
        self.VEW = VideoEditorWorker()

        self.dir_image = f"{DIR}{os.sep}static{os.sep}images"
        self.dir_audio = f"{DIR}{os.sep}static{os.sep}audio_transcribe"
        self.dir_final_video = f"{DIR}{os.sep}static{os.sep}final_video"
        check_folder_exist(dir_image=self.dir_image, dir_audio=self.dir_audio)
        self.bg_image_path = f"{DIR}{os.sep}data{os.sep}image_backgrounds{os.sep}bg.png"

        self.ttsw = TTS(model_path=tts_model_path, config_path=tts_config_path, nltk_data_path=nltk_data_path, output_dir=self.dir_audio)

        #----setup redis----
        # self.db_task_data = "data"
        # self.db_task_create_video = "video"
        url_redis = urlparse(redis_url)
        self.redisClient = redis.StrictRedis(host=url_redis.hostname,
                                            port=url_redis.port,
                                            password="RedisAuth",
                                            db=1)
        if not self.redisClient.hexists("session", "existed"):
            self.list_sess = []
        else:
            self.list_sess = eval(self.redisClient.hget("session", "existed"))
        #-----------setup cronjob--------
        self.delete_sess_thread = threading.Thread(
            target=self.delete_sess, args=())
        self.delete_sess_thread.start()

        self.time_delay = 2

    def delete_sess(self, ):
        while True:
            time.sleep(10)
            for sess_id in self.list_sess:
                if not self.redisClient.exists(sess_id):
                    sess_image_dir = os.path.join(self.dir_image, sess_id)
                    sess_final_dir = os.path.join(self.dir_final_video, sess_id)
                    sees_audio_dir = os.path.join(self.dir_audio, sess_id)
                    delete_folder_exist(sess_image_dir=sess_image_dir, sess_final_dir=sess_final_dir, sees_audio_dir=sees_audio_dir)
                    self.list_sess.remove(sess_id)

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
    async def get_data(self, sess_id: str, url: str):
        self.update_status(sess_id, "data", str(datetime.now()), {}, 0, "running")
        # ----init folder for sess_id----
        sess_image_dir = os.path.join(self.dir_image, sess_id)
        delete_folder_exist(sess_image_dir=sess_image_dir)
        check_folder_exist(sess_image_dir=sess_image_dir)
        if sess_id not in self.list_sess:
            self.list_sess.append(sess_id)
            self.redisClient.hset("session", "existed", str(self.list_sess))
        #/////////////////////////////

        result = extract_data(url=url, path_image_save=sess_image_dir)
        title_original = result["title"]
        content = result["content"]
        self.update_status(sess_id, "data", str(datetime.now()), {}, 20, "running")

        title_updated = await self.MA41.split_title(title=title_original)
        title_updated = title_updated["result"]
        self.update_status(sess_id, "data", str(datetime.now()), {}, 40, "running")

        result = await self.MA.get_idea(text=content, title=title_original)
        # title = result["title"]
        ideas = result.copy()
        # del ideas["title"]
        self.update_status(sess_id, "data", str(datetime.now()), {}, 50, "running")

        vdes = {}
        vipath = {}
        thread_des = []
        thread_vid = []
        for img in os.listdir(sess_image_dir):
            # vid = f"video_{len(vdes)}"
            vid = f"video_{len(thread_des)}"
            image_path = os.path.join(sess_image_dir, img)
            # des = await self.IAW.get_description(title_original, image_path)
            # vdes[vid] = des["description_vi"]
            thread_des.append(self.IAW.get_description(title_original, image_path))
            thread_vid.append(vid)
            vipath[vid] = image_path
        result = await asyncio.gather(*thread_des)
        result = [d["description_vi"] for d in result]
        vdes.update(dict(zip(thread_vid, result)))
        self.update_status(sess_id, "data", str(datetime.now()), {}, 80, "running")

        img_list_des = await self.MA.select_idea(description=vdes, ideas=ideas)
        self.update_status(sess_id, "data", str(datetime.now()), {}, 90, "running")

        img_des = await self.MA.synthesize_idea(ideas=img_list_des, title=title_original)

        return {"success": True, "title": title_updated, "img_des": img_des, "img_path": vipath}

    @MyException()
    async def run(self, sess_id: str, title_updated: str, img_des: dict, vipath: dict):
        self.update_status(sess_id, "video", str(datetime.now()), {}, 0, "running")
        # ----init folder for sess_id----
        sess_final_dir = os.path.join(self.dir_final_video, sess_id)
        sees_audio_dir = os.path.join(self.dir_audio, sess_id)
        delete_folder_exist(sess_final_dir=sess_final_dir, sees_audio_dir=sees_audio_dir)
        check_folder_exist(sess_final_dir=sess_final_dir, sees_audio_dir=sees_audio_dir)
        if sess_id not in self.list_sess:
            self.list_sess.append(sess_id)
            self.redisClient.hset("session", "existed", str(self.list_sess))
        list_path_delete = [sees_audio_dir, sess_final_dir]
        #/////////////////////////////

        img_abbreviation = await self.MA41.rewrite_abbreviation(news=img_des)
        self.update_status(sess_id, "video", str(datetime.now()), {}, 10, "running")

        # img_des = {'video_1': '**Trà Việt Nam** đã bắt đầu được **xuất khẩu sang phương Tây** từ thế kỷ 17. Ông **Thân Dỹ Ngữ**, Giám đốc Công ty TNHH Hiệp Thành, đã thành công trong việc **quảng bá trà Việt Nam** ra thế giới.', 'video_0': 'Hai loại **trà ô long ướp hoa sen** và **trà xanh ướp hoa sen** của Việt Nam được thương hiệu **Mariage Frères** xếp vào dòng sản phẩm **cao cấp nhất**. Giá bán lên tới **hơn 1.000 euro/ký**. Ngành trà Việt Nam đang **tăng trưởng** nhờ lối sống thay đổi và nhận thức cao về **lợi ích sức khỏe** của việc uống trà.', 'video_2': 'Việt Nam hiện có khoảng **120.000 héc ta** diện tích trồng trà. Mục tiêu mở rộng lên **135.000-140.000 héc ta** vào năm 2030.'}
        # img_abbreviation = {'video_1': {'TNHH': 'Trách Nhiệm Hữu Hạn', 'thế kỷ 17': 'thế kỷ mười bảy'}, 'video_0': {'1.000 euro/ký': 'một nghìn euro trên một ký'}, 'video_2': {'120.000 héc ta': 'một trăm hai mươi nghìn héc ta', '135.000-140.000 héc ta': 'một trăm ba mươi lăm nghìn đến một trăm bốn mươi nghìn héc ta', '2030': 'hai nghìn không trăm ba mươi'}}
        # vipath = {'video_1': '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/test/uong-tra.jpg', "video_0": '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/test/tra-sen3.jpg', 'video_2': '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/test/tra-sen2.jpg'}

        # img_des = {'video_1': 'Ông **Thân Dỹ Ngữ**, Giám đốc Công ty TNHH Hiệp Thành, là người tiên phong trong việc đưa **trà Việt Nam** vào thị trường **châu Âu**. Ông đã thành công trong việc khôi phục **niềm tin** của khách hàng quốc tế.', 'video_0': '**Trà Việt Nam** đang dần khẳng định vị thế trên thị trường quốc tế. Các sản phẩm cao cấp như **trà oolong ướp hoa sen** và **trà xanh ướp hoa sen** được bán tại **Mariage Frères**.', 'video_3':'Việt Nam hiện có khoảng **120.000 héc ta** diện tích trồng trà. Mục tiêu mở rộng lên **135.000-140.000 héc ta** vào năm **2030**, với tỷ lệ trà an toàn đạt **75%**.', 'video_2': 'Ngành trà Việt Nam đã có **lịch sử xuất khẩu** từ thế kỷ 17. Sự tham gia của các công ty nước ngoài như **Công ty Đông Ấn Hà Lan** và **Anh** đã góp phần vào sự phát triển này.'}
        # img_abbreviation = {'video_1': {'TNHH': 'Trách Nhiệm Hữu Hạn', 'châu Âu': 'châu Âu', 'niềm tin': 'niềm tin'}, 'video_0': {'Trà Việt Nam': 'Trà Việt Nam', 'Mariage Frères': 'Mariage Frères'}, 'video_3': {'120.000 héc ta': 'một trăm hai mươi nghìn héc ta', '135.000-140.000 héc ta': 'một trăm ba mươi lăm nghìn đến một trăm bốn mươi nghìn héc ta', '2030': 'hai nghìn không trăm ba mươi', '75%': 'bảy mươi lăm phần trăm'}, 'video_2': {'lịch sử xuất khẩu': 'lịch sử xuất khẩu', 'Công ty Đông Ấn Hà Lan': 'Công ty Đông Ấn Hà Lan', 'Anh': 'Anh'}}
        # vipath = {'video_1': '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/01e4992a-6ecf-4447-84e8-c24ea6e3fcf5/uong-tra-2-copy.jpg', "video_0": '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/01e4992a-6ecf-4447-84e8-c24ea6e3fcf5/screenshot-54-22892885959342895322244.png', 'video_3':'/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/01e4992a-6ecf-4447-84e8-c24ea6e3fcf5/tra-sen3-copy.jpg', 'video_2': '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/01e4992a-6ecf-4447-84e8-c24ea6e3fcf5/tra-sen2-copy.jpg'}

        audios = {}
        list_des = []
        list_overlay_image = []
        list_duration = []
        list_duration_text = []
        list_duration_audio = []
        duration_audio = 0
        duration_text = 0
        for j, (v_id, des) in enumerate(img_des.items()):
            duration = 0
            sub_des_rewrite = des
            if v_id in img_abbreviation:
                for k, v in img_abbreviation[v_id].items():
                    sub_des_rewrite = sub_des_rewrite.replace(k ,v)
            sub_des_rewrite = sub_des_rewrite.replace(". ", "\n").split("\n")

            sub_des = des.replace(". ", "\n").split("\n")
            for i, sd in enumerate(sub_des_rewrite):
                output_dir = await self.ttsw(text=regex.sub(r'[\*\*]', '', sd.rstrip(". ")), output_dir=sees_audio_dir, reference_path=[f"{DIR}/StyleTTS2/reference_audio/vn_1.wav"])
                audios[f"{v_id}_{i}"] = output_dir
                duration_audio += (len(sd.split())//5 + self.time_delay)*1000 + 600
                list_duration_audio.append(duration_audio)

                list_des.append(sub_des[i])
                duration_text += (len(sd.split())*0.2 + self.time_delay)
                list_duration_text.append(round(duration_text, 2))

                duration += (len(sd.split())//4.5 + self.time_delay)     

            list_overlay_image.append(vipath[v_id])
            list_duration.append(duration)
            self.update_status(sess_id, "video", str(datetime.now()), {}, 10 + round((j+1)*60/len(img_des),2) , "running")
        list_duration[-1] = list_duration[-1] + 2

        overlay_path = f"{sess_final_dir}{os.sep}overlay_video.mp4"
        result = await self.VEW.overlay_image(self.bg_image_path, list_overlay_image, list_duration, overlay_path, False)
        bg_sz = result["bg_size"]
        self.update_status(sess_id, "video", str(datetime.now()), {}, 80, "running")

        overlay_text_path = f"{sess_final_dir}{os.sep}overlay_text_video.mp4"
        result = await self.VEW.add_text(title_updated, list_des, bg_sz, overlay_path, overlay_text_path, False, [0] + list_duration_text)
        self.update_status(sess_id, "video", str(datetime.now()), {}, 90, "running")

        final_video_audio_file = f"{sess_final_dir}{os.sep}final_video.mp4"
        result = await self.VEW.add_audio(overlay_text_path, list(audios.values()), [200] + list_duration_audio[:-1], f"{DIR}/data/audio_background/ba2.mp3", final_video_audio_file)

        return {"success": True, "result_path": final_video_audio_file}

if __name__=="__main__":
    SECRET_KEY     = os.getenv('SECRET_KEY', "MMV")
    token_openai   = os.getenv('API_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5Ijoic2stcHJvai1QSDNHNnlMVEticmdvaU9ieTA4YlVMNHc0eVYxR3NJa25IeEltTl9VMFI1WmVsOWpKcDI0MzZuNUEwOTdVdTVDeXVFMDJha1RqNVQzQmxia0ZKX3dJTUw2RHVrZzh4eWtsUXdsMTN0b2JfcGVkV1c0T1hsNzhQWGVIcDhOLW1DNjY1ZE1CdUlLMFVlWEt1bzRRUnk2Ylk1dDNYSUEifQ.2qjUENU0rafI6syRlTfnKIsm6O4zuhHRqahUcculn8E')
    api_key_openai = jwt.decode(token_openai, SECRET_KEY, algorithms=["HS256"])["api_key"]

    TOKEN_GEM = os.getenv('API_GEM_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5IjoiQUl6YVN5Q1BKSHNJYUxXaGdMakllQkZVS3E4VHFrclRFdWhGd2xzIn0.7iN_1kRmOahYrT7i5FUplOYeda1s7QhYzk-D-AlgWgE')
    api_key_gem = jwt.decode(TOKEN_GEM, SECRET_KEY, algorithms=["HS256"])["api_key"]

    VG = VideoGeneration(api_key_openai=api_key_openai, api_key_gem=api_key_gem)

    sess_id = "test"
    query = "Trong số hơn 800 loại trà đến từ 36 quốc gia và vùng lãnh thổ có mặt tại Pháp cũng có tên trà của Việt Nam. Bất ngờ hơn nữa, trong đó có hai loại là trà ô long ướp hoa sen và trà xanh ướp hoa sen được thương hiệu Mariage Frères nổi tiếng xếp vào dòng sản phẩm cao cấp nhất, với giá bán hơn 1.000 euro/ký. Ở Kẻ Chợ - tên gọi dân gian chung của kinh thành Thăng Long vào thế kỷ 17 - có một khu vực dành cho các công ty và doanh nhân nước ngoài. Sớm nhất là thương điếm của Công ty Đông Ấn Hà Lan được mở vào năm 1637, tiếp đến là thương điếm của Công ty Đông Ấn Anh được lập vào năm 1863, sau đó đến các nước khác. Trà Việt Nam có lẽ đã bắt đầu được xuất khẩu sang phương Tây thông qua các công ty của Hà Lan và Anh này. Mức tăng trưởng của ngành trà ngày càng cao do lối sống thay đổi và người tiêu dùng nhận thức cao về việc uống trà có lợi cho sức khỏe. Vào danh mục trà cao cấp với giá bán hơn 1.000 euro mỗi ký Theo báo cáo của Guillaume Capus, chuyến hàng trà Đông Dương đầu tiên xuất khẩu sang Pháp là vào năm 1893. Năm 1899, trà Đông Dương được bán tại Paris (Pháp) và một số nước châu Âu, tổng khối lượng xuất khẩu là 131.391 ký, sau đó tăng lên mức 180.000 ký vào năm 1900. Trong số hơn 800 loại trà đến từ 36 quốc gia và vùng lãnh thổ hiện có mặt tại Pháp cũng có tên trà của Việt Nam. Bất ngờ hơn nữa, trong đó có hai loại là trà oolong ướp hoa sen và trà xanh ướp hoa sen được thương hiệu Mariage Frères nổi tiếng xếp vào dòng sản phẩm cao cấp nhất, với giá bán hơn 1.000 euro/ký. Người đưa được trà Việt Nam lên kệ của Mariage Frères là ông Thân Dỹ Ngữ, Giám đốc Công ty TNHH Hiệp Thành - doanh nghiệp sản xuất nông sản hữu cơ, chuyên xuất khẩu trà và nông sản hữu cơ sang thị trường Liên minh châu Âu và Mỹ. Ông cũng là thành viên Hiệp hội Nông nghiệp hữu cơ Việt Nam; là một trong những người sáng lập Liên minh Trà đặc sản hữu cơ Việt Nam (VOSTEA)."

    sess_id = "aaaa"
    img_des = {'video_1': '**Trà Việt Nam** đã bắt đầu được **xuất khẩu sang phương Tây** từ thế kỷ 17. Ông **Thân Dỹ Ngữ**, Giám đốc Công ty TNHH Hiệp Thành, đã thành công trong việc **quảng bá trà Việt Nam** ra thế giới.', 'video_0': 'Hai loại **trà ô long ướp hoa sen** và **trà xanh ướp hoa sen** của Việt Nam được thương hiệu **Mariage Frères** xếp vào dòng sản phẩm **cao cấp nhất**. Giá bán lên tới **hơn 1.000 euro/ký**. Ngành trà Việt Nam đang **tăng trưởng** nhờ lối sống thay đổi và nhận thức cao về **lợi ích sức khỏe** của việc uống trà.', 'video_2': 'Việt Nam hiện có khoảng **120.000 héc ta** diện tích trồng trà. Mục tiêu mở rộng lên **135.000-140.000 héc ta** vào năm 2030.'}
    vipath = {'video_1': '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/test/uong-tra.jpg', 'video_0': '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/test/tra-sen3.jpg', 'video_2': '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/test/tra-sen2.jpg'}
    title = "Chuyện một doanh nhân đưa trà Việt sang Paris"

    sess_id = "test"
    img_des = {'video_0': '**Tín dụng tại TP Hồ Chí Minh đã đạt 4,102 triệu tỉ đồng**, tăng 3.89% so với cuối năm 2024. Điều này cho thấy **sự phục hồi mạnh mẽ của nền kinh tế**. Tốc độ tăng trưởng tín dụng trong 5 tháng đầu năm 2025 **cao gấp đôi so với cùng kỳ năm 2023 và 2024**. Sự tăng trưởng này nhờ vào **môi trường kinh doanh thuận lợi và chính sách tiền tệ linh hoạt**. Các doanh nghiệp đang **mở rộng quy mô và tăng cường đầu tư trở lại**, thể hiện niềm tin tích cực vào triển vọng kinh tế.'}
    vipath = {'video_0': '/home/mq/disk2T/son/code/GitHub/MV_VTV/src/static/images/test/1.jpg'}
    title = "Tín dụng tại TP Hồ Chí Minh, vượt mốc 4.1 triệu tỉ đồng, phản ánh đà phục hồi mạnh mẽ, của nền kinh tế"
    asyncio.run(VG.run(sess_id, title, img_des, vipath))