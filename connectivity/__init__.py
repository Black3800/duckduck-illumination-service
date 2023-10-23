from subprocess import run, PIPE
from time import sleep

class ConnetivityException(Exception):
    pass

def backoff(seconds):
    sleep(seconds)

def scan():
    scanning = True
    delay = 1
    while scanning:
        scan_status = run(["wpa_cli", "-i", "wlan0", "scan"], stdout=PIPE)
        if scan_status == b'OK\n':
            break
        else:
            backoff(delay)
            delay += 1
            if delay > 10:
                raise ConnetivityException("Scan failed")
    scan_result = run(["wpa_cli", "-i", "wlan0", "scan_result"], stdout=PIPE)
    return scan_result.stdout