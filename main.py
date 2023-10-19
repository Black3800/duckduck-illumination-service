from zenggebulb import ZenggeBulb

from typing import Union
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

app = FastAPI()
bulb = ZenggeBulb("192.168.101.201")

class RGBColor(BaseModel):
    red: int
    green: int
    brightness: int

class CCTColor(BaseModel):
    temp: int
    brightness: int


@app.post("/rgb")
def post_rgb(data: RGBColor):
    rgb = jsonable_encoder(data)
    bulb.set_rgb(rgb.red, rgb.green, rgb.brightness)
    return {"status": "ok"}


@app.post("/cct")
def post_cct(data: CCTColor):
    cct = jsonable_encoder(data)
    bulb.set_cct(cct.temp, cct.brightness)
    return {"status": "ok"}
