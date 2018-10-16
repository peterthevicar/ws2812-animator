# ws2812-animator
High level functions for building interesting animations on WS2812 LED strips

For testing without actual WS2812 strips, there is a simulator which displays a simulation of the
strip using opencv. The neopixel-simulator therefore requires cv2 (python3-opencv package i ubuntu, which is not in raspbian stretch)
To install cv2 on raspbian stretch:
  pip3 install opencv-python
  apt-get install libjasper-dev libqtgui4
  Other things I installed but not sure if needed: libgtk2.0-dev libgtk-3-dev libatlas-base-dev gfortran python3-dev
