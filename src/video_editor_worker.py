import os
import cv2
import asyncio
import subprocess
import unicodedata
import re as regex
from PIL import ImageFont
from itertools import accumulate

import sys
from pathlib import Path 
FILE = Path(__file__).resolve()
DIR = FILE.parents[0]
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

def split_tittle(title: str, size_title: list, font_type: str):
    w_title, h_title = size_title

    if "%" in title:
        title = title.replace("%", " phần trăm")
        
    sub_title_original = title.split(", ")
    sub_title = regex.sub(r'[\*\*.]', '', title).split(", ")
    h_sub_title = h_title/len(sub_title)

    sub_title_content = []
    sub_title_idx = []
    [(sub_title_content.append(v), sub_title_idx.append(i)) for i, v in sorted(enumerate(sub_title), key=lambda x: len(x[1]), reverse=True)]
    # print(sub_title_idx)

    max_idex_no_changed = len(sub_title)
    idx_fz = {}
    for idx, stl in zip(sub_title_idx, sub_title_content):
        if idx in idx_fz:
            continue
        font_sz = 30
        font = ImageFont.truetype(font_type, size=font_sz)
        length_stitle = font.getlength(stl)
        height_stitle = sum(font.getmetrics())
        # print(stl)
        # print(height_stitle)
        # print(length_stitle)

        if length_stitle > w_title or height_stitle > h_sub_title:
            for fz in reversed(range(18,30)):
                font = ImageFont.truetype(font_type, size=fz)
                length_stitle = font.getlength(stl)
                height_stitle = sum(font.getmetrics())
                if length_stitle < w_title and height_stitle < h_sub_title:

                    break
            # print(font.size)
            # print(height_stitle)
            # print(length_stitle)

        elif length_stitle < w_title and height_stitle < h_sub_title:
            for fz in range(31,40):
                font = ImageFont.truetype(font_type, size=fz)
                length_stitle = font.getlength(stl)
                height_stitle = sum(font.getmetrics())
                if length_stitle > w_title or height_stitle > h_sub_title:
                    font = ImageFont.truetype(font_type, size=fz-1)
                    height_stitle = sum(font.getmetrics())
                    length_stitle = font.getlength(stl)
                    break
        #     print(font.size)
        #     print(height_stitle)
        #     print(length_stitle)
        # print("---------")

        for i in range(idx, max_idex_no_changed):
            idx_fz[i] = [font.size, height_stitle]
            h_title -= height_stitle
            h_sub_title = h_title/(len(sub_title)-len(idx_fz)+10e-5)

        max_idex_no_changed = idx

    return dict(zip(sub_title_original, dict(sorted(idx_fz.items())).values()))

def get_bold_text(sub_title_fz: dict):
    list_subtile = []
    list_bold = []
    for stl, fz in sub_title_fz.items():
        bold_text = regex.findall(r'\*\*(.*?)\*\*', stl)
        normal_texts = []
        bold_flag = []
        if bold_text:
            pattern = "|".join(map(regex.escape, bold_text))
            normal_texts = regex.split(pattern, regex.sub(r'[\*\*.]', '', stl))
            bold_flag = [0]*len(normal_texts)
            i = 1
            for bt in bold_text:
                normal_texts.insert(i, bt)
                bold_flag.insert(i,1)
                i += 2
        else:
            normal_texts.append(stl)
            bold_flag = [0]*len(normal_texts)

        [(normal_texts.pop(j), bold_flag.pop(j)) for j, t in enumerate(normal_texts) if not t]

        list_subtile.append(normal_texts)
        list_bold.append(bold_flag)
    return list_subtile[::-1], list_bold[::-1]

def count_accent(word):
    # normalized = unicodedata.normalize('NFD', word)
    num_above = 0
    num_below = 0
    char_tail = ["g", "p", "y", "q", ","]
    for char in word:
        decomposed = unicodedata.normalize('NFD', char)
        base = decomposed[0]
        accents = decomposed[1:]
        num_below_char = 0
        # num_above_char = 0
        if base in char_tail:
            num_below_char = 1
        # print(decomposed)
        for mark in accents:
            name = unicodedata.name(mark)
            # print(name)
            if 'BELOW' in name:
                num_below_char = 1
            # else:
            #     num_above_char += 1
        # num_above = num_above_char if num_above_char > num_above else num_above
        num_below = num_below_char if num_below_char > num_below else num_below
    return (num_above, num_below)

class VideoEditorWorker(object):
    def __init__(self,):
        super().__init__()
        self.font_text = f'{DIR}/font/arial/arial.ttf'
        self.font_bold = f'{DIR}/font/arial/arialbd.ttf'
        self.font_title = f'{DIR}/font/Anton/Anton-Regular.ttf'
        self.font = ImageFont.truetype(self.font_text, size=18)

    async def get_duration(self, vinput: str):
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration","-of", "default=noprint_wrappers=1:nokey=1", vinput]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {stderr.decode().strip()}")
        return float(stdout.decode().strip())

    async def overlay_image(self, bg_image_path: str, list_overlay_image: list, list_duration: list, output_path: str, fast: bool):
        print(f"----running overlay_image----")
        inputs = []
        infor_input = ""
        infor_overlay = ""
        infor_merge = ""
        last_ov_output = "0:v"
        size_bg = cv2.imread(bg_image_path).shape
        # print(size_bg)
        # exit()
        for i, ovi in enumerate(list_overlay_image):
            size_ovi = cv2.imread(ovi).shape
            # print(size_ovi)
            inputs += ["-loop", "1", "-t", f"{list_duration[i]}", "-i", ovi]
            if size_bg[0] > size_bg[1]:
                if size_ovi[0] < size_bg[0]:
                    fix_size = f"scale=(1-0.1*sin(2*PI*t/{list_duration[i]*3}))*iw:(1-0.1*sin(2*PI*t/{list_duration[i]*3}))*ih:eval=frame,pad=iw*{size_bg[0]}/ih:{size_bg[0]}:(ow-iw)/2:(oh-ih)/2"
                else:
                    fix_size = f"scale=(1-0.1*sin(2*PI*t/{list_duration[i]*3}))*iw*{size_bg[0]}/ih:(1-0.1*sin(2*PI*t/{list_duration[i]*3}))*{size_bg[0]}:eval=frame"
                infor_input += f"[{i+1}:v]{fix_size},crop={size_bg[1]}:{size_bg[0]}:(in_w-out_w)/2:(in_h-out_h)/2,format=rgba[ov{i+1}];"
            else:
                if size_ovi[1] < size_bg[1]:
                    fix_size = f"scale=(1-0.1*sin(2*PI*t/{list_duration[i]*3}))*iw:(1-0.1*sin(2*PI*t/{list_duration[i]*3}))*ih:eval=frame,pad={size_bg[1]}:ih*{size_bg[1]}/iw:(ow-iw)/2:(oh-ih)/2"
                else:
                    fix_size = f"scale=(1-0.1*sin(2*PI*t/{list_duration[i]*3}))*{size_bg[1]}:(1-0.1*sin(2*PI*t/{list_duration[i]*3}))*ih*{size_bg[1]}/iw:eval=frame"
                infor_input += f"[{i+1}:v]{fix_size},crop={size_bg[1]}:{size_bg[0]}:(in_w-out_w)/2:(in_h-out_h)/2,format=rgba[ov{i+1}];"

            next_ov_output = f"v{i}{i+1}"
            infor_overlay += f"[ov{i+1}][{last_ov_output}]overlay=x='(W-w)/2':y='(H-h)/2'[{next_ov_output}];"
            infor_merge += f"[{next_ov_output}]"

        if fast:
            cmd = ['ffmpeg', '-y', '-loop', '0', '-i', bg_image_path] + inputs + ['-filter_complex', f'{infor_input}{infor_overlay}{infor_merge} concat=n={len(list_overlay_image)}:v=1:a=0', '-t', str(sum(list_duration)), '-c:v', "h264_nvenc", "-preset", "fast", "-crf", "23", "-c:a", "copy", output_path]
        else:
            cmd = ['ffmpeg', '-y', '-loop', '0', '-i', bg_image_path] + inputs + ['-filter_complex', f'{infor_input}{infor_overlay}{infor_merge} concat=n={len(list_overlay_image)}:v=1:a=0', '-t', str(sum(list_duration)), '-c:v', 'libx264', output_path]

        print(f"----cmd: {cmd}")
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        stdout, stderr = await proc.communicate()
        # subprocess.run(cmd, check=True)
        return {"success": True, "bg_size": size_bg[:2][::-1]}

    # async def add_static_text(self, texts: list, img_size: list):


    async def add_text(self, title: str, texts: list, img_size: list, video_input_path: str, video_output_path: str, fast: bool, start_time: list=[0], text_position: list=[65, 65, 40, 160, 615, 720]):
        print(f"----running add_text----")
        padding_left, padding_right, y_title_top, y_title_bottom, y_sub_top, y_sub_bottom = text_position
        # print(texts)
        # print(start_time)
        # padding_left = 65
        # padding_right = 65
        # y_title_bottom = 160
        text_infos = ""
        #--------------------split title----------------------
        size_title = [img_size[0]-padding_left-padding_right, y_title_bottom-y_title_top]
        # print(size_title)
        sub_title_fz = split_tittle(title, size_title, self.font_title)
        # print(sub_title_fz)
        
        for stl, fz in reversed(sub_title_fz.items()):
            text_infos += f"drawtext=text={stl}:fontcolor=white:fontsize={fz[0]}:fontfile={self.font_title}:x={padding_left} + ({size_title[0]}-text_w)/2:y={y_title_bottom} - {fz[1]},"
            y_title_bottom -= fz[1]

        # list_subtile, list_bold = get_bold_text(sub_title_fz)
        # for i, (stl, fz) in enumerate(reversed(sub_title_fz.items())):
        #     font_ttl = ImageFont.truetype(self.font_title, size=fz[0])
        #     w_space = font_ttl.getlength(" ")
        #     w_stl = font_ttl.getlength(regex.sub(r'[\*\*.]', '', stl))
        #     w_split_stl = 0
        #     padding_w_title = (size_title[0]-w_stl)/2
        #     for j, s in enumerate(list_subtile[i]):
        #         if list_bold[i][j]:
        #             fontcolor = "yellow"
        #         else:
        #             fontcolor = "white"
        #         text_infos += f"drawtext=text={s}:fontcolor={fontcolor}:fontsize={fz[0]}:fontfile={self.font_title}:x={padding_left} + {w_split_stl} + {padding_w_title}:y={y_title_bottom} - {fz[1]},"
        #         w_split_stl += font_ttl.getlength(s) - padding_w_title + w_space
        #     y_title_bottom -= fz[1]
        #/////////////////////////////////////////////////////

        # text_infos = f"drawtext=text={text}:fontcolor=yellow:fontsize=h/30:box=1:boxcolor=black@0.2:boxborderw=1:x=(w-text_w)/2:y='h-(t*50)':alpha='if(lt(t\,0.5)\, 0\, if(lt(t\,2)\, (t\-0.5)/1.5\, 1))'"
        # text_infos = f"drawtext=text={text}:fontcolor=yellow:fontsize=h/30:x=(w-text_w)/2:y='h-200*(1-exp(-2.3*t))':alpha='if(lt(t\,0.5)\, 0\, if(lt(t\,2)\, (t\-0.5)/1.5\, 1))'"
        
        font_sz = img_size[0]*0.04 if img_size[0]<img_size[1] else img_size[1]*0.03
        self.font = ImageFont.truetype(self.font_text, size=font_sz)
        h_word = sum(self.font.getmetrics())
        w_space = self.font.getlength(" ")*1.2
        for j, st in enumerate(texts):
            # last_time_end = 0
            # sentences = text.replace(". ", ".\n").split("\n")

            # for k, st in enumerate(sentences):
                # if k+1 == len(sentences):
                #     spare_time = 2
                # else:
                #     spare_time = 1

            bold_index = []
            [bold_index.extend(range(m.start(1)-1, m.end(1)+5)) for m in regex.finditer(r'\*\*(.*?)\*\*', st)] # -2: for 2 "**" in left; +4: 1 for last letter, 2 for 2 "**" in right and 1 for the space, and 1 for word_index set len(w) -> word_index -1 == add 1 for range bold_index 
            word_index = list(accumulate([len(w)+1 for w in st.split()]))

            # list_word = regex.sub(r'[^\w\s]', '', st).split()
            list_word = regex.sub(r'[\*\*]', '', st.rstrip(". ")).split()
            # time_end = 0.2*len(list_word) + 2 + last_time_end + start_time[j]
            time_end = start_time[j+1]
            x_word = padding_left
            x_word_end = img_size[0] - padding_right

            w_sentence = self.font.getlength(st)
            w_text_area = x_word_end - x_word
            num_row_available = (y_sub_bottom - y_sub_top)/h_word
            num_row_current = w_sentence/w_text_area + 1
            num_row_spare = max(num_row_available - num_row_current, 0)

            y_word = (img_size[1] - y_sub_top - (1 + num_row_spare/2)*h_word)
            # print(list_word)
            for i, word in enumerate(list_word):
                if "%" in word:
                    word = word.replace("%", " phần trăm")
                if word.endswith(","):
                    word = word.replace(",", "\n")

                # print(word)
                num_above, num_below = count_accent(word)
                # print(num_below)
                num_accent = (num_above - num_below)

                if word_index[i] in bold_index:
                    fontfile = self.font_bold
                    fontcolor = 'yellow'
                    w_s = w_space * (0.8 + len(word)/6)
                    accent_ratio = num_accent/5

                    w_bold_word = 0
                    for bi in range(i,min(i+3, len(word_index))):
                        # print(f"----bi: {bi}")
                        if word_index[bi] in bold_index:
                            w_bold_word += self.font.getlength(list_word[bi]) + w_s

                    if x_word + w_bold_word - w_s > x_word_end:
                        x_word = padding_left
                        y_word -= h_word

                else:
                    fontfile = self.font_text
                    fontcolor = 'white'
                    w_s = w_space
                    accent_ratio = num_accent/5.5
                
                w_word = self.font.getlength(word)
                if x_word + w_word > x_word_end:
                    x_word = padding_left
                    y_word -= h_word
                # wt = round(i*0.2,2) + last_time_end + start_time[j]
                wt = round(i*0.2,2) + start_time[j]
                
                # text_infos += f"drawtext=text='{word}':fontcolor={fontcolor}:fontsize={self.font.size}:fontfile={fontfile}:x={x_word}:y='h - ({y_word}+text_h+{num_accent}*text_h/4)*(1/(1+exp(-4*(t-{wt})+1)))':alpha='if(lt(t\,{wt+0.3})\, 0\, if(lt(t\,{wt+1})\, (t\-0.5)/{wt+0.5}\, 1))':enable='between(t,{wt},{time_end})',"
                text_infos += f"drawtext=text='{word}':fontcolor={fontcolor}:fontsize={self.font.size}:fontfile={fontfile}:x={x_word}:y='(h-{y_word}+{h_word}) - ({h_word}+text_h+{accent_ratio}*text_h)*(1/(1+exp(-15*(t-{wt})+10)))':alpha='if(lt(t\,{wt+0.6})\, 0\, if(lt(t\,{wt+1})\, (t\-0.6)/{wt+0.6}\, 1))':enable='between(t,{wt},{time_end})',"
                
                if "\n" in word:
                    x_word = padding_left
                    y_word -= h_word
                else:
                    x_word += w_word + w_s

            # last_time_end = time_end
        # exit()

        if fast:
            cmd = ['ffmpeg', "-y", "-i", video_input_path, "-vf", text_infos[:-1], "-c:v", "h264_nvenc", "-preset", "fast", "-crf", "23", "-c:a", "copy", video_output_path]
        else:
            cmd = ['ffmpeg', "-y", "-i", video_input_path, "-vf", text_infos[:-1], "-c:v", "libx264", "-c:a", "copy", video_output_path]
        # print(f"----cmd: {cmd}")
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        stdout, stderr = await proc.communicate()
        # subprocess.run(cmd, check=True)
        return {"success": True}

    async def add_audio(self, video_input_path: str, list_audio_path: list, list_audio_time: list, audio_background_path: str, video_output_path: str):   #audio time in miliseconds
        print(f"----running add_audio----")
        if len(list_audio_path)!=len(list_audio_time):
            return {"success": False, "error": "The number of time start and the number of audio path is not the same"}
        a_inputs = ["-i", video_input_path]
        a_info = ""
        a_ids = ""
        list_audio_time += [-1]
        for i, inp in enumerate(list_audio_path):
            # duration_audio = float(ffmpeg.probe(inp)["format"]["duration"])
            # n_audio = int((list_audio_time[i+1]-list_audio_time[i])*1e-3//duration_audio)-1 if list_audio_time[i+1]>=0 else 0
            # a_inputs += ["-stream_loop", f"{n_audio}", "-i", inp]
            a_inputs += ["-stream_loop", "0", "-i", inp]
            a_info += f"[{i+1}:a]adelay={list_audio_time[i]}|{list_audio_time[i]},volume=100[a{i+1}];"
            a_ids += f"[a{i+1}]"
        # adding background audio
        duration_audio = await self.get_duration(audio_background_path)
        duration_video_input = await self.get_duration(video_input_path)
        n_audio = int(duration_video_input//duration_audio)-1 # subtract 1 because it is once itself
        a_inputs += ["-stream_loop", f"{n_audio}", "-i", audio_background_path]
        a_info += f"[{len(list_audio_path)+1}:a]adelay=0|0,volume=5[a{len(list_audio_path)+1}];"
        a_ids += f"[a{len(list_audio_path)+1}]"

        cmd = ['ffmpeg', '-y'] + a_inputs + ['-filter_complex', f'{a_info}{a_ids}amix=inputs={len(list_audio_path)+1}[a]', '-map', '0:v', '-map', '[a]', "-c:v", "copy", "-c:a", "aac", "-shortest", video_output_path]
        print(f"----cmd: {cmd}")
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        stdout, stderr = await proc.communicate()
        return {"success": True}

if __name__=="__main__":
    VEW = VideoEditorWorker()
    bg_image_path = "./data_test/bg2.png"
    list_overlay_image = ["./data_test/tra-sen2.png","./data_test/tra-sen3.png","./data_test/uong-tra.png", "./data_test/image_2025_03_05T02_30_16_004Z.png"]
    list_duration = [3,4,5,6]
    output_path = "output.mp4"
    # asyncio.run(VEW.overlay_image(bg_image_path, list_overlay_image, list_duration, output_path, True))

    title = "Chuyện một doanh nhân, đưa trà Việt sang Paris"
    text = "**Trà Việt Nam** đã có mặt trên thị trường quốc tế từ thế kỷ 17, nhờ vào các công ty Đông Ấn Hà Lan và Anh. \nGần đây, **ông Thân Dỹ Ngữ**, Giám đốc Công ty TNHH Hiệp Thành, đã thành công trong việc đưa trà Việt Nam vào kệ của **Mariage Frères**, một thương hiệu trà cao cấp nổi tiếng, giúp quảng bá trà Việt Nam ra thế giới."
    img_size = [450,800]
    video_input_path = "output.mp4"
    video_output_path = "output1.mp4"
    fast = True
    start_time = [0, 5]
    asyncio.run(VEW.add_text(title, [text], img_size, video_input_path, video_output_path, fast, start_time))