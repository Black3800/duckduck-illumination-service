from zenggebulb import ZenggeBulb
from os import environ
from time import sleep
from multiprocessing import Process

from typing import Union
from fastapi import FastAPI, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

import connectivity

import json

app = FastAPI()
bulb = ZenggeBulb(environ["BULB_IP"])
sunrise_process = None
sunrise_process_pool = []

class Power(BaseModel):
    on: bool

class Sunrise(BaseModel):
    time_unit: float

class HSLColor(BaseModel):
    h: int
    s: int
    l: int

class HSLColorStep(BaseModel):
    h: int
    s: int
    l: int
    step: int

class CCTColor(BaseModel):
    temp: int
    brightness: int

class WifiSSID(BaseModel):
    ssid: str
    password: str


def ensure_no_sunrise():
    global sunrise_process
    global sunrise_process_pool
    print(sunrise_process)
    if sunrise_process != None:
        sunrise_process.kill()

    print(sunrise_process_pool)
    if len(sunrise_process_pool) > 0:
        for p in sunrise_process_pool:
            p.kill()

    sunrise_process = None
    sunrise_process_pool = []


@app.get("/connectivity/scan")
def get_scan():
    result = connectivity.scan().decode("utf-8")
    result = result.split("\n")
    wifi_list = []
    for i in range(1, len(result)-1):
        entry = result[i].split("\t")
        if entry[3].find("PSK") != -1 and len(entry[4].replace("\\\\", "")) > 0:
            wifi_list.append(entry)
    return Response(content=json.dumps(wifi_list), media_type="application/json")


@app.post("/connectivity/connect")
def post_connect(data: WifiSSID):
    wifi = jsonable_encoder(data)
    connectivity.connect(wifi["ssid"], wifi["password"])
    return Response(content=json.dumps({"status": "ok"}), media_type="application/json")


@app.post("/power")
def post_power(data: Power):
    ensure_no_sunrise()
    power = jsonable_encoder(data)
    if bulb.set_power(power["on"]):
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")


@app.post("/hsl")
def post_hsl(data: HSLColor):
    ensure_no_sunrise()
    hsl = jsonable_encoder(data)
    if bulb.set_hsl(hsl["h"], hsl["s"], hsl["l"]):
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")


@app.post("/hsl_step")
def post_hsl(data: HSLColorStep):
    ensure_no_sunrise()
    hsl = jsonable_encoder(data)
    if bulb.set_hsl_step(hsl["h"], hsl["s"], hsl["l"], hsl["step"]):
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")


@app.post("/cct")
def post_cct(data: CCTColor):
    ensure_no_sunrise()
    cct = jsonable_encoder(data)
    if bulb.set_cct(cct["temp"], cct["brightness"]):
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")


@app.post("/sunrise")
def post_sunrise(data: Sunrise):
    global sunrise_process
    ensure_no_sunrise()
    sunrise = jsonable_encoder(data)
    sunrise_process = Process(target=start_sunrise, args=(sunrise["time_unit"],))
    sunrise_process.start()
    print(f"x: {sunrise_process}")
    return Response(content=json.dumps({"status": "ok"}), media_type="application/json")


def start_sunrise(time_unit):
    global sunrise_process
    global sunrise_process_pool
    print(f"start {sunrise_process}")
    # if time_unit < 1:
    #     time_unit = 1
    h = 0
    s = 100
    l = 0
    for i in range(0, 30):
        if i % 2 == 0:
            l += 1
        if i % 3 == 0:
            h += 1 
        print([h, s, l])
        p = Process(target=bulb.set_hsl_norecv, args=(h, s, l))
        p.daemon = True
        sunrise_process_pool.append(p)
        p.start()
        p.join()
        sunrise_process_pool.pop()
        sleep(time_unit)
    print(f"done: {h}, {s}, {l}")
    h = 10
    s = 100
    l = 15
    for i in range(0, 20):
        if i % 4 == 0:
            h += 1
        print([h, s, l])
        p = Process(target=bulb.set_hsl_norecv, args=(h, s, l))
        p.daemon = True
        sunrise_process_pool.append(p)
        p.start()
        p.join()
        sunrise_process_pool.pop()
        sleep(time_unit)
    print(f"done: {h}, {s}, {l}")
    h = 15
    s = 100
    l = 15
    for i in range(0, 35):
        s -= 1
        print([h, s, l])
        p = Process(target=bulb.set_hsl_norecv, args=(h, s, l))
        p.daemon = True
        sunrise_process_pool.append(p)
        p.start()
        p.join()
        sunrise_process_pool.pop()
        sleep(time_unit)
    print(f"done: {h}, {s}, {l}")
    cct = -1
    brightness = 1
    for i in range(0, 40):
        cct += 1
        if i % 4 == 0:
            brightness += 1
        print([cct, brightness])
        p = Process(target=bulb.set_cct_norecv, args=(cct, brightness))
        p.daemon = True
        sunrise_process_pool.append(p)
        p.start()
        p.join()
        sunrise_process_pool.pop()
        sleep(time_unit)
    cct = 40
    brightness = 12
    for i in range(0, 60):
        cct += 1
        brightness += 1
        print([cct, brightness])
        p = Process(target=sunrise_cct, args=(cct, brightness))
        p.daemon = True
        sunrise_process_pool.append(p)
        p.start()
        p.join()
        sleep(time_unit)
    sunrise_process_pool = []
    sunrise_process = None
    print("done")

def sunrise_hsl(h, s, l):
    global sunrise_process
    # if sunrise_process == None:
    #     return

    bulb.set_hsl_norecv(h, s, l)

def sunrise_cct(cct, brightness):
    global sunrise_process
    # print(sunrise_process)
    # if sunrise_process == None:
    #     return

    bulb.set_cct_norecv(cct, brightness)