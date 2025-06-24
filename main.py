import requests
from bs4 import BeautifulSoup
import re
import urllib.request
import os
from urllib.parse import urljoin, urlparse

def save_img(img):
    base_url = "https://cdn-images.vtv.vn"
    img_src = img.get('src')
    if img_src and not (img_src.startswith('http://') or img_src.startswith('https://')):
        img_src = base_url + img.get('src')
    # print(img_src)
    filename = os.path.basename(urlparse(img_src).path)
    path = "images"
    if not os.path.exists(path):
        os.mkdir(path) 
    try:
        urllib.request.urlretrieve(img_src, f"images/{filename}")
    except Exception as e:
        print("Lỗi tải ảnh", e)

def extract_data(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print("Lỗi bs4")

    #save images
    try:
        main = soup.find('div', class_='wrap d_flex vdetail-content__main-detail')
        for img in main.find_all('img'):
            save_img(img)
    except Exception as e:
        print("Lỗi lưu ảnh nội dung",e)

    #save title
    try: 
        h1 = soup.find('h1', class_='name-blog__title')
        title = h1.get_text().replace('\n',' ').replace('\t',' ')
        title = re.sub(r'\s{2,}', ' ', title)
        # print(title)
    except Exception as e:
        print("Lỗi lưu tiêu đề")

    #save content
    try:
        body = soup.find('div', class_='wrap d_flex vdetail-content__main-detail--body')        
        body_text = body.get_text().replace('\n',' ').replace('\t',' ')
        content = re.sub(r'\s{2,}', ' ', body_text)
        # print(content)
    except Exception as e:
        print("Lỗi lấy nội dung")   

    return {title: content}

if __name__ == "__main__":
    url = 'https://money.vtv.vn/hoi-doanh-nhan-tre-viet-nam-se-to-chuc-dien-dan-kinh-te-tu-nhan-nam-2025'
    print(extract_data(url))        