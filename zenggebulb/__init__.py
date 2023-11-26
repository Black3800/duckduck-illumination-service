import socket
from select import select
from multiprocessing import Process

TRUE                 = 0xF0
FALSE                = 0x0F
ON                   = 0x23
OFF                  = 0x24

def run_with_limited_time(func, args, kwargs, time):
    """Runs a function with time limit

    :param func: The function to run
    :param args: The functions args, given as tuple
    :param kwargs: The functions keywords, given as dict
    :param time: The time limit in seconds
    :return: True if the function ended successfully. False if it was terminated.
    """
    p = Process(target=func, args=args, kwargs=kwargs)
    p.start()
    p.join(time)
    if p.is_alive():
        p.terminate()
        return False

    return True

class ZenggeBulb(object):
    def __init__(self, host):
        """Initialization"""
        self.host = host
        self.port = 5577
        self.timeout = 5

    ### calculate message checksum ###
    def checksum(self, data):
        sum = 0
        for byte in data:
            sum += byte
        return sum % 256

    def connect(self):
        sock = socket.socket()
        try:
            sock.connect((self.host, self.port))
            return sock
        except OSError:
            return False

    def close(self, sock):
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
    
    def send(self, sock, msg, checksum=True):
        try:
            if checksum:
                msg.append(self.checksum(msg))
            
            return run_with_limited_time(sock.sendall, (bytes(msg),), {}, 4)
        except OSError:
            return False

    def sendraw(self, sock, msg, checksum=True):
        try:
            if checksum:
                msg.append(self.checksum(msg))
            
            sock.sendall(bytes(msg))
            return True
        except OSError:
            return False

    def run(self, cmd, checksum=True):
        if type(self.host) != str:
            return False
        sock = self.connect()
        data = None
        try:
            if self.send(sock, cmd) is False:
                raise OSError('F')
            ready = select([sock], [], [], 6)
            if ready[0]:
                sock.settimeout(10)
                data = sock.recv(32)
            if data == None:
                return False
            else:
                return data.hex()
        except OSError:
            print('err')
            return False
        finally:
            self.close(sock)
        

    ### set bulb to hsl mode ###
    # r: 0 -> 180
    # g: 0 -> 100
    # b: 0 -> 100
    def set_hsl(self, h, s, l):
        return self.set_hsl_step(h, s, l, 48)

    def set_hsl_step(self, h, s, l, step):
        cmd = [0xb0, 0xb1, 0xb2, 0xb3, 0x00, 0x01, 0x02, 0xec, 0x00, 0x0e, 0xe0, 0x01, 0x00, 0xa1, h, s, l, 0x00, 0x00, 0x00, 0x00, step, 0x00, 0x00]
        return self.run(cmd)

    def set_hsl_norecv(self, h, s, l):
        sock = self.connect()
        cmd = [0xb0, 0xb1, 0xb2, 0xb3, 0x00, 0x01, 0x02, 0xec, 0x00, 0x0e, 0xe0, 0x01, 0x00, 0xa1, h, s, l, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        result = self.sendraw(sock, cmd)
        self.close(sock)
        return result

    ### set bulb to cct mode ###
    # temp: 0 -> 100, (warm -> cool)
    # brightness : 0 -> 100
    def set_cct(self, temp, brightness):
        return self.set_cct_step(temp, brightness, 48)

    def set_cct_step(self, temp, brightness, step):
        cmd = [0x3b, 0xb1, 0x00, 0x00, 0x00, temp, brightness, 0x00, 0x00, step, 0x00, 0x00]
        return self.run(cmd)

    def set_cct_norecv(self, temp, brightness):
        sock = self.connect()
        cmd = [0x3b, 0xb1, 0x00, 0x00, 0x00, temp, brightness, 0x00, 0x00, 0x00, 0x00, 0x00]
        result = self.sendraw(sock, cmd)
        self.close(sock)
        return result

    def set_power(self, on):
        cmd = [0xb0, 0xb1, 0xb2, 0xb3, 0x00, 0x00, 0x00, 0x11, 0x00, 0x03, 0x71, (ON if on else OFF), (0x94 if on else 0x95)]
        return self.run(cmd)
    
    def get_state(self):
        cmd = [0x81, 0x8a, 0x8b, 0x96]
        print(cmd)
        data = self.run(cmd, checksum=False)
        print(data)
        data = [int(data[i:i+2],16) for i in range(0, len(data), 2)]
        return State(data[1], data[2] == ON, data[3], data[5], Color(data[6], data[7], data[8], data[9], data[12] == TRUE), data[10])
    

class State:
    def __init__(self, deviceType, isOn, Mode, Slowness, Color, LedVersionNum):
        self.deviceType = int(deviceType)
        self.isOn = bool(isOn)
        self.Mode = int(Mode)
        self.Slowness = int(Slowness)
        self.Color = Color
        self.LedVersionNum = int(LedVersionNum)
    
    def toJSON(self):
        return {
            "deviceType": self.deviceType,
            "isOn": self.isOn,
            "mode": self.Mode,
            "slowness": self.Slowness,
            "color": {
                "h": self.Color.H,
                "s": self.Color.S,
                "l": self.Color.L,
                "w": self.Color.W,
                "ignoreW": self.Color.IgnoreW
            },
            "ledVersionNum": self.LedVersionNum
        }

class Color:
    def __init__(self, H, S, L, W, IgnoreW):
        self.H = int(H)
        self.S = int(S)
        self.L = int(L)
        self.W = int(W)
        self.IgnoreW = bool(IgnoreW)