import sys
import time
import RPi.GPIO as GPIO 
import asyncio
import copy

WAIT = 0.0065
gear_ratio = 126/17
sidereal_day = 86164 #seconds
GPIO.setmode(GPIO.BCM)

motor_pins = {"z": [18, 13, 12, 19], "x": [27, 17, 22, 5], "y": [20, 16, 21, 7]}

def _turn_off(motor):
    pins = motor_pins[motor]
    
    for pin in pins:
        GPIO.output(pin, True)


def _set_pins(motor):
    pins = motor_pins[motor]
    
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)

def lock_motor(motor):
    print("Locking motor", motor)
    _set_pins(motor)
    pins = motor_pins[motor]
    GPIO.output(pins[0], True)
    GPIO.output(pins[1], True)
    GPIO.output(pins[2], False)
    GPIO.output(pins[3], False)
    

def vibrate(motor, duration):
    steps_to_vibrate = int((duration/WAIT)/2)
    print("steps to vibrate:", steps_to_vibrate)
    for i in range(steps_to_vibrate):
        move(motor, 1, clockwise=True)
        move(motor, 1, clockwise=False)
        print(f"steps: {i}/{steps_to_vibrate}", end="\r") 
    _turn_off(motor)


async def move_microstep(motor, steps, sleep=False, clockwise=True):
    _set_pins(motor)

    pins = copy.deepcopy(motor_pins[motor])
    if not clockwise:
        pins.reverse()

    frequency = 1000
    max_pwm_value = 100
    wait_time = 0.001
    resolution = 50
    wait_between_steps = (sidereal_day/(200*4*gear_ratio)) - wait_time 

    pin_pwm_1 = GPIO.PWM(pins[0],frequency)		#create PWM instance with frequency
    pin_pwm_2 = GPIO.PWM(pins[1],frequency)		#create PWM instance with frequency
    pin_pwm_3 = GPIO.PWM(pins[2],frequency)		#create PWM instance with frequency
    pin_pwm_4 = GPIO.PWM(pins[3],frequency)		#create PWM instance with frequency
    pin_pwm_1.start(0)				#start PWM of required Duty Cycle 
    pin_pwm_2.start(0)				#start PWM of required Duty Cycle 
    pin_pwm_3.start(0)				#start PWM of required Duty Cycle 
    pin_pwm_4.start(0)				#start PWM of required Duty Cycle 

    first_time=True
    while True:
        for duty in range(0, max_pwm_value+1, resolution):
            # print("duty:", duty)
            pin_pwm_1.ChangeDutyCycle(duty)
            time.sleep(wait_time)
            if sleep:
                await asyncio.sleep(wait_between_steps)

        if not first_time:
            for duty in range(0, max_pwm_value+1, resolution):
                pin_pwm_4.ChangeDutyCycle(100-duty)
                time.sleep(wait_time)
                if sleep:
                    await asyncio.sleep(wait_between_steps)


        steps -= 1
        if steps < 0:
            return

        for duty in range(0, max_pwm_value+1, resolution):
            pin_pwm_2.ChangeDutyCycle(duty)
            time.sleep(wait_time)
            if sleep:
                await asyncio.sleep(wait_between_steps)


        for duty in range(0, max_pwm_value+1, resolution):
            pin_pwm_1.ChangeDutyCycle(100-duty)
            time.sleep(wait_time)
            if sleep:
                await asyncio.sleep(wait_between_steps)

        
        steps -= 1
        if steps < 0:
            return
        
        for duty in range(0, max_pwm_value+1, resolution):
            pin_pwm_3.ChangeDutyCycle(duty)
            time.sleep(wait_time)
            if sleep:
                await asyncio.sleep(wait_between_steps)


        for duty in range(0, max_pwm_value+1, resolution):
            pin_pwm_2.ChangeDutyCycle(100 - duty)
            time.sleep(wait_time)
            if sleep:
                await asyncio.sleep(wait_between_steps)


        steps -= 1
        if steps < 0:
            return
        
        for duty in range(0, max_pwm_value+1, resolution):
            pin_pwm_4.ChangeDutyCycle(duty)
            time.sleep(wait_time)
            if sleep:
                await asyncio.sleep(wait_between_steps)


        for duty in range(0, max_pwm_value+1, resolution):
            pin_pwm_3.ChangeDutyCycle(100-duty)
            time.sleep(wait_time)
            if sleep:
                await asyncio.sleep(wait_between_steps)

        first_time=False

        steps -= 1
        if steps < 0:
            return

def move(motor, steps, clockwise=True):
    _set_pins(motor)
    print(f"moving {motor} for", steps, "steps with clockwise=", clockwise, end="\r")
    
    step_sequence = list(range(4))

    pins = copy.deepcopy(motor_pins[motor])

    if not clockwise:
        pins.reverse()

    step_sequence[0] = [pins[0], pins[1]]
    step_sequence[1] = [pins[1], pins[2]]
    step_sequence[2] = [pins[2], pins[3]]
    step_sequence[3] = [pins[0], pins[3]]

    while True:
        for pin_list in step_sequence:
            for pin in pins:
                if pin not in pin_list:
                    GPIO.output(pin, True)
                else:
                    GPIO.output(pin, False)
            steps -= 1
            if steps < 0:
                return
            print("steps remaining in move:", steps, end="\r")
            time.sleep(WAIT)


    

