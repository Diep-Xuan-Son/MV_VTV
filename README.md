# Generate Video
---

## Pretrained
[Click here to get model](https://drive.google.com/drive/folders/1MK35d_Y8cuMphnePkqGhE3plCevDoVch?usp=sharing)

## Installation
```bash
git clone http://git.mqsolutions.vn:8083/MQ-AI/MV_VTV.git
cd MV_VTV
pip install -r requirement.txt
pip install -r requirements_serving.txt
pip install -r requirements_ui.txt
```

## Usage
```bash
cd src
python controller.py
python ui.py
```
## Deployment
```bash
cd docker
# Change information of services in .env file and run command below:
docker-compose -f docker-compose.yml --profile "*" up -d
```
