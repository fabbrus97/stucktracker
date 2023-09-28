#reference: https://github.com/adafruit/Adafruit_CircuitPython_ICM20X
import board
import adafruit_icm20x

from math import atan2, sqrt, sin, asin, cos
import numpy as np

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
icm = adafruit_icm20x.ICM20948(i2c)

#Soft iron transformation matrix:
si = np.array([[ 4.2621072,  -0.08672055, -0.41655735],
 [-0.08672055,  4.32391982,  0.02483947],
 [-0.41655735,  0.02483947,  5.92281568]])
#Hard iron bias:
hi = np.array([[-23.41308837],
 [  8.67579027],
 [ 52.92178302]])


def get_position():
    # ax, ay, az = icm.acceleration
    mx, my, mz = icm.magnetic
    # gx, gy, gz = icm.gyro

    corrected_xyz = np.dot(si, np.array([mx - hi[0], my - hi[1], mz - hi[2]]))
    heading_rad = atan2(corrected_xyz[1], corrected_xyz[0])
    #heading_rad += 0.0663 #adjust for magnetic declination

    if (heading_rad < 0):
        heading_rad += 2*np.pi

    if (heading_rad > 2*np.pi):
        heading_rad -= 2*np.pi

    heading = np.rad2deg(heading_rad)
    print("Compass: heading to", heading, end="\r")
    return heading


if __name__ == "__main__":
    print(get_position())
