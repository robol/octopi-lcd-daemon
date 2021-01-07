#!/usr/bin/env python3

API_KEY = "C2B8D8369DCC4DF1B307CC78AD134B59"

import requests, time, json, lcddriver

class LcdDaemon():

    def __init__(self):
        self._lcd = lcddriver.lcd()
        self._lcd.lcd_clear()

    def update_jobs(self):
        try:
            job_r = requests.get(
                'http://octopi.oleandri.tk/api/job',
                headers = {
                    'X-Api-Key': API_KEY
                }
            )
            jobs = json.loads(job_r.text)
            self._jobs = jobs
        except:
            self._jobs = None

    def update_printer(self):
        try:
            printer_r = requests.get(
                'http://octopi.oleandri.tk/api/printer',
                headers = { 'X-Api-Key': API_KEY }
            )
            printer = json.loads(printer_r.text)
            self._printer = printer
        except:
            self._printer = None


    def set_message(self, row, msg):
        # print("ROW = %d, %s" % (row, msg))
        msg = msg + " " * (16 - len(msg))
        self._lcd.lcd_display_string(msg, row)

    def update(self):
        self.update_jobs()
        self.update_printer()

        counter = int(time.time() / 8) % 3

        progress = None

        if self._printer is None:
            self.set_message(1, "Oleandri Printer")
            dots = "." * (counter + 1)
            self.set_message(2, dots + " starting " + dots)
            return

        state = self._printer["state"]

        if state["flags"]["printing"] and self._jobs is not None:
            progress = self._jobs["progress"]
            printTimeLeft = progress["printTimeLeft"]
            if printTimeLeft is None:
                printTimeLeftS = "N/A"
            else:
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

            printTimeLeftS = "> " + printTimeLeftS

            progress_msg = "%2.1f%% %s" % (progress["completion"], printTimeLeftS.rjust(10))
            self.set_message(1, progress_msg)
        else:
            if counter == 0:
                self.set_message(1, self._printer["state"]["text"].center(16, ' '))
            else:
                self.set_message(1, "Oleandri Printer")

        temps = self._printer["temperature"]

        try:
            tool_temp = temps["tool0"]["actual"]
            bed_temp = temps["bed"]["actual"]
            tool_target = temps["tool0"]["target"]
            bed_target = temps["bed"]["target"]
            if counter == 0:
                self.set_message(2, "Tool: %3.0fC%s" % (tool_temp, '' if tool_target in [ None, 0.0 ] else '/%3.0fC' % tool_target))
            elif counter == 1:
                self.set_message(2, "Bed: %2.0fC%s" % (bed_temp, '' if bed_target in [ None, 0.0 ] else '/%2.0fC' % bed_target))
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


if __name__ == "__main__":

    daemon = LcdDaemon()

    while True:
        daemon.update()
        time.sleep(1.5)
