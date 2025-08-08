import sys 
from pathlib import Path 
FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
if ROOT not in sys.path:
	sys.path.append(str(ROOT))

import os
import time
import json
import shutil 
import logging 
import traceback
from loguru import logger
from fastapi.responses import StreamingResponse, JSONResponse
from functools import wraps

import logging
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logging.basicConfig(
    level=logging.INFO,
    format=formatter._fmt,
    stream=sys.stderr,
)

def check_folder_exist(*args, **kwargs):
	if len(args) != 0:
		for path in args:
			if not os.path.exists(path):
				os.makedirs(path, exist_ok=True)

	if len(kwargs) != 0:
		for path in kwargs.values():
			if not os.path.exists(path):
				os.makedirs(path, exist_ok=True)

def delete_folder_exist(*args, **kwargs):
	if len(args) != 0:
		for path in args:
			if os.path.exists(path):
				if os.path.isfile(path):
					os.remove(path)
				elif os.path.isdir(path):
					shutil.rmtree(path)

	if len(kwargs) != 0:
		for path in kwargs.values():
			if os.path.exists(path):
				if os.path.isfile(path):
					os.remove(path)
				elif os.path.isdir(path):
					shutil.rmtree(path)

# def MyException(name_func: str, logger_: object):
def MyException():
	def decorator(func):
		def inner(*args, **kwargs):
			try:
				value = func(*args, **kwargs)
				return value
			except Exception as e:
				tb_str = traceback.format_exc()
				# logger_.error(f"Failed to add worker: {tb_str}")
				print(f"Failed to add worker: {tb_str}")
				return {"success": False, "error": e}
		return inner
	return decorator

def HTTPException():
	def decorator(func):
		@wraps(func)
		async def inner(*args, **kwargs):
			try:
				value = await func(*args, **kwargs)
				return value
			except Exception as e:
				tb_str = traceback.format_exc()
				# logger_.error(f"Failed to add worker: {tb_str}")
				print(f"Error submitting task: {tb_str}")
				return JSONResponse(status_code=500, content=str(f"Error processing request: {str(e)}"))
		return inner
	return decorator