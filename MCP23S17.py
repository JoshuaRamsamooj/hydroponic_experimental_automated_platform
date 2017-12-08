import spidev
import time

class MCP23S17(object):
    READ = 1
    WRITE = 0
    # Bank 0 Addresses
    IODIRA = 0x00
    IODIRB = 0x01
    
    IODIR_BIT_READ = 1
    IODIR_BIT_WRITE = 0
    
    GPIOA = 0x12
    GPIOB = 0x13
    
    IOCON_INIT = 0x28 # 0010 1000
    MCP23S17_IOCON = 0x0A

    max_speed_hz = None
    
    portA_value = None
    portB_value = None

    
    def __init__(self, bus, device, addr):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
            
        self.max_speed_hz = 10000000
        self.addr = addr

        addr1 = 0x40 | self.addr << 1 | self.WRITE
        addr2 = self.MCP23S17_IOCON

        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.xfer2 (list([addr1, addr2, self.IOCON_INIT]))
    
        self.portA_value = self.getPortA()
        self.portB_value = self.getPortB()
            
    def clearPortA(self):

        addr1 = 0x40 | self.addr << 1 | self.WRITE
        addr2 = self.GPIOA
        self.portA_value = 0
        
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.xfer2 (list([addr1, addr2, self.portA_value]))

    def clearPortB(self):

        addr1 = 0x40 | self.addr << 1 | self.WRITE
        addr2 = self.GPIOB
        self.portB_value = 0
        
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.xfer2 (list([addr1, addr2, self.portB_value]))

    def setPortA(self, port, value):

        addr1 = 0x40 | self.addr << 1 | self.WRITE
        addr2 = self.GPIOA

        if value:
            self.portA_value |= (1 << port)
        else:
            self.portA_value &= ~(1 << port)
        
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.xfer2 (list([addr1, addr2, self.portA_value]))

    def setPort(self, port, value):
        if port<=7:
            self.setPortA(port, value)

        else:
            self.setPortB(port-8, value)


    def setPortA_dir(self, value):
        addr1 = 0x40 | self.addr << 1 | self.WRITE
        addr2 = self.IODIRA
        cmdValue = value;
        
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.xfer2 (list([addr1, addr2, cmdValue]))
        
    def setPortB_dir(self, value):
        addr1 = 0x40 | self.addr << 1 | self.WRITE
        addr2 = self.IODIRB
        cmdValue = value;
        
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.xfer2 (list([addr1, addr2, cmdValue]))


    def setPortB(self, port, value):
        addr1 = 0x40 | self.addr << 1 | self.WRITE
        addr2 = self.GPIOB
        if value:
            self.portB_value |= (1 << port) 
        else:
            self.portB_value &= ~(1 << port)
        
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.xfer2 (list([addr1, addr2, self.portB_value]))

    def getPortB(self):
        addr1 = 0x40 | self.addr << 1 | self.READ
        addr2 = self.GPIOB

        self.spi.max_speed_hz = self.max_speed_hz
        r = self.spi.xfer2 (list([addr1, addr2, 0]))
        return r[2]

    def getPortA(self):
        addr1 = 0x40 | self.addr << 1 | self.READ
        addr2 = self.GPIOA

        self.spi.max_speed_hz = self.max_speed_hz
        r = self.spi.xfer2 (list([addr1, addr2, 0]))
        return r[2]


    def getPort(self, port):
        if port <= 7:
            portA = self.getPortA()
            return int(format(portA, '08b')[::-1][port])
            # ^ get 8bit binary as string,
            # reverses sting then returns the correct bit

        else:
            portB = self.getPortB()
            return int(format(portB, '08b')[::-1][port-8])


