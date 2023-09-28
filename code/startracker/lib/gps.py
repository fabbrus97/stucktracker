import serial
import pynmea2
import datetime
import time

gps_port = "/dev/serial0"

def _port_setup(port):
    ser = serial.Serial(port, baudrate=9600, timeout=2)
    return ser

def _parseGPSdata(ser):
        keywords = ["$GPRMC","$GPGGA"]
        gps_data = ser.readline()
        gps_data = gps_data.decode("utf-8")  # transform data into plain string
        try:
            nmeaobj = pynmea2.parse(gps_data)
            #print(gps_data)
            #print(['%s: %s' % (nmeaobj.fields[i][0], nmeaobj.data[i])
            #    for i in range(len(nmeaobj.fields))])
        except Exception as e:
            print(e)

        if len(gps_data) > 5:  # Check to see if the GPS gave any useful data
            if gps_data[0:6] in keywords:   # Check t see if the message code
                try:
                    gps_msg = pynmea2.parse(gps_data)
                    lat = gps_msg.latitude
                    lng = gps_msg.longitude
                    alt = gps_msg.altitude 
                    date = gps_msg.timestamp
                    return (lat,lng,alt,date)
                except:
                    return None
            
        return None

def get_gps_data():
    date = None
    lat  = None
    lon  = None
    alt  = None

    ser = _port_setup(gps_port)
    gps_coords = _parseGPSdata(ser)
    print(gps_coords)
    if gps_coords is not None:
        lat = gps_coords[0]
        lon = gps_coords[1]
        alt = gps_coords[2]
        date = gps_coords[3]

    return lat, lon, alt, date



if __name__ == "__main__":

    ser = _port_setup(gps_port)
    while True:
        print(get_gps_data())
        time.sleep(1)
