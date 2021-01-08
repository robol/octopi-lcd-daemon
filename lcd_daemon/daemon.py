import time, os, sys, threading
import requests, configparser, json

from . import lcddriver

class OctoPoller(threading.Thread):

    daemon = True

    def __init__(self, host, api_key):
        threading.Thread.__init__(self)

        self._host = host
        self._api_key = api_key
        self._printer = None
        self._jobs = None

        self._running = True
        self._interval = 5
        self._last_update = 0

    def get_printer(self):
        return self._printer

    def get_jobs(self):
        return self._jobs

    def get_last_update(self):
        return self._last_update

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            time.sleep(self._interval)

            try:
                job_r = requests.get(
                    'http://%s/api/job' % self._host,
                    headers = {
                        'X-Api-Key': self._api_key
                    }
                )
                jobs = json.loads(job_r.text)
                self._jobs = jobs
            except:
                self._jobs = None

            try:
                printer_r = requests.get(
                    'http://%s/api/printer' % self._host,
                    headers = { 'X-Api-Key': self._api_key }
                )
                printer = json.loads(printer_r.text)
                self._printer = printer
            except:
                self._printer = None

            self._last_update = time.time()

class LcdDaemon():

    def __init__(self):
        self._lcd = lcddriver.lcd()
        self._lcd.lcd_clear()
        self.define_symbols()

        if not os.path.exists('lcd-daemon.conf'):
            print("lcd-daemon.conf not found, aborting!")
            sys.exit(1)

        config = configparser.ConfigParser()
        config.read('lcd-daemon.conf')

        self._api_key = config['octopi']['api_key']
        self._host = config['octopi']['host']
        self._name = config['octopi']['name']

        self._poller = OctoPoller(self._host, self._api_key)
        self._poller.start()

    def define_symbols(self):
        # Clock symbol as 0x00
        clock = [ 0b00001110, \
                  0b00000100, \
                  0b00001110, \
                  0b00010101, \
                  0b00010111, \
                  0b00010001, \
                  0b00001110, \
                  0b00000000 ]
        self.save_symbol(0x00, clock)

        deg = [ 0b11000, \
                0b11000, \
                0b00000, \
                0b00111, \
                0b01000, \
                0b01000, \
                0b00111, \
                0b00000 ]
        self.save_symbol(0x08, deg)

        # Thermometer
        self.save_symbol(0x08 * 2,
            [ 0x04, 0x0A, 0x0A, 0x0A, \
              0x11, 0x11, 0x0E, 0x00 ])

        # Heater
        self.save_symbol(0x08 * 3,
           [ 0x00, 0x1F, 0x15, 0x11, \
             0x15, 0x1F, 0x00, 0x00 ])

    def save_symbol(self, address, rows):
        self._lcd.lcd_write(address | lcddriver.LCD_SETCGRAMADDR)
        for row in rows:
            self._lcd.lcd_write(row, lcddriver.Rs)

    def update_status(self):
        self._printer = self._poller.get_printer()
        self._jobs = self._poller.get_jobs()
        self._last_update = self._poller.get_last_update()

    def set_message(self, row, msg):
        # print("ROW = %d, %s" % (row, msg))
        msg = msg + " " * (16 - len(msg))
        self._lcd.lcd_display_string(msg, row)

    def update(self):
        self.update_status()

        counter = int(time.time() / 8) % 3
        scroll_counter = int(time.time() * 2)

        progress = None

        if self._printer is None:
            self.set_message(1, self._name)
            dots = "." * (counter + 1)
            spaces = " " * (2 - counter)
            self.set_message(2, spaces + dots + " starting " + dots)
            return

        state = self._printer["state"]

        if state["flags"]["printing"] and self._jobs is not None:
            progress = self._jobs["progress"]
            printTimeLeft = progress["printTimeLeft"]
            if printTimeLeft is None:
                printTimeLeftS = "N/A"
            else:
                printTimeLeft = round(printTimeLeft - time.time() + self._last_update)
                if printTimeLeft < 60:
                    printTimeLeftS = str(printTimeLeft) + "s"
                elif printTimeLeft < 3600:
                    secs = printTimeLeft % 60
                    mins = int((printTimeLeft - secs) / 60)
                    printTimeLeftS = "%2s:%2s" % (str(mins).zfill(2), str(secs).zfill(2))
                else:
                    secs = printTimeLeft % 60
                    mins = int((printTimeLeft - secs) / 60) % 60
                    hours = int((printTimeLeft - secs - mins * 60) / 3600)
                    printTimeLeftS = "%d:%2s:%2s" % (hours, str(mins).zfill(2), str(secs).zfill(2))

            printTimeLeftS = "\x00 " + printTimeLeftS
            progress_msg = "%2.1f%% %s" % (progress["completion"], printTimeLeftS.rjust(10))
            self.set_message(1, progress_msg)
        else:
            if counter == 0:
                self.set_message(1, self._printer["state"]["text"].center(16, ' '))
            else:
                self.set_message(1, self._name)

        temps = self._printer["temperature"]

        try:
            tool_temp = temps["tool0"]["actual"]
            bed_temp = temps["bed"]["actual"]
            tool_target = temps["tool0"]["target"]
            bed_target = temps["bed"]["target"]
            if counter == 0:
                self.set_message(2, "\x02 %3.0f\x01%s" % (tool_temp, '' if tool_target in [ None, 0.0 ] else '/%3.0f\x01' % tool_target))
            elif counter == 1:
                self.set_message(2, "\x03 %2.1f\x01%s" % (bed_temp, '' if bed_target in [ None, 0.0 ] else '/%2.1f\x01' % bed_target))
            else:
                if progress is not None:
                    nboxes = round(progress["completion"] / 100.0 * 15.0) + 1
                    # We do this by hand, since non-ASCII characters are
                    # not exposed by lcddriver
                    self._lcd.lcd_write(0xC0)
                    for i in range(nboxes):
                        self._lcd.lcd_write(0xFF, lcddriver.Rs)
                    self._lcd.lcd_write(ord('>'), lcddriver.Rs)
                    for i in range(16 - nboxes - 1):
                        self._lcd.lcd_write(ord(' '), lcddriver.Rs)
                else:
                    self.set_message(2, "No print started")
        except:
            return

