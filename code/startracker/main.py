import asyncio
import RPi.GPIO as GPIO 
from lib import gps, compass, motors, accel
from datetime import date
import time
import wmm2020
import numpy as np
import os
GPIO_BUTTON=25              # The GPIO pin the button is attached to
GPIO_LED=4                  # The GPIO pin the led is attached to
LONGPRESS_SHUTDOWN=10       # If button is held this length of time, shut down the system
LONGPRESS_START_STOP=3      # If button is held this length of time, start/stop the star tracker
""" 
    after the system gets in the right tilt position, we may want to move the camera, and this can make the system go in the wrong tilt position
    so we wait WAIT_BETWEEN_ADJUST_TILT seconds before adjusting again the system in the correct position
"""
WAIT_BETWEEN_ADJUST_TILT=15 
                            

is_running = False      # status of the star tracker (running/not running)
is_ready_1 = False      # wether the star tracker points to north and we have gps data
is_ready_2 = False      # wether the star tracker is ready to track (in the correct position)
gps_data = [None, None, None, None]         # gps position - lat, lon, alt, date
compass_data = None     # distance from north (degrees)

GPIO.setmode(GPIO.BCM) 
GPIO.setup(GPIO_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
GPIO.setup(GPIO_LED,GPIO.OUT) 

async def listen_accel():
    print("Listen accel started")
    gear_ratio1 = 64/17
    gear_ratio2 = 127/24
    
    global is_ready_1
    global is_ready_2
    global gps_data

    is_ok = False
    while True:
        if is_ready_1 and is_running:
            tilt_array = []
            for i in range(30):
                _tilt = accel.get_tilt() #tilt is negative
                print("got tilt of", _tilt, end="\r")
                tilt_array.append((_tilt*-1))
            
            _tilt = np.median(tilt_array)
            print("accel: tilt is", _tilt)
            if _tilt == 0:
                #we took no data because everything is 0
                continue
            distance = gps_data[0] - _tilt
            if distance < 1.5 and distance > -1.5:
                #now the user is going to mount the camera
                motors.lock_motor("y")
                #so the camera won't fall 
                if is_ok:
                    is_ready_2 = True
                    motors.lock_motor("x")
                    print("Motor locked for accel")
                    break
                is_ok = True
            else:
                is_ok = False
            
                rot2  = distance*gear_ratio2
                step1 = abs(int((rot2*gear_ratio1)/1.8))
                print("accel: we are at tilt", _tilt, "and need to go to", gps_data[0])
                print("accel:", step1, "steps needed to position correctly - distance is", distance)
                if distance > 0:
                    print("accel: I need to move clockwise")
                    motors.move("x", step1, clockwise=True)
                else:
                    print("accel: I need to move anticlockwise")
                    motors.move("x", step1, clockwise=False)
            await asyncio.sleep(WAIT_BETWEEN_ADJUST_TILT)
        await asyncio.sleep(1)    

async def tracking():
    while True:
        if is_ready_2 and is_running:
            print("tracking 10 seconds")
            #the led will flash for a few seconds, so the user has the time to press the shutter button on the camera before the tracking starts
            await asyncio.sleep(10)
            await motors.move_microstep("y", 1000, sleep=True) #1000 is a random number - is just a large number of steps
        else:
            await asyncio.sleep(1)

def listen_gps():
    print("Listen gps task started")
    # while True:
    _gps_data = gps.get_gps_data()
    print("Got gps data:", _gps_data)
    if _gps_data != None and _gps_data[0] != 0:
        global gps_data
        global compass_data
        global is_ready_1
        gps_data[0] = _gps_data[0]
        gps_data[1] = _gps_data[1]
        gps_data[2] = _gps_data[2]
        gps_data[3] = _gps_data[3]
        if compass_data != None:
            is_ready_1 = True
        else:
            print("gps ready, but not compass, can't set is_ready_1 to true")
        # break
        return True
    # else:
    #     await asyncio.sleep(1)
    return False
        

async def control_led():
    print("Control led started")
    #shut the led off
    GPIO.output(GPIO_LED,GPIO.LOW) 

    while True:
        print("is_read_1", is_ready_1)
        print("is_ready_2", is_ready_2)
        if is_ready_1 and not is_ready_2:
            #light the led
            GPIO.output(GPIO_LED,GPIO.HIGH) 
        elif is_ready_2:
            GPIO.output(GPIO_LED,GPIO.LOW) 
            print("LED: we are ready and tracking, countdown...")
            pos = 0
            for i in [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]: #fib sequence
                #this gives us about 9 seconds of blinking
                time2sleep = 1/i
                print("blink time2sleep:", time2sleep)
                pos += 1
                for j in range(pos):
                    #do pos blinks for time time
                    GPIO.output(GPIO_LED,GPIO.HIGH) 
                    print("BLINK")
                    time.sleep(time2sleep)
                    GPIO.output(GPIO_LED,GPIO.LOW) 
                    print("NOT BLINK")
                    time.sleep(time2sleep)
                    
            counter_seconds = 0
            while is_ready_2:
                print("now we have to blink fast every 30 seconds")
                print((30 - counter_seconds), "seconds to blink")
                if counter_seconds == 0:
                    print("Counter seconds:", counter_seconds)
                    #blink
                    for l in range(2):
                        GPIO.output(GPIO_LED,GPIO.HIGH) 
                        time.sleep(0.05)
                        GPIO.output(GPIO_LED,GPIO.LOW) 
                        time.sleep(0.05)

                counter_seconds += 1
                counter_seconds = counter_seconds%30
                await asyncio.sleep(1)
        await asyncio.sleep(1)

def listen_compass():
    print("listen compass started")
    # while True:
    compass_array = []
    compass_array_shifted = []
    for i in range(30):
        _compass = compass.get_position()
        if _compass > 180:
            compass_array_shifted.append(360 - _compass)
        else:
            compass_array_shifted.append(_compass)
        compass_array.append(_compass)
    
    _compass_shifted = np.median(compass_array_shifted)
    _compass = np.median(compass_array)

    print("read compass:", _compass, "and shifted:", _compass_shifted)
    
    # if gps_data == None or gps_data[0] == None or gps_data[2] == None or gps_data[3] == None:
    #     print("compass: gps data is still None, continue")
    #     # await asyncio.sleep(1)
    #     # continue
    #     return False
    
    current_date = gps_data[3]
    year = current_date.year
    elapsed = current_date.toordinal() - date(year, 1, 1).toordinal()
    yeardec = year + (elapsed/365)
    
    mag = wmm2020.wmm(gps_data[0], gps_data[1], gps_data[2]/1000, yeardec)        
    decl = mag.decl.data[0,0]
    print("Declination is", decl)
    _compass += decl
    _compass = _compass%360
#        global gps_data
    global compass_data
    global is_ready_1

    if _compass_shifted < 5:
    # if _compass_shifted > 175:
        #we are within 2 degrees from north, let's block the motor and signal to the user with 5 vibrations:
        for i in range(5):
            print("we found the north, vibrate three times for one second")
            motors.vibrate("z", 0.2)
            time.sleep(0.3)
        compass_data = _compass_shifted
        motors.lock_motor("z")
        print("\nMotor locked for compass")
        if gps_data[0] != None:
            is_ready_1 = True
        else:
            print("compass ready, but not gps_data, can't set is_ready_1 to true")
        # break
        return True


    if  _compass < 180: #we are, e.g., at 40° from north and must turn anticlockwise
        print("we should turn a bit anticlockwise, vibrate once for", _compass/90, "seconds")
        # let's signal it to the user with a vibrations:
        motors.vibrate("z", _compass/90) #vibration in seconds: 180 = 2 sec, 90 = 1 sec etc.
        # motors.vibrate("z", (180 - _compass)/90) #vibration in seconds: 180 = 2 sec, 90 = 1 sec etc.
        time.sleep(3) #time for the user to make the adjustement
    else: #we are, e.g. 330° = 30° from north and must turn clockwise
        print("we should turn a bit clockwise, vibrate twice for", _compass/180, "seconds each")
        # let's signal it to the user with two vibrations:
        motors.vibrate("z", (360 - _compass)/180) #it's like (_compass/90)/2
        # motors.vibrate("z", (_compass - 180)/180) #it's like (_compass/90)/2
        time.sleep(0.5)
        motors.vibrate("z", (360 - _compass)/180) #it's like (_compass/90)/2

        time.sleep(3) #time for the user to make the adjustement

    
    # await asyncio.sleep(1)
    return False

async def listen_button():
    while True:
        await asyncio.sleep(1)

        if GPIO.input(GPIO_BUTTON) == False: # Listen for the press 
            print("button: someone pressed")
            pressed_time=time.time()
            while GPIO.input(GPIO_BUTTON) == False: 
                time.sleep(0.1)

                elapsed_time=time.time()-pressed_time
                print("pressing time:", elapsed_time, end="\r")
                if GPIO.input(GPIO_BUTTON): #the pressing stopped
                    if elapsed_time > LONGPRESS_START_STOP and elapsed_time < LONGPRESS_SHUTDOWN:
                        global is_ready_1
                        global is_ready_2
                        global is_running
                        
                        if not is_ready_1:
                            print("Cannot start tracking, ready_1 is false")
                            break
                        if is_ready_1 and not is_running: #pressing the button before we have gps data and pointing to north does nothing
                            is_running = True
                            break
                        else:    
                            print("Stopping tracking")
                            is_running = False
                            is_ready_2 = False
                    elif elapsed_time > LONGPRESS_SHUTDOWN:
                        print("SHUTTING SYSTEM DOWN")
                        os.system("sudo shutdown now")
        else:
            print("button: no pressing detected")
                
async def listen_gps_compass():
    while not listen_gps():
        asyncio.sleep(1)
    while not listen_compass():
        asyncio.sleep(1)
    

async def main():
    task_button = asyncio.create_task(listen_button()) 
    task_gps_compass = asyncio.create_task(listen_gps_compass())
    task_tracking = asyncio.create_task(tracking())
    task_accel = asyncio.create_task(listen_accel())
    task_led = asyncio.create_task(control_led())
    await asyncio.gather(task_button, task_gps_compass, task_tracking, task_accel, task_led) 

if __name__ == "__main__":
    asyncio.run(main())
