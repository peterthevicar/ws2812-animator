import time
import sys
try:
    from rpi_ws281x import Color
except:
    import os; sys.path.append(os.path.dirname(os.path.realpath(__file__))+'/rpi-ws281x-simulator')
    from rpi_ws281x_simulator import Color
from colours import *
# How it works overview:
# The gradient description is used to 
# calculate the colours for each of the LEDs in a single segment. If
# the number of colours in the gradient description is smaller than the 
# size of a segment then the relevant interpolation function is used
# to fill in the intermediate colours.


# Blend values
SMOOTH=1; STEP=2; DASH=3; DOT=4

def _hue(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)
def _colour_to_tuple(colour):
    return (colour >> 16, (colour >> 8) & 0xFF, colour & 0xFF)
def _interp(colour1, colour2, frac):
    ct1 = _colour_to_tuple(colour1)
    ct2 = _colour_to_tuple(colour2)
    interp_col=[0]*3
    for i in range(3):
        interp_col[i] = int((1-frac)*ct1[i] + frac*ct2[i])
    return Color(interp_col[0], interp_col[1], interp_col[2])

class GradientDesc:
    """
    Specify and generate a gradient for use in pattern_display
    """
    def __init__(self, colours=[RGB_Black], repeats=1, blend=STEP, bar_on=0, bar_off=5):
        """
        Store the values defining the gradient. The renderer spaces
        the colours defined in the list 'colours' evenly along the gradient
        'repeats' times, using the 'blend' algorithm to interpolate 
        intermediate colours if necessary
        """
        self.colours = colours
        self.repeats = repeats
        self.blend = blend
        self.bar_on = bar_on
        self.bar_off = bar_off

    def render(self, size, out_data):
        """
        Compute 'size' (number) of individual colours for the current 
        gradient and put the computed colours into the supplied list
        The way colour points are treated is different between STEP and
        SMOOTH. E.g. two colour points, white and black. For a STEP you
        expect white to 50%, then black to 100%. For a SMOOTH you expect 
        a blend from white at 0 to black at 100%. This can be achieved 
        by pretending we have one fewer colour point when using SMOOTH
        For repeats: split the size into equal parts. Fill the first
        part then copy to the others. If the size isn't divisible exactly
        then round up for the first part and copy to n*size/repeats which
        will periodically overwrite the last bit
        """
        # calculate the max size of each of the repeats in the gradient
        part_sz = (size+self.repeats-1)//self.repeats
        print("DEBUG: gradient part_sz=",part_sz)
        # fill in the first part
        if self.blend != SMOOTH: # simple case
            ncols = len(self.colours)
            for i in range(part_sz):
              out_data[i] = self.colours[ncols*i//part_sz]
        else:
            ncols = len(self.colours) - 1 # last colour is reserved for final data point
            out_data[part_sz-1] = self.colours[ncols] # put the last colour in
            smooth_sz = part_sz - 1 # we're working with this part now
            i_per_c = smooth_sz / ncols # how many entries in the gradient for each defined colour
            cur_c = -1
            for i in range(smooth_sz):
                this_c = int(ncols * i // smooth_sz)
                if this_c != cur_c:
                    cur_c = this_c
                    cur_ci = i
                    colour1 = self.colours[this_c]
                    colour2 = self.colours[this_c + 1]
                out_data[i] = _interp(colour1, colour2, (i-cur_ci) / i_per_c)
                # ~ print(i,ncols,this_c,'DEBUG: colour1 {0:#08x}, colour2 {1:#08x}, ipercol:{2:1.2f} ithisc:{3:d} res:{4:#08x} prop:{5:1.2f}'.format(colour1,colour2,i_per_c,cur_ci,out_data[i],float(i-cur_ci) / i_per_c))
        # ~ print('DEBUG: part_sz=', part_sz, ' out_data=', out_data)
        # Copy to other parts. Start at the top to avoid overwriting the master copy
        for part in range(self.repeats-1,0,-1): 
            i = size * part//self.repeats
            out_data[i:i+part_sz]=out_data[0:part_sz]
        # put in the black bars
        if self.bar_on > 0:
            d_sz = max(1, size // 75)
            on_sz = self.bar_on * d_sz
            off_sz = self.bar_off * d_sz
            bar = [RGB_Black] * on_sz
            i = 0
            while i + on_sz < size:
                out_data[i:i+on_sz] = bar
                i += on_sz+off_sz
            while i < size:
                out_data[i:i+1]=[RGB_Black]
                i += 1
            

def gradient_preset(preset, blend=STEP, bar_on=0, bar_off=2):
    """Some presets for quick setup of gradient descriptor"""
    if preset == 1:
        # Christmas
        gra_colours = (RGB_Red, RGB_Green)
        gra_repeats = 8
    elif preset == 2: #Gold
        gra_colours = (RGB_Yellow, RGB_W_bal)
        gra_repeats = 8
    elif preset == 3: #Flag
        gra_colours = (RGB_W_bal, RGB_Blue, RGB_Black, RGB_Red)
        gra_repeats = 4
    elif preset == 4: #Piano
        gra_colours = (RGB_Black, RGB_W_bal,
        RGB_Black, RGB_Black, RGB_Black, RGB_W_bal)
        gra_repeats = 5
    elif preset == 5: #Rainbow
        gra_colours = (RGB_Red, RGB_Yellow, RGB_Green, RGB_Cyan, RGB_Blue, RGB_Magenta, RGB_Red)
        #gra_colours = (RGB_Red, RGB_Green, RGB_Blue, RGB_Red)
        gra_repeats = 1
    elif preset == 6: #Dash
        gra_colours = (RGB_Red, RGB_Black, RGB_Black, RGB_Black, 
            RGB_Black, RGB_Black, RGB_Black, RGB_Black, 
            RGB_Black, RGB_Black, RGB_Black, RGB_Black, 
            RGB_Black, RGB_Black, RGB_Black, RGB_Black)
        gra_repeats = 1
    elif preset == 7: #Saints
        gra_colours = (RGB_W_bal, RGB_Red, RGB_W_bal, RGB_Red, RGB_Black)
        gra_repeats = 3
    elif preset == 8: #LIS
        gra_colours = (RGB_W_bal, RGB_Blue)
        gra_repeats = 4
        
    return GradientDesc(gra_colours, gra_repeats, blend, bar_on, bar_off)


# ~ g_data=[0]*64
# ~ g = gradients_preset(5, SMOOTH)
# ~ g.render(len(g_data),g_data)
# ~ print(g_data)
