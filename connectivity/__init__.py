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
        if scan_status.stdout == b'OK\n':
            break
        else:
            backoff(delay)
            delay += 1
            if delay > 10:
                raise ConnetivityException("Scan failed")
    scan_result = run(["wpa_cli", "-i", "wlan0", "scan_result"], stdout=PIPE)
    return scan_result.stdout

def connect(ssid, password):
    run(["sudo", "rfkill", "block", "wifi"])
    run(["sudo", "rfkill", "unblock", "wifi"])
    run(f"sudo sh -c \"echo 'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\ncountry=TH\n' > /etc/wpa_supplicant/wpa_supplicant.conf\"", shell=True)
    run(f"sudo sh -c \"wpa_passphrase '{ssid}' '{password}' >> /etc/wpa_supplicant/wpa_supplicant.conf\"", shell=True)
    run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"])
