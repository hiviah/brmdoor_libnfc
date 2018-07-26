#!/bin/bash
# This is example script to force unlock the lock in case the reader HW is
# dead, kernel driver misbehaves or reader cable is damaged.

export PIN=25

if [ '!' -d /sys/class/gpio/gpio$PIN ]; then
    echo $PIN > /sys/class/gpio/export
    echo out > /sys/class/gpio/gpio$PIN/direction
fi

echo 1 > /sys/class/gpio/gpio$PIN/value; sleep 5; echo 0 > /sys/class/gpio/gpio$PIN/value
