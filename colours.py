try:
	from rpi_ws281x import Color
except:
	import os; import sys
	sys.path.append(os.path.dirname(os.path.realpath(__file__))+'/rpi-ws281x-simulator')
	from rpi_ws281x_simulator import Color
# Some pre-calculated primary colours for use around the place (Color is defined in neopixels)
RGB_Red=Color(255,0,0); RGB_Green=Color(0,255,0); RGB_Blue=Color(0,0,255)
RGB_Yellow=Color(255,255,0); RGB_Cyan=Color(0,255,255); RGB_Magenta=Color(255,0,255)
RGB_Black=Color(0,0,0); RGB_Grey=Color(85,85,85); RGB_White=Color(255,255,255)
RGB_W_bal=Color(240,240,240) # looks as bright as a pure colour
