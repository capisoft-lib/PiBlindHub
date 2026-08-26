import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

GPIO.setup(22, GPIO.IN)
GPIO.setup(27, GPIO.IN)
GPIO.setup(25, GPIO.IN)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(24, GPIO.OUT)
#GPIO.setup(25, GPIO.OUT)

def Up1():
    GPIO.output(23, GPIO.HIGH)
    GPIO.output(24, GPIO.LOW)

def Down1():
    GPIO.output(23, GPIO.LOW)
    GPIO.output(24, GPIO.HIGH)

def Stop1():
    GPIO.output(23, GPIO.LOW)
    GPIO.output(24, GPIO.LOW)

def rising_callback(channel):
    print(channel)

#GPIO.add_event_detect(22, GPIO.BOTH, callback=rising_callback, bouncetime=75)
n = False
pressed = False

Up1()
time.sleep(60)
Stop1()