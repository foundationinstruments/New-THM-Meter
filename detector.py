# control the elements of the detector module

import time
import serial

import threading

class Detector:
    def __init__(self, port):
        self._connected = False

        self._port = None
        self._port_name = port
        self._comm_lock = threading.Lock()

        self._receive_thread = None

        self._new_samples_available = threading.Condition()
        self._latest_samples = []

    def connect(self):
        with self._comm_lock:
            if self._connected:
                raise Exception("already connected")

            # NOTE FOR THE FUTURE: if this function gives lots of exceptions,
            # do "sudo systemctl disable ModemManager" and reboot

            port = None
            # try several times to open the port in case it is busy for whatever
            # reason or the board has not yet finished powering on and is not
            # yet present
            for attempt in range(5):
                try:
                    port = serial.Serial(self._port_name, 115200, timeout=1.0)
                except serial.SerialException:
                    if attempt == 4:
                        raise
                    else:
                        time.sleep(1)
                        continue

            for attempt in range(3):
                # request firmware version after erasing any garbage or desynced
                # responses in the buffers
                port.reset_input_buffer()
                port.reset_output_buffer()
                port.write(b"Q0\n")

                try:
                    fwinfo = port.readline()
                    ok = port.readline()
                except (serial.SerialException, serial.SerialTimeoutException):
                    continue

                # make sure the version response looks coherent
                if fwinfo.startswith(b"Q") and ok == b"C OK\n":
                    break

                # if it doesn't, give the board a bit to finish responding
                # before we clear it out next go around
                time.sleep(0.25)
            else:
                raise Exception("timed out connecting")

            if fwinfo != b"Q V0.1\n":
                print("WARNING: Detector firmware version is unsupported!")

            self._port = port
            self._connected = True

            self._receive_thread = threading.Thread(
                target=self._receive_fn, daemon=True)
            self._receive_thread.start()

    def _receive_fn(self):
        while self._connected:
            try:
                with self._comm_lock:
                    if not self._connected:
                        raise Exception("not connected")

                    line = self._port.readline()[:-1].decode("ascii")
            except:
                import traceback
                traceback.print_exc()

                break

            if line == "C OK":
                continue
            elif line == "C ERR":
                raise Exception("error reply")

            linebits = line.split()
            if linebits[0] != "V":
                raise Exception("unknown reply "+line)

            sample_index = int(linebits[1])
            bits = list(float(v) for v in linebits[2:])

            with self._new_samples_available:
                self._latest_samples.append((sample_index, *bits))
                self._new_samples_available.notify()

    def get_latest_samples(self, wait=True):
        """
        first value: sample index
        second value: actual control voltage in volts.
            this will be slightly different than the desired control voltage
            due to ADC inaccuracy, etc.
        third value: calculated system voltage (5Vusb) in volts.
            this is the voltage used to generate all the other outputs, so it
            is important that it be stable! slow fluctuations are compensated
            for, but it it changes a lot there might be problems.
        fourth value: actual LED voltage in volts.
            this is correlated with LED heat and light output so it might be
            interesting to monitor. also useful for diagnosis: ~0V = LED power
            input not present or LED short, ~24V = LED open circuit
        fifth value: detector signal voltage in millivolts.
            peaks out at around 1650mV.
        """

        with self._new_samples_available:
            if wait:
                while len(self._latest_samples) == 0:
                    self._new_samples_available.wait()

            latest_samples = self._latest_samples
            self._latest_samples = []

        return latest_samples

    def set_detector_control_voltage(self, voltage):
        """
        set detector control voltage output, in volts
        """

        voltage = float(voltage)
        if voltage < 0 or voltage > 1:
            raise ValueError("voltage must be between 0 and 1")

        with self._comm_lock:
            self._port.write(f"D{voltage}\n".encode("ascii"))

    def set_led_current(self, current):
        """
        set led supply current, in amps
        """

        current = float(current)
        if current < 0 or current > 1:
            raise ValueError("current must be between 0 and 1")

        with self._comm_lock:
            self._port.write(f"L{current}\n".encode("ascii"))
