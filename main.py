from zenggebulb import ZenggeBulb
from os import environ

from typing import Union
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

import connectivity

app = FastAPI()
bulb = ZenggeBulb(environ["BULB_IP"])

class HSLColor(BaseModel):
    h: int
    s: int
    l: int

class CCTColor(BaseModel):
    temp: int
    brightness: int


@app.get("/connectivity/scan")
def get_scan():
    return connectivity.scan()


@app.post("/hsl")
def post_hsl(data: HSLColor):
    hsl = jsonable_encoder(data)
    bulb.set_rgb(hsl["h"], hsl["s"], hsl["l"])
    return {"status": "ok"}


@app.post("/cct")
def post_cct(data: CCTColor):
    cct = jsonable_encoder(data)
    bulb.set_cct(cct["temp"], cct["brightness"])
    return {"status": "ok"}
