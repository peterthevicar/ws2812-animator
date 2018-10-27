#
# Based on 2018 program 'example.py' by Dave Hocker
#
try:
	from pyudmx import pyudmx
except:
	sys.path.append(os.path.dirname(os.path.realpath(__file__))+'/pyudmx')
	from pyudmx import pyudmx

from time import sleep, time

_DMX_UNIVERSE_SIZE = 255
_DMX_CHANS_PER_UNIT = 7
_dmx = None
_dmx_buffer = [0 for v in range(0, _DMX_UNIVERSE_SIZE)]

def _dmx_show():
	_dmx.send_multi_value(1, _dmx_buffer)
	
def dmx_blank():
	_dmx_buffer[:] = [0 for v in range(0, _DMX_UNIVERSE_SIZE)]
	return _dmx_show()

def dmx_init():
	global _dmx
	print("Starting DMX controller")
	_dmx = pyudmx.uDMXDevice()
	_dmx.open()
	dmx_blank()

def dmx_put_unit(unit=0, colour=0x000000, brightness=255):
	b = colour & 0xFF
	g = (colour >> 8) & 0xFF
	r = (colour >> 16) & 0xFF
	chan_offs = _DMX_CHANS_PER_UNIT * unit
	# Order correctly for the particular channel use of the unit
	_dmx_buffer[chan_offs:chan_offs+_DMX_CHANS_PER_UNIT] = [brightness & 0xFF, r, g, b, 0, 0, 0]
	return _dmx_show()

def dmx_close():
	_dmx.close()

if __name__ == "__main__":
	dmx_init()
	print('Ramp blue')
	t_start = time()
	frames = 250
	for b in range (frames):
		dmx_put_unit(0, b, 255)
	print('FPS:', frames/(time()-t_start))
	print('Colour red')		
	dmx_put_unit(0,0xFF0000,255)
	# These particular units seem to need refreshing every half second or so
	for i in range(10):
		sleep(0.5)
		_dmx_show()
	print('Colour green')
	dmx_put_unit(1,0x00FF00,255)
	for i in range(10):
		sleep(0.5)
		_dmx_show()
	print('Blank')
	dmx_blank()
	sleep(2)
	#dmx_close()
