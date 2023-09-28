# Code
This folder contains the code to run the star tracker. The code was developed for a Raspberry Pi 3B+, and is entirely written in Python.

The required libraries can be installed as root with:
```
# pip3 install -r requirements.txt
```

Furthermore, `startracker.service` can be installed with:
```
# mv startracker.service /etc/systemd/system/
# enable startracker.service
```