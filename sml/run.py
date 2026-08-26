import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

GPIO.setup(22, GPIO.IN)
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
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
n = True
pressed = False

up_count=0
down_count=0

def buttonUpPressed(channel):
    global up_count
    if up_count%2==1:
        time.sleep(0.15)
        print("UP pressed "+str(channel))
        Up1()
    else:
        print("UP released "+str(channel))
        Stop1()
    up_count+=1

def buttonDownPressed(channel):
    global down_count
    if down_count%2==1:
        time.sleep(0.15)
        print("DOWN pressed "+str(channel))
        Down1()
    else:
        print("DOWN released "+str(channel))
        Stop1()
    down_count+=1

#GPIO.add_event_detect(25, GPIO.RISING, callback=buttonUpPressed, bouncetime=75)
#GPIO.add_event_detect(27, GPIO.RISING, callback=buttonDownPressed, bouncetime=75)

while n:
    #print(str(GPIO.input(25)))
    if GPIO.input(25) == GPIO.HIGH & up_count == 1:
        up_count=0
        print("UP pressed!")
        Up1()
    elif GPIO.input(25) == GPIO.HIGH & up_count == 0:
        up_count = 1
        print("UP released...")
        Stop1()
    if GPIO.input(27) == GPIO.HIGH & down_count == 1:
        down_count = 0
        print("Down pressed!")
        Down1()
    elif GPIO.input(27) == GPIO.HIGH & down_count == 0:
        down_count = 1
        print("Down released...")
        Stop1()
    time.sleep(0.1)

message=input("Press Enter to Quit\n\n")
GPIO.cleanup()