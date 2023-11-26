from zenggebulb import ZenggeBulb
from os import environ
from time import sleep, monotonic
from multiprocessing import Process
import json

from typing import Union
from fastapi import FastAPI, Response
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import connectivity

from datetime import timedelta
from dotenv import load_dotenv

load_dotenv('bulb.conf')

app = FastAPI()
bulb_ip = environ.get("BULB_IP") or None
bulb = ZenggeBulb(bulb_ip) if bulb_ip != None else ZenggeBulb('127.0.0.1')
sunrise_process = None
sunrise_process_pool = []
origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BulbConnect(BaseModel):
    ip: str

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


active_color = None

def with_bulb_connected(func):

    def wrapper_func():
        if (bulb == None) or (bulb.host == '127.0.0.1'):
            return on_no_bulb()
        else:
            return func()

    def on_no_bulb():
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")
    return wrapper_func


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


def save_bulb_ip(ip):
    f = open("bulb.conf", "w")
    f.write(f"BULB_IP={ip}")
    f.close()


@app.post("/bulb-connect")
def post_connect(data: BulbConnect):
    global bulb
    global bulb_ip
    connect = jsonable_encoder(data)
    bulb_test = ZenggeBulb(connect["ip"])
    try:
        bulb_test.get_state()
        bulb = bulb_test
        bulb_ip = connect["ip"]
        save_bulb_ip(connect["ip"])
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    except:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")


@app.get("/connectivity/check")
def get_check():
    result = {
        "online": connectivity.check()
    }
    return Response(content=json.dumps(result), media_type="application/json")


@app.get("/connectivity/scan")
def get_scan():
    result = connectivity.scan().decode("utf-8")
    result = result.split("\n")
    wifi_list = []
    for i in range(1, len(result)-1):
        entry = result[i].split("\t")
        if entry[3].find("WPA2-PSK") != -1 and len(entry[4].replace("\\\\", "")) > 0:
            wifi_list.append(entry)
    return Response(content=json.dumps(wifi_list), media_type="application/json")


@app.post("/connectivity/connect")
def post_connect(data: WifiSSID):
    wifi = jsonable_encoder(data)
    connectivity.connect(wifi["ssid"], wifi["password"])
    return Response(content=json.dumps({"status": "ok"}), media_type="application/json")


@app.post("/power")
@with_bulb_connected
def post_power(data: Power):
    ensure_no_sunrise()
    power = jsonable_encoder(data)
    if bulb.set_power(power["on"]):
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")


@app.post("/hsl")
@with_bulb_connected
def post_hsl(data: HSLColor):
    ensure_no_sunrise()
    hsl = jsonable_encoder(data)
    if bulb.set_hsl(hsl["h"], hsl["s"], hsl["l"]):
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")


@app.post("/hsl_step")
@with_bulb_connected
def post_hsl(data: HSLColorStep):
    ensure_no_sunrise()
    hsl = jsonable_encoder(data)
    if bulb.set_hsl_step(hsl["h"], hsl["s"], hsl["l"], hsl["step"]):
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")


@app.post("/cct")
@with_bulb_connected
def post_cct(data: CCTColor):
    ensure_no_sunrise()
    cct = jsonable_encoder(data)
    if bulb.set_cct(cct["temp"], cct["brightness"]):
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")
    

@app.get("/state")
@with_bulb_connected
def get_state():
    state = bulb.get_state()
    if state:
        return Response(content=json.dumps({"status": "ok", "data": state.toJSON()}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")


@app.post("/sunrise")
@with_bulb_connected
def post_sunrise(data: Sunrise):
    global bulb
    global sunrise_process
    ensure_no_sunrise()
    sunrise = jsonable_encoder(data)
    delay = []
    for i in range(3):
        start_time = monotonic()
        bulb.set_hsl_norecv(0, 100, 1)
        end_time = monotonic()
        delay.append(round(timedelta(seconds=end_time - start_time).microseconds/100000, 3))
        sleep(0.5)
        start_time = monotonic()
        bulb.set_cct_norecv(0, 1)
        end_time = monotonic()
        delay.append(round(timedelta(seconds=end_time - start_time).microseconds/100000, 3))
        sleep(0.5)
    delay = max(delay)
    print(f"delay = {delay}")
    sunrise_process = Process(target=start_sunrise, args=(sunrise["time_unit"] - delay,))
    sunrise_process.start()
    print(f"x: {sunrise_process}")
    return Response(content=json.dumps({"status": "ok"}), media_type="application/json")


def start_sunrise(time_unit):
    global sunrise_process
    global sunrise_process_pool
    print(f"start {sunrise_process}")
    if time_unit < 1:
        time_unit = 1
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


@app.post("/dim")
@with_bulb_connected
def post_sunrise():
    global bulb
    ensure_no_sunrise()
    if bulb.set_hsl(20, 100, 30):
        return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
    else:
        return Response(content=json.dumps({"status": "failed"}), media_type="application/json")

