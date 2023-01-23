# control the elements of the Duet 3 board

import time
import serial
import json

import threading

class DuetController:
    def __init__(self, port):
        self._communicator = DuetCommunicator(port)
        self._pump_controller = DuetPumpController(self._communicator)

        self._objects = []
        self._next_temp_sensor = 0
        self._next_heater = 0
        self._next_output = 0
        self._next_pump = 0

    def connect(self):
        """
        open the connection to the board and make sure it's the right version.
        must be called first!
        """
        self._communicator.connect()

    def reset(self):
        """
        reset the board to stop all activity and clear out any existing objects.
        should be called at the beginning of the program right after connecting
        to make sure the board is in a clean state and at the end of the
        program to make sure the board does not leave any outputs on.
        """
        self._pump_controller._stop()
        self._communicator.reset()

    def create_thermistor(self, pin, resistance, b, c=0):
        """
        create a thermistor object for temperature monitoring or as a control
        input to a heater

        pin: which temperature input pin on the board to use
        resistance: thermistor resistance in ohms
        b: calibration Steinhart-Hart beta value
        c: calibration Steinhart-Hart C value
        """

        obj = TempSensor(self._communicator,
            self._next_temp_sensor, pin, "thermistor", (resistance, b, c))
        self._objects.append(obj)
        self._next_temp_sensor += 1

        return obj

    def create_thermocouple(self, pin, kind):
        """
        create a thermocouple object for temperature monitoring or as a control
        input to a heater

        pin: which temperature input pin on the board to use
             (on the adapter board, TC0=spi.cs0 and TC1=spi.cs1)
        kind: thermocouple kind letter: B, E, J, K, N, R, S or T
        """

        obj = TempSensor(self._communicator,
            self._next_temp_sensor, pin, "thermocouple", (kind,))
        self._objects.append(obj)
        self._next_temp_sensor += 1

        return obj

    def create_heater(self, pin, temp_sensor, rate, tc, dt, invert=False):
        """
        create a heater object for automatic temperature control

        pin: which output pin on the board the heater is attached to
        temp_sensor: temperature sensor object used to control the heater
        rate: process heating rate at ambient in degrees C/sec
        tc: process time constant
        dt: process dead time in seconds
        invert: if True, invert output i.e. it's a cooler
        """

        obj = Heater(self._communicator, self._next_heater, pin,
            temp_sensor, rate, tc, dt, invert)
        self._objects.append(obj)
        self._next_heater += 1

        return obj

    def create_output(self, pin, pwm_freq=None):
        """
        create a generic output object for valve or DC motor control

        pin: which output pin on the board to create an output for
        pwm_freq: PWM output frequency in Hz. for motors, >20KHz is inaudible
        """

        obj = Output(self._communicator, self._next_output, pin, pwm_freq)
        self._objects.append(obj)
        self._next_output += 1

        return obj

    def create_pump(self, driver, peak_current, steps_per_rev, revs_per_ml,
            invert=False):
        """
        create a pump object for precise rate-based pump stepper control

        driver: driver number that pump is attached to
        peak_current: peak drive current, in milliamps
        steps_per_rev: number of steps per revolution of the pump motor, should
                       be obtainable from its specifications
        revs_per_ml: number of revolutions per milliliter of liquid pumped, must
                     be manually calibrated
        invert: invert direction of pump motor
        """

        # we don't particularly care about the distinction
        steps_per_ml = float(steps_per_rev)*float(revs_per_ml)
        obj = Pump(self._communicator, self._pump_controller,
            self._next_pump, driver,
            peak_current, steps_per_ml, invert)
        self._objects.append(obj)
        self._next_pump += 1

        return obj

    def finish_creation(self):
        """
        finish creation of all objects.
        must be called exactly once, after all create_* functions and before any
        other function!
        """

        # tell the pump objects to finish configuration
        for obj in self._objects:
            if isinstance(obj, Pump):
                obj._finish_configuration()

        # wait until each object has a valid value
        all_valid = False
        while not all_valid:
            all_valid = True
            for obj in self._objects:
                all_valid = all_valid and obj.get_value() is not None

        # allow movement without axes being homed and outside of defined volume
        self._communicator._command('M564 S0 H0')

        self._pump_controller._start()


# we have a separate pump controller that sends pump commands in the background.
# these commands use the duet's normal G code movement operators. because
# movement is buffered and there's no real way to clear the buffer, we need to
# send a continuous series of small movements instead of one big movement that
# lasts the whole experiment. this lets us change rates and stop the pumps
# according to the user's desires. this also means the pumps stop automatically
# shortly after the program stops.
class DuetPumpController:
    def __init__(self, communicator):
        self._communicator = communicator
        self._pump_rates = []

        self._running = False
        self._pump_cmd_thread = None

    def _start(self):
        self._running = True
        self._pump_cmd_thread = threading.Thread(
            target=self._pump_cmd_fn, daemon=True)
        self._pump_cmd_thread.start()

    def _stop(self):
        self._running = False
        if self._pump_cmd_thread is not None:
            self._pump_cmd_thread.join()
        self._pump_cmd_thread = None

    def _set_rate(self, index, ml_per_min):
        while index >= len(self._pump_rates):
            self._pump_rates.append(0)

        self._pump_rates[index] = ml_per_min

    def _pump_cmd_fn(self):
        dt = 0.25 # movement command time in seconds
        curr_rates = [None]*len(self._pump_rates)
        dest_pos = [0]*len(self._pump_rates)

        long_loops = 0
        next_time = time.monotonic() + dt
        while self._running:
            # check and update pump rates. it's unclear if these take effect for
            # moves already in the buffer, but that doesn't really matter
            # except for possibly adding a short delay.
            curr_rates = self._update_pump_rates(curr_rates, self._pump_rates)

            # retrieve current axis position from monitoring thread
            curr_pos = [self._communicator._get_status_value(
                        lambda s: float(
                            s["move"]["axes"][idx]["machinePosition"]))[1]
                for idx in range(len(curr_rates))
            ]

            # each G1 movement command tells the duet the desired cumulative
            # pump volume of each pump. a command is considered complete when
            # all pumps have reached the volume specified in the command. the
            # speed of the movement for each pump is defined by the feed rate
            # command. this implies all pump volumes must increase each command
            # in order for them to run continuously. the duet plans ahead, so
            # we have to have a few moves in the buffer at all times for
            # movement to not be erratic. additionally, the reported position
            # only updates after a command completes.

            # for each axis which is moving, send enough commands to put its
            # volume 4 command times out based on the current position and
            # movement rate. each command is only 1 command time long so we get
            # useful position updates. this implies changes in rate may take up
            # to 4 command times to take effect (1 second by default). the pump
            # might stop completely for a moment if the new rate is less than
            # 1/4 the old one but that situation is unlikely and the
            # consequences are minimal.
            NC = 4 # number of commands
            # the loop sends multiple commands this command time if necessary
            for cmd in range(NC):
                updated = False
                for idx, rate in enumerate(curr_rates):
                    if rate == 0: continue # ignore inactive pumps
                    # will this pump reach its volume soon?
                    if abs(dest_pos[idx]-curr_pos[idx]) < NC*(abs(rate)/60*dt):
                        # yes, so we need to send an update
                        updated = True

                if updated:
                    for idx, rate in enumerate(curr_rates):
                        # move all pumps forward at their desired rate, even
                        # ones which aren't close enough to trigger an update,
                        # so that they don't stop for a moment
                        dest_pos[idx] += (rate/60*dt)

                    # build and send movement command
                    move_cmd = "G1 "
                    for idx, dest in enumerate(dest_pos):
                        move_cmd += f"{Pump.AXIS_LETTERS[idx]}{dest} "
                    self._communicator._command(move_cmd)

            try:
                time.sleep(next_time - time.monotonic())
            except ValueError as e:
                # the board can take a long time to respond especially during
                # the end of init. give it three long responses before giving
                # up and complaining something is wrong
                print("WARNING: long pump command loop")
                long_loops += 1
                if long_loops == 4:
                    raise e from None
                next_time = time.monotonic()
            next_time += dt

    def _update_pump_rates(self, curr_rates, desired_rates):
        # make copy in case anyone sets a rate while we are updating
        desired_rates = desired_rates[:]
        for curr_rate, desired_rate in zip(curr_rates, desired_rates):
            if curr_rate != desired_rate:
                break
        else:
            return curr_rates

        # set maximum feed rate for all axes and set minimum feed rate to 0% of
        # maximum
        rate_cmd = "M203 I0 "
        for idx, rate in enumerate(desired_rates):
            rate_cmd += f"{Pump.AXIS_LETTERS[idx]}{abs(rate)} "
        self._communicator._command(rate_cmd)

        return desired_rates # rates are now all updated


class DuetCommunicator:
    def __init__(self, port):
        self._connected = False

        self._port = None
        self._port_name = port
        self._comm_lock = threading.Lock()

        self._monitor_thread = None
        self._latest_status = None
        self._status_lock = threading.Lock()

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
                    port = serial.Serial(self._port_name, timeout=1)
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
                port.write(b"\nM115\n")

                try:
                    fwinfo = port.readline()
                    ok = port.readline()
                except (serial.SerialException, serial.SerialTimeoutException):
                    continue

                # make sure the version response looks coherent
                if b"FIRMWARE_VERSION" in fwinfo and ok == b"ok\n":
                    break

                # if it doesn't, give the board a bit to finish responding
                # before we clear it out next go around
                time.sleep(0.25)
            else:
                raise Exception("timed out connecting")

            if b"FIRMWARE_VERSION: 3.3" not in fwinfo:
                print("WARNING: Duet firmware version is unsupported!")

            self._port = port
            self._connected = True

            self._monitor_thread = threading.Thread(
                target=self._monitor_fn, daemon=True)
            self._monitor_thread.start()

    def reset(self):
        with self._comm_lock:
            if not self._connected:
                raise Exception("not connected")

            # shut down monitor thread
            self._connected = False
            self._monitor_thread.join(timeout=1)

            # request software reset
            self._port.write(b"\nM999\n")

            self._port.close()
            self._port = None
            self._connected = False

        time.sleep(3)
        self.connect()

    def _command(self, cmd, response_expected=False):
        with self._comm_lock:
            if not self._connected:
                raise Exception("not connected")

            self._port.write((cmd+"\n").encode("ascii"))

            extra_resp = []
            while True:
                resp = self._port.readline()[:-1]
                if resp == b"ok":
                    break

                extra_resp.append(resp.decode("ascii"))

        if len(extra_resp) > 0 and not response_expected:
            raise Exception(f"unexpected response: {extra_resp[0]}")

        if response_expected:
            return extra_resp

        return extra_resp

    def _monitor_fn(self):
        monitor_interval = 0.5

        long_loops = 0
        next_time = time.monotonic() + monitor_interval
        while self._connected:
            try:
                status = self._command(
                    'M409 F"f,d3"', # get frequently changing values
                    response_expected=True
                )[0] # remove trailing blank line
            except:
                break

            status = json.loads(status)
            with self._status_lock:
                self._latest_status = status

            try:
                time.sleep(next_time - time.monotonic())
            except ValueError as e:
                # the board can take a long time to respond especially during
                # the end of init. give it three long responses before giving
                # up and complaining something is wrong
                print("WARNING: long monitoring loop")
                long_loops += 1
                if long_loops == 4:
                    raise e from None
                next_time = time.monotonic()
            next_time += monitor_interval

    def _get_status_value(self, fn):
        with self._status_lock:
            if self._latest_status is None:
                return None

            status = self._latest_status

        status_time = (status["result"]["state"]["upTime"] +
            status["result"]["state"]["msUpTime"]/1000)

        try:
            value = fn(status["result"])
        except (IndexError, KeyError):
            return None

        return status_time, value


class TempSensor:
    def __init__(self, communicator, index, pin, kind, params):
        self._communicator = communicator
        self._index = index
        self._pin = pin
        self._kind = kind
        if kind == "thermistor":
            self._params = tuple(float(v) for v in params)
        elif kind == "thermocouple":
            self._params = tuple(str(v) for v in params)

        self._configure()

    def _configure(self):
        if self._kind == "thermistor":
            self._communicator._command(
                f'M308 ' # set temperature sensor parameter
                f'S{self._index} ' # with our index
                f'P"{self._pin}" ' # on the given pin
                f'Y"thermistor" ' # and parameters
                f'T{self._params[0]} B{self._params[1]} C{self._params[2]}'
            )
        elif self._kind == "thermocouple":
            self._communicator._command(
                f'M308 ' # set temperature sensor paramter
                f'S{self._index} ' # with our index
                f'P"{self._pin}" ' # on the given pin
                f'Y"thermocouple-max31856" ' # and parameters
                f'K"{self._params[0]}"'
            )
        else:
            raise Exception(f"unknown temp sensor kind {self.kind}")

    def get_value(self):
        """
        return the current value of the sensor in degrees Celsius
        """
        value = self._communicator._get_status_value(
            lambda s: float(
                s["sensors"]["analog"][self._index]["lastReading"]))

        if value is not None:
            return value[1]
        else:
            return None


class Heater:
    def __init__(self, communicator, index, pin,
            temp_sensor, rate, tc, dt, invert):
        self._communicator = communicator
        self._index = index
        self._pin = pin
        self._temp_sensor = temp_sensor
        self._rate = float(rate)
        self._tc = float(tc)
        self._dt = float(dt)
        self._invert = bool(invert)

        self._configure()

    def _configure(self):
        self._communicator._command(
            f'M950 ' # create heater
            f'H{self._index} ' # with our index
            f'C"{self._pin}" ' # on the given pin
            f'T{self._temp_sensor._index}' # using the given temperature sensor
        )

        self._communicator._command(
            f'M563 ' # create tool (so the heater can have a temperature)
            f'P{self._index} H{self._index}' # with the same index
        )

        self._communicator._command(
            f'M307 ' # set heating process parameters
            f'H{self._index} '
            f'R{self._rate} C{self._tc} D{self._dt} I{int(self._invert)}'
        )

        self.disable()

    def enable(self, temperature):
        """
        enable temperature control and set target temperature in degrees Celsius
        """
        self._communicator._command(
            f'M568 ' # set tool settings
            f'P{self._index} ' # of the tool this heater is attached to
            f'S{float(temperature)} ' # set active temperature
            f'A2' # activate active temperature
        )

    def disable(self):
        """
        disable temperature control and turn off heater
        """
        self._communicator._command(
            f'M568 ' # set tool settings
            f'P{self._index} ' # of the tool this heater is attached to
            f'A0' # disable the heater
        )

    def get_value(self):
        """
        return average PWM value where 0 = fully off and 1 = fully on. this is
        useful to determine how hard the heater is working and whether the
        control is stable.

        NOTE: NOT ACTUALLY IMPLEMENTED YET
        """
        return 0
        # when we upgrade to 3.4
        # value = self._communicator._get_status_value(
        #     lambda s: float(s["heat"]["heaters"][self._index]["avgPwm"]))
        #
        # if value is not None:
        #    return value[1]
        # else:
        #    return None


class Output:
    def __init__(self, communicator, index, pin, pwm_freq):
        self._communicator = communicator
        self._index = index
        self._pin = pin
        self._pwm_freq = int(pwm_freq) if pwm_freq is not None else None

        self._configure()

    def _configure(self):
        self._communicator._command(
            f'M950 ' # create GPIO
            f'P{self._index} ' # with our index
            f'C"{self._pin}"' # on the given pin
            # at the desired PWM frequency (if not default)
            +(f' Q{self._pwm_freq}' if self._pwm_freq is not None else '')
        )

    def set_value(self, value):
        """
        set output value where 0 = fully off and 1 = fully on. intermediate
        values are generated via PWM.
        """
        value = float(value)
        if value < 0 or value > 1:
            raise ValueError(f"invalid output value {value}")

        self._communicator._command(
            f'M42 ' # set output value
            f'P{self._index} ' # with our index
            f'S{value}' # to the given value
        )

    def get_value(self):
        """
        return current output value where 0 = fully off and 1 = fully on. this
        may not reflect the set value immediately.
        """
        value = self._communicator._get_status_value(
            lambda s: float(s["state"]["gpOut"][self._index]["pwm"]))

        if value is not None:
            return value[1]
        else:
            return None

class Pump:
    AXIS_LETTERS = "XYZUVWABC"

    def __init__(self, communicator, pump_controller, index, driver,
            peak_current, steps_per_ml, invert):
        self._communicator = communicator
        self._pump_controller = pump_controller
        self._index = index
        self._driver = int(driver)
        self._peak_current = float(peak_current)
        self._steps_per_ml = float(steps_per_ml)
        self._invert = bool(invert)

        self._configure()

    def _configure(self):
        L = Pump.AXIS_LETTERS[self._index]
        self._communicator._command(
            f'M584 ' # set drive mapping
            f'{L}{self._driver}' # for our axis to our driver
        )

        # M584 has to be before all instances of most motor configuration
        # commands according to the docs, so we postpone the majority of the
        # config until all objects are created

        # but make sure the pump controller is aware of us by setting a rate
        self.set_rate(0)

    def _finish_configuration(self):
        L = Pump.AXIS_LETTERS[self._index]

        self._communicator._command(
            f'M569 ' # set driver direction
            f'P{self._driver} ' # for our driver
            f'S{int(not self._invert)}' # 0 = inverted, 1 = regular
        )

        self._communicator._command(
            f'M92 ' # set steps per unit (which we call milliliters)
            f'{L}{self._steps_per_ml}' # for our axis to our value
        )

        self._communicator._command(
            f'M906 ' # set motor current
            f'{L}{self._peak_current}' # for our axis to our value
        )

    def set_rate(self, ml_per_min):
        """
        set pump rate in milliliters per minute
        (can be negative to run pump backwards)
        """

        self._pump_controller._set_rate(self._index, ml_per_min)

    def get_value(self):
        """
        return total accumulated pumped volume in milliliters
        """
        value = self._communicator._get_status_value(
            lambda s: float(s["move"]["axes"][self._index]["machinePosition"]))

        if value is not None:
            return value[1]
        else:
            return None