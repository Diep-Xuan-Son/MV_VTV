from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from typing import List, Union, Tuple, Optional, Type
from fastapi import Query, Form

    
# @dataclass
class InputUrl(BaseModel):
    sess_id: str = ""
    url: str = ""
    
# @dataclass
class InputGen(BaseModel):
    sess_id: str = ""
    title: str = ""
    descriptions: str = ""
    image_paths: str = ""
    
