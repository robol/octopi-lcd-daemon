# OctoPi LCD Daemon

This repository contains a simple daemon that updates a standard HD44780
LCD screen with the information of an OctoPi instance. It can be configured
to get that info using the configuration file ```lcd-daemon.conf```. 

## Instructions

To get started, copy the files in ```/home/pi/lcd-daemon``` on your 
Raspberry PI, create ```lcd-daemon.conf``` and adjust your settings
(you will need to generate an Application Key from the OctoPi web
interface), and then run 
```bashe
sudo make install
sudo systemctl daemon-reload
sudo systemctl enable lcd-daemon
sudo systemctl start lcd-daemon
```
The LCD screen should be connected through I2C.

## Credits

The LCD library is adapted from [here](https://github.com/sweetpi/python-i2c-lcd). All the code
is released under the GPL version 2. 
