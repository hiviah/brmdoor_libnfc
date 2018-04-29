#!/bin/bash


#Prepare input PIN as input with pullup for the OPEN/CLOSED switch
#Configure the same PIN number in brmdoor_nfc.config in [open_switch] section
export PIN=22

if [ '!' -d /sys/class/gpio/gpio$PIN ]; then
    echo $PIN > /sys/class/gpio/export
    echo in > /sys/class/gpio/gpio$PIN/direction
fi

python -c "import wiringpi; wiringpi.wiringPiSetupGpio(); wiringpi.pinMode($PIN, wiringpi.INPUT); wiringpi.pullUpDnControl($PIN, wiringpi.PUD_UP)"

cd /root/brmdoor_libnfc/
/usr/bin/python2 brmdoor_nfc_daemon.py brmdoor_nfc.config

