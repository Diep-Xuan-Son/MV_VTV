import os
import time
import uuid
import json
import asyncio
import requests
import threading
from PIL import Image
import streamlit as st
from io import BytesIO
from datetime import datetime

if "sess_id" not in st.session_state:
    st.session_state["sess_id"] = str(uuid.uuid4())

if 'images_data' not in st.session_state:
    st.session_state["images_data"] = []

if 'processed_url' not in st.session_state:
    st.session_state["processed_url"] = ""

if 'title_video' not in st.session_state:
    st.session_state["title_video"] = ""

if 'video_path' not in st.session_state:
    st.session_state["video_path"] = ""

def update_status_data(sess_id, type):
    url = "http://localhost:8387/api/getStatus"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    payload = json.dumps({
        "sess_id": sess_id,
        "type": type
    })
    
    res = requests.request("POST", url, headers=headers, data=payload)
    content = res.json()
    
    if res.status_code == 200:
        percent = float(content["percent"])
        status = content["status"]
        text_response = ""
        title = ""
        images_data = []
        if percent==100 and status=="done":
            print(content)
            text_response = "Analyzing Successfully!"
            result = json.loads(content['result'])
            descriptions = result["img_des"]
            image_paths = result["img_path"]
            title = result["title"]

            for i, (v_id, des) in enumerate(descriptions.items()):
                images_data.append({
                    'v_id': v_id,
                    'description': des,
                    'image_path': image_paths[v_id]
                })

        elif status=="error":
            text_response = f"Can't analyze because {json.loads(content['result'])['error']}"
    else:
        percent = 0
        status = "error"
        title = ""
        images_data = []
        text_response = content
    
    return percent, status, text_response, title, images_data

def update_status_video(sess_id, type):
    url = "http://localhost:8387/api/getStatus"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    payload = json.dumps({
        "sess_id": sess_id,
        "type": type
    })
    
    res = requests.request("POST", url, headers=headers, data=payload)
    content = res.json()
    
    if res.status_code == 200:
        percent = float(content["percent"])
        status = content["status"]
        text_response = ""
        video_path = ""
        if percent==100 and status=="done":
            print(content)
            text_response = "Creating Successfully!"
            result = json.loads(content['result'])
            video_path = result["result_path"]

        elif status=="error":
            text_response = f"Can't create video because {json.loads(content['result'])['error']}"
    else:
        percent = 0
        status = "error"
        text_response = content
        video_path = ""
    
    return percent, status, text_response, video_path

def get_data(sess_id: str, url_input: str):
    url = "http://localhost:8387/api/getData"

    headers = {
        'Content-Type': 'application/json'
    }
    
    payload = json.dumps({
        "sess_id": sess_id,
        "url": url_input
    })

    res = requests.request("POST", url, headers=headers, data=payload)

    # if res.status_code == 201:
    #     content = res.json()
    #     descriptions = content["img_des"]
    #     image_paths = content["img_path"]
    #     title = content["title"]
    # else:
    #     descriptions = []
    #     image_paths = []
    #     title = ""

    # images_data = []
    # for i, (v_id, des) in enumerate(descriptions.items()):
    #     # img_pil = Image.open(image_paths[v_id])

    #     # # Skip very small images (likely icons)
    #     # if img_pil.size[0] < 100 or img_pil.size[1] < 100:
    #     #     continue

    #     images_data.append({
    #         'v_id': v_id,
    #         'description': des,
    #         'image_path': image_paths[v_id]
    #     })

    # print(images_data)
    # return title, images_data

def create_video(sess_id, title, images_data):
    v_ids = []
    descriptions = []
    image_paths = []
    for dt in images_data:
        v_ids.append(dt['v_id'])
        descriptions.append(dt['description'])
        image_paths.append(dt['image_path'])

    url = "http://localhost:8387/api/createVideo"

    headers = {
        'Content-Type': 'application/json'
    }

    payload = json.dumps({
        "sess_id": sess_id,
        "title": title,
        "descriptions": json.dumps(dict(zip(v_ids, descriptions))),
        "image_paths": json.dumps(dict(zip(v_ids, image_paths)))
    })

    res = requests.request("POST", url, headers=headers, data=payload)

    # if res.status_code == 201:
    #     content = res.json()
    #     video_path = content["result_path"]
    # else:
    #     video_path = ""

    # return video_path
    
st.set_page_config(page_title="Video Generation", page_icon="🎬", layout="wide")

st.title("Video Generation")
st.markdown("Enter a URL to view its image and text content")
    

st.header("1. Enter Website URL")
with st.form("url_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])

    with col1:
        # URL input
        url_input = st.text_input("Enter URL:", placeholder="https://money.vtv.vn/", label_visibility="collapsed")

    with col2:
        send_button = st.form_submit_button("Send 📨", use_container_width=True)

# Handle user input
if send_button and url_input.strip():
    # Add protocol if missing
    if not url_input.startswith(('http://', 'https://')):
        url_input = 'https://' + url_input

    # Process as URL
    progress_bar = st.progress(0)
    status_text = st.empty()
    with st.spinner("Analyzing URL ..."):
        # st.session_state["title_video"], st.session_state["images_data"] = get_data(st.session_state["sess_id"], url_input)
        thread = threading.Thread(target=get_data, args=(st.session_state["sess_id"], url_input,), daemon=True)
        thread.start()
        st.session_state["processed_url"] = url_input
        while True:
            time.sleep(1)
            percent, status, text_response, st.session_state["title_video"], st.session_state["images_data"] = update_status_data(st.session_state["sess_id"], "data")
            progress_bar.progress(percent/100)
            status_text.text(f"Processing... {percent}%")
            if status == "done":
                st.success(f"✅ {text_response}")
                # st.balloons()
                break
            elif status == "error":
                st.error(f"❌ {text_response}")
        progress_bar.empty()
        status_text.empty()

print(st.session_state["images_data"])
# Display extracted images
if st.session_state["images_data"]:
    st.header("2. Edit Image Descriptions")
    st.success(f"Found {len(st.session_state['images_data'])} images from {st.session_state['processed_url']}")

    
    title = st.text_area(
        "Video title:",
        value=st.session_state["title_video"],
        key=f"title",
        height=80
    )
    
    if st.button(f"Update title", key=f"update_title_button"):
        st.session_state["title_video"] = title
        st.success(f"✅ Update title success!")
        st.rerun()

    for i, img_data in enumerate(st.session_state["images_data"]):
        with st.expander(f"Image {i+1}", expanded=True):
            col1, col2 = st.columns([1, 2])

            with col1:
                if not os.path.exists(img_data['image_path']):
                    uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"], key=f"uploader_key_{i}")
                    if uploaded_file is not None:
                        # Save uploaded file to disk
                        with open(img_data['image_path'], "wb") as f:
                            f.write(uploaded_file.read())
                        st.rerun()

                else:    
                    img_pil = Image.open(img_data['image_path'])
                    st.image(img_pil, caption=f"Image {i+1}", use_container_width=True)
                # Delete Button
                if st.button(f"Delete Image", key=f"delete_button_{i}"):
                    os.remove(img_data['image_path'])
                    st.rerun()

            with col2:
                new_description = st.text_area(
                    "Description:",
                    value=img_data['description'],
                    key=f"desc_{i}",
                    height=100
                )
                
                if st.button(f"Update description", key=f"update_des_button_{i}"):
                    # Update the description in session state
                    st.session_state["images_data"][i]['description'] = new_description
                    st.success(f"✅ Update description success!")
                    st.rerun()

    # Video creation section
    st.header("3. Create Video")
    if st.button("Create Video", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        with st.spinner("Creating video ..."):
            # st.session_state["video_path"] = create_video(st.session_state["sess_id"], st.session_state["title_video"], st.session_state["images_data"])
            thread = threading.Thread(target=create_video, args=(st.session_state["sess_id"], st.session_state["title_video"], st.session_state["images_data"],), daemon=True)
            thread.start()
            st.session_state["processed_url"] = url_input
            while True:
                time.sleep(1)
                percent, status, text_response, st.session_state["video_path"] = update_status_video(st.session_state["sess_id"], "video")
                progress_bar.progress(percent/100)
                status_text.text(f"Processing... {percent}%")
                if status == "done":
                    st.success(f"✅ {text_response}")
                    # st.balloons()
                    break
                elif status == "error":
                    st.error(f"❌ {text_response}")
            progress_bar.empty()
            status_text.empty()

    if os.path.exists(st.session_state["video_path"]):
        col1, col2, col3 = st.columns([1, 1, 2])
        with col2:
            with open(st.session_state["video_path"], 'rb') as video_file:
                video_bytes = video_file.read()
                st.video(video_bytes, format="video/mp4")

# Footer
st.markdown("---")
st.markdown("*Built with DXSON* 🚀")