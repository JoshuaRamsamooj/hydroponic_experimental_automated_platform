import spidev
import time 

class mcp3008():

	def __init__(self):
		self.spi = spidev.SpiDev()
		self.spi.open(0,1)
		

	def readadc(self, adcnum):
		if adcnum>7 or adcnum<0:
			return -1
		r = self.spi.xfer2([1,8+adcnum<<4,0])
		data = ((r[1]&3)<<8)+r[2]
		v = 3.3*(float(data)/float(1023))
		return v

if __name__ == '__main__':
	m = mcp3008()
	print m.readadc(0)