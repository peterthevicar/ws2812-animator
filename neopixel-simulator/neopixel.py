# This is a drop-in replacement for the real neopixel library to give a quick
# simulation of an LED strip on a computer screen
import numpy
import cv2
import time
import sys

def _adjust_primary(primary, brightness):
	return (primary*brightness+128)/255
	
def _adjust_colour(colour, brightness):
	return (_adjust_primary(colour & 0xFF, brightness),
	_adjust_primary((colour>>8) & 0xFF, brightness),
	_adjust_primary(colour>>16, brightness))

def Color(r, g, b, w=0):
	return ((r & 0xFF)<<16) | ((g & 0xFF)<<8) | (b & 0xFF)

IMAGE_W = 1000 # how wide you want the image of the LED strip (pixels)
LED_R = 3 # radius of an LED

class Adafruit_NeoPixel:
	def __init__(self, led_count, led_pin, led_freq_hz, led_dma, led_invert, led_brightness, led_channel):
		self.N_LEDS = led_count
		self._led_data = [0 for i in range(led_count)]
		self.brightness = led_brightness
		self.LED_W = float(IMAGE_W) / (led_count+1)
		# Create a black image in which to draw the LEDs
		self.IMAGE = numpy.zeros((LED_R*4, IMAGE_W, 3), numpy.uint8)
		cv2.namedWindow('neopixel') # Create a named window
		cv2.moveWindow('neopixel', 10,300) # Move it to a good place on the screen
		
	def begin(self):
		self.show()

	def setPixelColor(self, ix, colour):
		self._led_data[ix] = colour

	def numPixels(self):
		return self.N_LEDS

	def show(self):
		#print(self._led_data)
		if len(self._led_data) != self.N_LEDS:
			print('ERROR length of leds has changed to', len(self._led_data))
		for ix in range(self.N_LEDS):
			adjusted_colour = _adjust_colour(self._led_data[ix], self.brightness)
			cv2.circle(self.IMAGE, (int(self.LED_W*(ix+1) + 0.5), LED_R*2), LED_R, adjusted_colour, -1)
		cv2.imshow('neopixel', self.IMAGE)
		key = cv2.waitKeyEx(1)
		if key != -1: # seem to need about 40ms before anything appears on the screen
			print('*** Interrupted by keyboard *** character code=', key)
			sys.exit(99)
			
	def setPixelColorRGB(self, ix, r, g, b, w = 0):
		self.setPixelColor(ix, Color(r, g, b, w))

	def setBrightness(self, brightness):
		self.brightness = brightness

	def getBrightness(self):
		return self.brightness

	def getPixels(self):
		return self._led_data

	def numPixels(self):
		return self.N_LEDS

	def getPixelColor(self, n):
		return self._led_data[n]

	def finish(self):
		cv2.destroyAllWindows()

# ~ test = Adafruit_NeoPixel(100, 1, 1, 1, 1, 255, 1)
# ~ test_data = test.getPixels()
# ~ test_data[:]=[Color(255,255,0)]*100
# ~ f=1
# ~ while True:
	# ~ print(f)
	# ~ f+=1
	# ~ test.show()
	# ~ time.sleep(1)
# ~ print(_adjust_colour(0xff00f0,254))
