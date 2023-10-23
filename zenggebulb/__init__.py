import socket

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
        self.sock = socket.socket()
        try:
            self.sock.connect((self.host, self.port))
            return True
        except OSError:
            return False

    def close(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
    
    def send(self, msg, checksum=True):
        self.connect()
        try:
            if checksum:
                msg.append(self.checksum(msg))

            self.sock.sendall(bytes(msg))
            return True
        except OSError:
            return False

    def run(self, cmd, checksum=True):
        self.connect()
        try:
            if self.send(cmd) is False:
                raise OSError('F')
            data = self.sock.recv(32)
        except OSError:
            print('err')
        return data.hex()

    ### set bulb to hsl mode ###
    # r: 0 -> 180
    # g: 0 -> 100
    # b: 0 -> 100
    def set_hsl(self, h, s, l):
        step = 48
        cmd = [0xb0, 0xb1, 0xb2, 0xb3, 0x00, 0x01, 0x02, 0xec, 0x00, 0x0e, 0xe0, 0x01, 0x00, 0xa1, h, s, l, 0x00, 0x00, 0x00, 0x00, step, 0x00, 0x00]
        return self.run(cmd)

    ### set bulb to cct mode ###
    # temp: 0 -> 100, (warm -> cool)
    # brightness : 0 -> 100
    def set_cct(self, temp, brightness):
        step = 48
        cmd = [0x3b, 0xb1, 0x00, 0x00, 0x00, temp, brightness, 0x00, 0x00, step, 0x00, 0x00]
        return self.run(cmd)
    
