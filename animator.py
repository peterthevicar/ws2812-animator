from time import time, sleep
from time import time, sleep
# comment out the next line if using the real neopixel library
import sys, os
from numpy.random import randint
try:
    from rpi_ws281x import *
except:
    sys.path.append(os.path.dirname(os.path.realpath(__file__))+'/rpi-ws281x-simulator')
    from rpi_ws281x_simulator import *
from gradients import GradientDesc, gradient_preset, SMOOTH, STEP
from colours import *

# How it works overview:
# There are LED_COUNT LEDs in the strip.
# The pattern on these LEDs is made up of 1, 2, 4 or 8 repeated segments
# Each segment is based on a gradient defined by a gradient descriptor
# which has an arbitrary number of colours, a repeat count and an
# interpolation function. The interpolation functions available are:
# blend, bar, dash and dot.
# To display a patter on the LEDs, the gradient description is used to 
# calculate the colours for each of the LEDs in a single segment. If
# the number of colours in the gradient description is smaller than the 
# size of a segment then the relevant interpolatioin function is used
# to fill in the intermediate colours.
# The gradient is then copied to the pattern buffer (once per segment)
# adjusting the start point of the copy to give the motion effect.
# Then any overlay effects (sparkle, fade, spot) are applied.
# Once the pattern is complete it is sent to the LEDs

# LED strip configuration passed to WS2812 library:
LED_PIN = 18            # GPIO pin connected to the pixels (18 uses PWM1).
LED_FREQ_HZ = 800000    # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10            # DMA channel to use for generating signal (try 10)
LED_INVERT = False      # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0         # set to '1' for GPIOs 13, 19, 41, 45 or 53

#----------------------- Some constants for settings readability
# Motion values
STOP = 0; RIGHT=1; LEFT=2; L2R1=3
# Looping values
REPEAT=1; REVERSE=2
#----------------------- neopixel globals
_pat_strip = None # This is where the WS2812 library stores its stuff
_max_brightness = None
_led_count = None

#----------------------- Fade and sparkle stuff
_fade_blend = None              # square wave or sawtooth
_fade_min = 0                   # dimmest value
_fade_max = 100                 # brightest value
_fade_steps_per_repeat = None           # how long the fade cycle is
_fade_s_per_repeat = None           # how long the fade cycle is
_fade_steps_per_half = None         # half a cycle
_fade_s_per_step = None             # how long each frame in the fade is
_fade_t_start = 0               # when the cycle began

# Sparkle
_spark_count = 0                # Number of sparks to add in per step
_sparkles = None                # vector of random indexes into the led data
_spark_t_start = 0              # when this pattern of sparles started
_spark_duration = None          # how long each pattern of sparkles lasts (secs)

def _fade_scale(f_min, f_max):
    global _fade_min, _fade_max, _fade_steps_per_half, _fade_steps_per_repeat, _fade_s_per_step
    _fade_min = int(_max_brightness*f_min/100)
    _fade_max = int(_max_brightness*f_max/100)
    _fade_steps_per_half = max(0, _fade_max - _fade_min)
    _fade_steps_per_repeat = _fade_steps_per_half * 2
    if _fade_steps_per_repeat > 0:
        _fade_s_per_step = _fade_s_per_repeat / _fade_steps_per_repeat
    else:
        _fade_s_per_step = 1
       # ~ print('DEBUG:animator:65 min=', _fade_min, ' max=', _fade_max, ' steps=',_fade_steps_per_repeat)

def _render_fade_spark(t_now):
    # First the sparkles - a random set of places to set white for _spark_duration
    global _sparkles, _spark_t_start
    if _spark_count > 0:
        if t_now - _spark_t_start > _spark_duration: # time to get a new set of sparkles
            _sparkles = randint(0, _leds_in_use, _spark_count)
            _spark_t_start = t_now
        data = _pat_strip.getPixels()
        for i in _sparkles:
            data[i]=RGB_White
        t_next = _spark_t_start + _spark_duration
    else:
        t_next = t_now + 1000
        
    if _fade_steps_per_repeat == 0: # No fading so return
        return t_next

    global _fade_t_start
    if _fade_t_start == 0: _fade_t_start = t_now
    
    step = (t_now -_fade_t_start) // _fade_s_per_step
    if step >= _fade_steps_per_repeat:
        step = 0
        _fade_t_start = t_now
        
    if _fade_blend == STEP:
        new_b = _fade_min if step < _fade_steps_per_half else _fade_max
    else:
        if step < _fade_steps_per_half: # ramping up
            new_b = _fade_min + step
        else: # ramping down
            new_b = _fade_max - (step - _fade_steps_per_half)
            
    # Set the new value which mustn't be above the currently set max brightness
    new_b = int(min(new_b, _max_brightness))
    if new_b != _pat_strip.getBrightness():
        _pat_strip.setBrightness(new_b)
    
    return _fade_t_start + (step+1) * _fade_s_per_step
        
        

#----------------------- Moving spot stuff
_spot_size = 0                  # Size of moving spot, 0 = off
_spot_colour = None             # Colour of the moving spot
_spot_t_start = None            # When current spot animation started
_spot_s_per_step = None         # Sets the speed of the spot animation
_spot_steps_per_repeat = None   # Number of steps in spot animation
_spot_reverse = None            # RepeatLooping type - repeat or reverse
_spot_motion_now = None         # Direction of spot animation for this loop

def _render_spot(t_now):
    # Find out which step we're on in the pattern, need to calculate this
    # as timing is important and we may need to skip steps to keep up
    if _spot_size == 0:
        return t_now + 1000

    global _spot_t_start
    if _spot_t_start == 0: _spot_t_start = t_now
    
    global _spot_motion_now
    step = int((t_now - _spot_t_start) // _spot_s_per_step)
    if step >= _spot_steps_per_repeat: # Completed run, start again
        step = 0
        _spot_t_start = t_now;
        if _spot_reverse == REVERSE:
            _spot_motion_now = LEFT if _spot_motion_now == RIGHT else RIGHT

    # Work out the direction we're going
    if _spot_motion_now == RIGHT: ix = step # Count up
    else: ix = _pat_seg_size -_spot_size - step # Count down
    # ~ print('DEBUG:animator: spot step=', step, '/', _spot_steps_per_repeat,' spot ix=', ix)

    # Paint the spot in its current position
    # ~ print('DEBUG:animator: ix=', ix, ' _spot_size=', _spot_size)
    _pat_strip.getPixels()[ix:ix+_spot_size]=[_spot_colour]*_spot_size
            
    return _spot_t_start + _spot_s_per_step*(step+1); # Theoretical start time for next step (may be past)

#----------------------- Main pattern
# Pattern stuff
_pat_motion_now = RIGHT             # Current direction of pattern motion
_pat_reverse = REPEAT               # When pattern gets to end, does it repeat or reverse
_pat_sequential = None              # Do you fill the segments from the whole gradient (True) or have the whole segment filled with the same colour (False)
# Segment stuff
_pat_segments = 0                   # How many copies of the gradient to be fitted into the pattern
_pat_seg_size = 0
pat_seg_reverse = REPEAT            # Each segment is repeat or reverse of previous one
# Where are we in the animation
_pat_t_start = 0
_pat_s_per_step = 0
# Gradient object and data
_gra_desc = None
_gra_data = None # maximum size a segment can be
_leds_in_use = None # how many are actually being used

# Definition for the L2R1 motion - how far right and then left to go.
# These vary according to the segment size
_l2r1_l = 0
_l2r1_r = 0
_l2r1_t = 0
_l2r1_d = 0
def _set_l2r1_globals():
    global _l2r1_l, _l2r1_r, _l2r1_t, _l2r1_d
    _l2r1_l = max(2, _pat_seg_size//5)
    _l2r1_r = max(1, _l2r1_l//3)
    _l2r1_t = _l2r1_l + _l2r1_r
    _l2r1_d = _l2r1_l - _l2r1_r
    # ~ print('DEBUG:animator: r=',_l2r1_r,' l=',_l2r1_l,' ss//t*t=',_pat_seg_size//_l2r1_t*_l2r1_t)

def _render_segment(t_now):
    # Find out which step we're on in the pattern, need to calculate this as timing is 
    # important and we may need to skip steps to keep up
    
    # _pat_t_start is set to 0 by anim_define_pattern to indicate 'start again'
    global _pat_t_start
    if _pat_t_start == 0:
        _pat_t_start = t_now
    
    global _pat_s_per_step, _pat_steps_per_repeat
    global _pat_motion_0, _pat_motion_now, _pat_reverse
    # ~ print("DEBUG:animator: _pat_motion_now=",_pat_motion_now)
    if _pat_motion_now == STOP:
        step = 0
    else:
        step = int(((t_now - _pat_t_start) / _pat_s_per_step) + 0.5)
        if step >= _pat_steps_per_repeat: # completed pattern, start again
            step = 0;
            if _pat_motion_now != L2R1: 
                if _pat_reverse == REVERSE: 
                    _pat_motion_now = RIGHT if _pat_motion_now == LEFT else LEFT 
            _pat_t_start = t_now
    # Calculate start point for copying entries from the pattern palette (pat_ix)
    # Use the step number and the direction of motion
    # Work out the direction we're going
    if _pat_motion_now == LEFT or _pat_motion_now == STOP:
        pat_ix = step # Count up
    elif _pat_motion_now == RIGHT:
        pat_ix = _pat_seg_size-1 - step # Count down
    elif _pat_motion_now == L2R1:
        # This is the complicated one: turns out this does the trick! T=total(L,R), D=difference(L,R)
        rem = step % _l2r1_t
        pat_ix = (step // _l2r1_t) * _l2r1_d + (rem if rem <= _l2r1_l else _l2r1_l - (rem - _l2r1_l))
        pat_ix = pat_ix % _pat_seg_size # cope with wrap around

    # ~ print('DEBUG:animator: step=',step, 'LEFT' if _pat_motion_now==LEFT else 'RIGHT' if _pat_motion_now==RIGHT else 'L2R1', "pat_seg=", _pat_seg_size, " pat_ix=", pat_ix)
    if _pat_sequential: # copy the gradient into the segment, offset by the pat_ix
        _pat_strip.getPixels()[0:_pat_seg_size]=_gra_data[pat_ix:_pat_seg_size]+_gra_data[:pat_ix]
    else: # non-sequential means the whole segment is the same colour
        _pat_strip.getPixels()[0:_pat_seg_size]=[_gra_data[pat_ix]]*_pat_seg_size
    
    if _pat_motion_now == STOP:
        return t_now + 10 # no need but it seems nice to refresh every now and again!
    else:
        return _pat_t_start + _pat_s_per_step*(step+1); # Theoretical start time for next step (may be past)
    
def _render_frame():
    """
    Call all the renderers to build up the current state and then show on the LED strip
    Return the time of the next frame
    """
    
    t_now = time() # Use the same time throughout the calculations

    # Handle blanking
    if (_max_brightness == 0):
        _pat_strip.show()
        return t_now + 1

    # copy the gradient into first segment at the right place (phase shift)
    pat_t_next = _render_segment(t_now)
    
    # draw the moving spot on top
    spot_t_next = _render_spot(t_now)
    
    # for multi-segment patterns, copy into the other segments
    for i in range(1, _pat_segments):
        s_off = i*_pat_seg_size
        strip_data = _pat_strip.getPixels()
        if i % 2 == 0 or _pat_seg_reverse == REPEAT: # this segment is in forwards
            strip_data[s_off:s_off+_pat_seg_size]=strip_data[0:_pat_seg_size]
        else: # have to put this segment in backwards
            strip_data[s_off:s_off+_pat_seg_size]=strip_data[0:_pat_seg_size][::-1]
        
    # apply any sparkles and fade pattern
    fade_t_next = _render_fade_spark(t_now)

    # Send the data to the LED strip
    _pat_strip.show()
    #print("{0:3.2f} {1:3.2f} {2:3.2f} {3:3.2f} ".format(t_now, time(), pat_t_next, spot_t_next))
    # Work out the soonest step to be done
    return min(pat_t_next, fade_t_next, spot_t_next)
#
# -------------------------- INTERFACE FUNCTIONS ----------------------
#
def anim_init(led_count):
    """
    Initial set up of the system for animations
    Clears everything out and switches things off
    """
    global _led_count, _gra_data
    _led_count = led_count
    _gra_data = [0]*led_count # Maximum segment size
    
    global _max_brightness
    _max_brightness = 0

    global _pat_strip
    _pat_strip = PixelStrip(led_count, LED_PIN, LED_FREQ_HZ, 
    LED_DMA, LED_INVERT, _max_brightness, LED_CHANNEL)
    _pat_strip.begin()

    # Switch off sparkle, fade and spot
    global _spark_count, _fade_steps_per_repeat, _spot_size
    _spark_count = 0; _fade_steps_per_repeat = 0; _spot_size = 0
    
def anim_stop():
    """
    Called to turn everything off
    """
    if _pat_strip != None:
        #~ _pat_strip.getPixels()[:]=[RGB_Black]*_pat_Strip.numPixels()
        anim_set_max_brightness(0)
        _pat_strip.show()
    
def anim_define_pattern(g_desc, segments=1, seg_reverse=REPEAT, motion=RIGHT, repeat_s=10, reverse=REPEAT):
    """
    Set the globals for the main pattern generation. 
    Rebuild the gradient and restart the animation.
    g_desc is a gradient descriptor for the main gradient. This is repeated
    in each of the segments (number of segments).
    seg_reverse says whether the repeat of the gradient in each segement
    is in the same direction or reverses segment-by-segment.
    motion is LEFT, RIGHT, L2R1 or STOP and reverse says whether the
    gradient movement reverses or repeats when it gets to the end of its
    segment.
    """
    global _spot_size
    _spot_size = 0 # mustn't run spot for previous pattern in case segment size changes

    global _gra_desc
    _gra_desc = g_desc
                
    global _pat_segments, _pat_seg_size, _leds_in_use, _pat_sequential
    if segments <= 0: # asking all LEDS to change colour together
        _pat_sequential = False
        _pat_segments = 1
    else:
        _pat_sequential = True
        _pat_segments = min(segments, _led_count) # can't have segments smaller than one LED
    _pat_seg_size = _led_count // _pat_segments
    _set_l2r1_globals()
    _leds_in_use = _pat_seg_size * _pat_segments
    
    global _pat_seg_reverse
    _pat_seg_reverse = seg_reverse

    global _pat_motion_now, _pat_steps_per_repeat
    _pat_motion_now = motion
    # ~ print("DEBUG:animator: motion=",motion,"seg_sz=",_pat_seg_size)
    if motion == LEFT or motion == RIGHT:
        _pat_steps_per_repeat = _pat_seg_size
    elif motion == L2R1:
        # This is hard because _l2r1_d is not 1 so not every length can be exactly accommodated
        wholes = _pat_seg_size // _l2r1_d
        rem = _pat_seg_size % _l2r1_d
        _pat_steps_per_repeat = _l2r1_t * wholes + rem
        # ~ print('DEBUG:animator: seg_size',_pat_seg_size, 'steps_per_repeat',_pat_steps_per_repeat)
    else: # stop
        _pat_steps_per_repeat = 0;

    global _pat_s_per_step
    if motion != STOP: _pat_s_per_step = float(repeat_s) / _pat_steps_per_repeat
    # ~ print("DEBUG:animator: s_per_step=",_pat_s_per_step)

    global _pat_reverse
    _pat_reverse = reverse
            
    # regenerate the gradient
    global _gra_data
    _gra_desc.render(_pat_seg_size, _gra_data)
    
    # request restart of the animation
    global _pat_t_start
    _pat_t_start = 0
    # ~ print('DEBUG:animator: seg_size',_pat_seg_size,'tot',_pat_seg_size*_pat_segments)

def anim_define_spot(s_size, s_colour, s_motion=RIGHT, s_secs=5, s_reverse=REVERSE):
    """
    Define a spot moving on top of the background gradient
    s_size is the size of the spot in 32nds of the segement size.
    The spot is a single colour (s_colour) and can move left, right, 2l1r
    as defined by s_motion. s_secs is how long the spot takes to move 
    the length of the segment. When it gets to the end it comes back 
    (s_reverse=REVERSE) or starts again (s_reverse=REPEAT)
    """
    global _spot_size, _spot_steps_per_repeat
    if s_size <= 0:
        _spot_size = 0
    else:
        _spot_size = max(1, s_size*_pat_seg_size // 32)
        # ~ print('DEBUG:animator: spot_sz=', _spot_size) 
        _spot_steps_per_repeat = _pat_seg_size - _spot_size; # Prevent overflow
            
    global _spot_colour
    _spot_colour = s_colour
    
    global _spot_motion_now
    _spot_motion_now = s_motion

    global _spot_s_per_step
    _spot_s_per_step = float(s_secs) / _pat_seg_size

    global _spot_reverse
    _spot_reverse = s_reverse
    
    # request restart of the animation
    global _spot_t_start
    _spot_t_start = 0

def anim_define_sparkle(s_per_k, s_duration=0.1):
    """
    How many sparks (fully lit pixels) per thousand, and how long each should
    be lit before going out.
    """
    global _spark_count
    _spark_count = s_per_k * _leds_in_use // 1000
    
    global _spark_duration
    _spark_duration = s_duration

def anim_define_fade(f_secs, f_blend=SMOOTH, f_min=0, f_max=100):
    """
    Fade the whole LED strip in a cycle taking f_secs. The cycle can step
    between f_min and f_max in one go or smoothly linearly interpolated.
    f_min and f_max are in percent of the currently set max_brightness
    which is calculated in _fade_scale
    """
    global _fade_steps_per_repeat
    if f_secs <= 0: # switch off fading
        _fade_steps_per_repeat = 0
        return
        
    global _fade_blend
    _fade_blend = f_blend
    global _fade_s_per_repeat
    _fade_s_per_repeat = f_secs
    _fade_scale(f_min, f_max)

def anim_set_max_brightness(new_b):
    """
    Set the maximum brightness for the LEDs. As this tweaks the same
    property of the LED string that fade does, we need to scale the 
    values used by fade whenever this changes.
    """
    global _max_brightness
    if new_b != _max_brightness:
        old_b = _max_brightness; _max_brightness = new_b
        # Re-scale the fade min and max values if fading is going on
        if _fade_steps_per_repeat != 0:
            _fade_scale(_fade_min*100/old_b, _fade_max*100/old_b)
        _pat_strip.setBrightness(_max_brightness)

def anim_render(stop_time=0):
    """
    Keep transfering the animation to the LEDs until we reach stop_time.
    """
    while time() < stop_time:
        t_next = _render_frame()
        if stop_time != 0: t_next = min(t_next, stop_time)
        pause = t_next - time()
        if pause > 0: sleep(pause)
                
if __name__ == "__main__":
    anim_init(150, 200)
    anim_define_pattern(gradient_preset(6), 1, seg_reverse=REPEAT, motion=LEFT, repeat_s=5, reverse=REPEAT)
    anim_define_spot(s_size=3, s_colour=0x00FF00, s_motion=RIGHT, s_secs=5, s_reverse=REVERSE)
    anim_define_sparkle(s_per_k=10, s_duration=0.1)
    anim_define_fade(f_secs=5, f_blend=SMOOTH, f_min=50, f_max=100)
    anim_render(time()+30)
    
