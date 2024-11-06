from typing import Optional
import logging
import datetime
from .devices import Device
from .util import data_item_prop, data_item_prop_opt, from_timestamp, ffmt

logger = logging.getLogger(__name__)

# Registered derive classes for realtime queries
RT_DEVICE_CLASSES = {}


def rt_register(dev_type_id):
    """ Register a class for realtime support"""
    def _wrapper(cls):
        global RT_DEVICE_CLASSES

        if dev_type_id in RT_DEVICE_CLASSES:
            raise ValueError(f"Realtime data class for device {dev_type_id} already defined")

        RT_DEVICE_CLASSES[dev_type_id] = cls
        return cls

    return _wrapper


@rt_register(-1)  # Default if none found
class DeviceRTData:
    """
    Base class for Real-Time Device Data API
    This class is derived by sub-classes depending on device type
    """

    RUN_STATES = {
        0: "Disconnected",
        1: "Connected",
    }

    def __init__(self, data: dict, devices: dict[str, Device]):
        """
        Initialize from JSON response
        """
        self._data = data
        self._dev_id = data["devId"]
        if self._dev_id not in devices:
            raise ValueError(f"Device {self._dev_id} not found for device realtime data")
        self._device = devices[self._dev_id]

    @classmethod
    def supported_devices(self) -> list[int]:
        """
        Return devices IDs that are supported for realtime data

        Returns:
            list of int, see Device.DEVICE_TYPES
        """
        return list(RT_DEVICE_CLASSES.keys())

    @staticmethod
    def from_list(data: list, devices: dict[str, Device]) -> list["DeviceRTData"]:
        """
        Parse real time data from a response

        Args:
          data: consumption data
          devices: dictionary of devices

        Returns:
          list: list of realtime data
        """
        global RT_DEVICE_CLASSES

        result = []
        for item in data:
            dev_id = item["devId"]
            if dev_id not in devices:
                raise ValueError(f"Device {dev_id} not found for device realtime data")
            device = devices[dev_id]
            if device.dev_type_id not in RT_DEVICE_CLASSES:
                logging.error(f"Realtime data class for device {device} not implemented - using default")
                DataCls = RT_DEVICE_CLASSES[-1]
            else:
                DataCls = RT_DEVICE_CLASSES[device.dev_type_id]

            result.append(DataCls(item, devices))

        return result

    @property
    def device(self) -> Device:
        """
        Corresponding device
        """
        return self._device

    @property
    def data(self) -> dict:
        """
        Data loaded from the response.
        """
        return self._data

    run_state_id = data_item_prop_opt("run_state", -1, "Run state as integer (int)")

    @property
    def collect_time(self) -> datetime:
        """
        Collect time as datetime.

        This is either:

        - Time of the request for real time data
        - For historical data, collect time as provided
        """
        if "collectTime" in self._data:
            return from_timestamp(self._data["collectTime"])
        return datetime.datetime.now()

    @property
    def run_state(self) -> int:
        """
        Run state as integer
        """
        return self.RUN_STATES.get(self.run_state_id, "Unknown")

    def __str__(self) -> str:
        return f"Device {self.device} - {self.run_state}"


@rt_register(1)  # String inverter
class DeviceRTDataSInverter(DeviceRTData):
    INVERTER_STATES = {
        0: "Standby: initializing",
        1: "Standby: insulation resistance detecting",
        2: "Standby: irradiation detecting",
        3: "Standby: grid detecting",
        256: "Start",
        512: "Grid-connected",
        513: "Grid-connected: power limited",
        514: "Grid-connected: self-derating",
        768: "Shutdown: on fault",
        769: "Shutdown: on command",
        770: "Shutdown: OVGR",
        771: "Shutdown: communication interrupted",
        772: "Shutdown: power limited",
        773: "Shutdown: manual startup required",
        774: "Shutdown: DC switch disconnected",
        1025: "Grid scheduling: cosψ-P curve",
        1026: "Grid scheduling: Q-U curve",
        1280: "Ready for terminal test",
        1281: "Terminal testing...",
        1536: "Inspection in progress",
        1792: "AFCI self-check",
        2048: "I-V scanning",
        2304: "DC input detection",
        40960: "Standby: no irradiation",
        45056: "Communication interrupted",
        49152: "Loading...",
    }

    inverter_state_id = data_item_prop("inverter_state", "Inverter state as integer (int)")

    @property
    def inverter_state(self) -> str:
        """
        Inverter state as string
        """
        return self.INVERTER_STATES.get(self.inverter_state_id, "Unknown")

    @property
    def diff_voltage(self) -> dict[str, Optional[float]]:
        """
        line voltage difference of grid (V)

        AB: A-B
        BC: B-C
        CA: C-A
        """
        return {diff.upper(): self._data["dataItemMap"].get(f"{diff}_u", None) for diff in ("ab", "bc", "ca")}

    @property
    def voltage(self) -> dict[str, Optional[float]]:
        """
        Voltage of lines A, B and C (V).
        Example: {"A": 10, "B": 20, "C": None}
        """
        return {phase.upper(): self._data["dataItemMap"].get(f"{phase}_u", None) for phase in "abc"}

    @property
    def current(self) -> dict[str, Optional[float]]:
        """
        Grid current of phases A, B and C (A).
        Example: {"A": 10, "B": 20, "C": None}
        """
        return {phase.upper(): self._data["dataItemMap"].get(f"{phase}_i", None) for phase in "abc"}

    efficiency = data_item_prop("efficiency", "Inverter conversion efficiency (manufacturer) in % (float)")
    temperature = data_item_prop("temperature", "Internal temperature in °C (float)")
    power_factor = data_item_prop("power_factor", "Power factor (float)")
    elec_freq = data_item_prop("elec_freq", "Grid frequency in Hz (float)")
    active_power = data_item_prop("active_power", "Active power in kW (float)")
    reactive_power = data_item_prop("reactive_power", "Output reactive power in kVar (float)")
    day_cap = data_item_prop("day_cap", "Yield today in kWh (float)")
    mppt_power = data_item_prop("mppt_power", "MPPT total input power in kW (float)")

    @property
    def pv_voltage(self) -> dict[int, float]:
        """
        PVx input voltage in V for each PV
        Example: {1: 10, 2: 10, 3: None}
        """
        result = {}
        for i in range(1, 29):
            key = f"pv{i}_u"
            if key in self._data["dataItemMap"]:
                result[i] = self._data["dataItemMap"][key]

        return result

    @property
    def pv_current(self) -> dict[int, float]:
        """
        PVx input current in A for each PV
        Example: {1: 10, 2: 10, 3: None}
        """
        result = {}
        for i in range(1, 29):
            key = f"pv{i}_i"
            if key in self._data["dataItemMap"]:
                result[i] = self._data["dataItemMap"][key]

        return result

    total_cap = data_item_prop("total_cap", "Total yield in kWh (float)")
    open_time = data_item_prop("open_time", "Inverter startup time (datetime)", conv=from_timestamp)
    close_time = data_item_prop("close_time", "Inverter shutdown time in (datetime)", conv=from_timestamp)

    @property
    def mppt_total_cap(self) -> float:
        """
        Total DC input energy in kWh
        """
        if "mppt_total_cap" in self._data["dataItemMap"]:
            return self._data["dataItemMap"]["mppt_total_cap"]
        # Not in residential inverter
        return sum(self.mppt_cap)

    @property
    def mppt_cap(self) -> dict[int, float]:
        """
        MPPT 1 DC total yield in kWh
        Example: {1: 10, 2: 10, 3: None}
        """
        result = {}
        for i in range(1, 29):
            key = f"mppt_{i}_cap"
            if key in self._data["dataItemMap"]:
                result[i] = self._data["dataItemMap"][key]

        return result

    def __str__(self) -> str:
        return f"""
{super().__str__()}
  {self.inverter_state} {self.temperature} °C
  Voltage  A:{ffmt(self.voltage['A'])} V  B:{ffmt(self.voltage['B'])} V  C:{ffmt(self.voltage['C'])} V  PV: {ffmt(self.pv_voltage)} V
  Current  A:{ffmt(self.current['A'])} A  B:{ffmt(self.current['B'])} A  C:{ffmt(self.current['C'])} A  PV: {ffmt(self.pv_current)} A
  """


@rt_register(38)  # Residential inverter - Same as String inverter
class DeviceRTDataRInverter(DeviceRTDataSInverter):
    pass


@rt_register(10)  # Environmental monitoring instrument (EMI)
class DeviceRTDataEMI(DeviceRTData):
    temperature = data_item_prop("temperature", "Temperature in °C (float)")
    pv_temperature = data_item_prop("pv_temperature", "PV temperature in °C (float)")
    wind_speed = data_item_prop("wind_speed", "Wind speed in m/s (float)")
    wind_direction = data_item_prop("wind_direction", "Wind direction in Degree (float)")
    radiant_total = data_item_prop("radiant_total", "Daily irradiation in MJ/m2 (float)")
    radiant_line = data_item_prop("radiant_line", "Irradiance in W/m2 (float)")

    def __str__(self) -> str:
        return f"""
{super().__str__()}
  Temperature: {ffmt(self.temperature)} °C  PV Temperature: {ffmt(self.pv_temperature)} °C
  Wind: {ffmt(self.wind_direction)} m/s {ffmt(self.wind_direction)} °
        """


@rt_register(17)  # Grid meter
class DeviceRTDataGMeter(DeviceRTData):
    @property
    def diff_voltage(self) -> dict[str, Optional[float]]:
        """
        line voltage difference of grid (V)

        AB: A-B
        BC: B-C
        CA: C-A
        """
        return {diff.upper(): self._data["dataItemMap"].get(f"{diff}_u", None) for diff in ("ab", "bc", "ca")}

    @property
    def voltage(self) -> dict[str, Optional[float]]:
        """
        Phase voltage of lanes A, B and C (AC output) in V
        Example: {"A": 10, "B": 20, "C": None}
        """
        return {phase.upper(): self._data["dataItemMap"].get(f"{phase}_u", None) for phase in "abc"}

    @property
    def current(self) -> dict[str, Optional[float]]:
        """
        Phase voltage of grid, lanes A, B and C in A
        Example: {"A": 10, "B": 20, "C": None}
        """
        return {phase.upper(): self._data["dataItemMap"].get(f"{phase}_i", None) for phase in "abc"}

    active_power = data_item_prop("active_power", "Active power in kW (float)")
    power_factor = data_item_prop("power_factor", "Power factor in % (float)")
    active_cap = data_item_prop("active_cap", "Active energy (positive active energy) in kWh (float)")
    reactive_power = data_item_prop("reactive_power", "Reactive power in kVar (float)")
    reverse_active_cap = data_item_prop("reverse_active_cap", "Negative active energy in kWh (float)")
    forward_reactive_cap = data_item_prop("forward_reactive_cap", "Positive reactive energy in kWh (float)")
    reverse_reactive_cap = data_item_prop("reverse_reactive_cap", "Negative reactive energy in kWh (float)")

    @property
    def active_power_phase(self) -> dict[str, Optional[float]]:
        """
        Active power of lanes A, B and C in kW
        Example: {"A": 10, "B": 20, "C": None}
        """
        return {phase.upper(): self._data["dataItemMap"].get(f"active_power_{phase}", None) for phase in "abc"}

    total_apparent_power = data_item_prop("total_apparent_power", "Total apparent power in kVA (float)")

    def __str__(self) -> str:
        return f"""
{super().__str__()}
  Voltage  A:{ffmt(self.voltage['A'])} V  B:{ffmt(self.voltage['B'])} V  C:{ffmt(self.voltage['C'])} V
  Current  A:{ffmt(self.current['A'])} A  B:{ffmt(self.current['B'])} A  C:{ffmt(self.current['C'])} A
  """


@rt_register(47)  # Power sensor
class DeviceRTDataPSensor(DeviceRTData):
    METER_STATUS = {0: "Offline", 1: "Normal"}

    meter_status_id = data_item_prop("meter_status", "Meter state as integer (int)")

    @property
    def meter_status(self) -> int:
        """
        Meter state as string
        """
        return DeviceRTDataPSensor.METER_STATUS.get(self.meter_status_id, "Unknown")

    voltage = data_item_prop("meter_u", "Phase A voltage (AC output) in V (float)")
    current = data_item_prop("meter_i", "Phase A current of grid in A (float)")
    active_power = data_item_prop("active_power", "Active power in W (float)")
    reactive_power = data_item_prop("reactive_power", "Reactive power in Var (float)")
    power_factor = data_item_prop("power_factor", "Power factor in % (float)")
    grid_frequency = data_item_prop("grid_frequency", "Grid frequency in Hz")
    active_cap = data_item_prop("active_cap", "Active energy (positive active energy) in kWh (float)")
    reverse_active_cap = data_item_prop("reverse_active_cap", "Negative active energy in kWh (float)")

    @property
    def diff_voltage(self) -> dict[str, Optional[float]]:
        """
        line voltage difference of grid (V)

        AB: A-B
        BC: B-C
        CA: C-A
        """
        return {diff.upper(): self._data.get(f"{diff}_u", None) for diff in ("ab", "bc", "ca")}

    @property
    def voltage_phase(self) -> dict[str, Optional[float]]:
        """
        Phase voltage of lanes A, B and C (AC output) in V
        Example: {"A": 10, "B": 20, "C": None}
        """
        return {phase.upper(): self._data.get(f"{phase}_u", None) for phase in "abc"}

    @property
    def current_phase(self) -> dict[str, Optional[float]]:
        """
        Phase voltage of grid, lanes A, B and C in A
        Example: {"A": 10, "B": 20, "C": None}
        """
        return {phase.upper(): self._data.get(f"{phase}_i", None) for phase in "abc"}

    @property
    def active_power_phase(self) -> float:
        """
        Active power, lanes A, B and C in kW
        """
        return {phase.upper(): self._data.get(f"active_power_{phase}", None) for phase in "abc"}

    def __str__(self) -> str:
        return f"""
{super().__str__()}
  Voltage  A:{ffmt(self.voltage_phase['A'])} V  B:{ffmt(self.voltage_phase['B'])} V  C:{ffmt(self.voltage_phase['C'])} V
  Current  A:{ffmt(self.current_phase['A'])} A  B:{ffmt(self.current_phase['B'])} A  C:{ffmt(self.current_phase['C'])} A
  """


@rt_register(39)
class DeviceRTDataRBattery(DeviceRTData):
    BATTERY_STATUS = {0: "offline", 1: "standby", 2: "running", 3: "faulty", 4: "hibernating"}

    CHARGE_MODE = {
        0: "none",
        1: "forced charge/discharge",
        2: "time-of-use price",
        3: "fixed charge/discharge",
        4: "automatic charge/discharge",
        5: "fully fed to grid",
        6: "TOU",
        7: "remote scheduling–max. self-consumption",
        8: "remote scheduling–fully fed to grid",
        9: "remote scheduling–TOU",
        10: "EMMA",
    }

    battery_status_id = data_item_prop("battery_status", "Battery running state as integer (int)")

    @property
    def battery_status(self) -> str:
        """
        Battery running state as string
        """
        return self.BATTERY_STATUS.get(self.battery_status_id, "Unknown")

    def __str__(self) -> str:
        return f"""
{super().__str__()}
  {self.battery_status}, charge model {self.charge_mode}
  Power {ffmt(self.ch_discharge_power)} W, soc {self.soc} %, soh {self.soh}%
  Charge cap {ffmt(self.charge_cap)} kWh, discharge cap {ffmt(self.discharge_cap)} kWh
  """

    max_charge_power = data_item_prop("max_charge_power", "Maximum charge power in W (float)")
    max_discharge_power = data_item_prop("max_discharge_power", "Maximum discharge power in W (float)")
    # Note: documentation says W instead of kW
    ch_discharge_power = data_item_prop("ch_discharge_power", "Charge/Discharge power in kW (float)")
    voltage = data_item_prop("busbar_u", "Battery voltage in V (float)")
    soc = data_item_prop("battery_soc", "Battery State of Charge (SOC) in %")
    soh = data_item_prop(
        "battery_soh", "Battery State of Health (SOH), supported only by LG batteries, in % (float)"
    )
    charge_mode_id = data_item_prop("ch_discharge_model", "Charge/Discharge mode as integer (int)")

    @property
    def charge_mode(self) -> str:
        """
        Charge/Discharge mode as string
        """
        return self.CHARGE_MODE.get(self.charge_mode_id, "Unknown")

    charge_cap = data_item_prop("charge_cap", "Charged energy in kWh (float)")
    discharge_cap = data_item_prop("discharge_cap", "Discharged energy in kWh (float)")


@rt_register(41)  # C&I and utility ESS
class DeviceRTDataCI(DeviceRTData):
    ch_discharge_power = data_item_prop("ch_discharge_power", "Charge/Discharge power in W (float)")
    soc = data_item_prop("battery_soc", "Battery State of Charge (SOC) in % (float)")
    soh = data_item_prop("battery_soh", "Battery State of Health (SOH) in % (float)")
    charge_cap = data_item_prop("charge_cap", "Charged energy in kWh (float)")
    discharge_cap = data_item_prop("discharge_cap", "Discharged energy in kWh (float)")

    def __str__(self) -> str:
        return f"""
{super().__str__()}
  Power {ffmt(self.ch_discharge_power)} W, soc {self.soc} %, soh {self.soh}%
  Charge cap {ffmt(self.charge_cap)} kWh, discharge cap {ffmt(self.discharge_cap)} kWh
  """


@rt_register(60001)  # Mains (supported only in the Power-M scenario)
class DeviceRTDataMains(DeviceRTData):
    MAINS_STATE = {
        0: "mains unavailable",
        1: "mains available",
    }

    GRID_QUALITY = {0: "Unknown", 1: "Class 1", 2: "Class 2", 3: "Class 3", 4: "Class 4"}

    mains_state_id = data_item_prop("mains_state", "Mains status as integer (int)")

    @property
    def mains_state(self) -> str:
        """
        Mains status as string
        """
        return self.MAINS_STATE.get(self.mains_state_id, "Unknown")

    ac_voltage = data_item_prop("ac_voltage", "AC voltage in V (float)")
    ac_current = data_item_prop("ac_current", "AC current in A (float)")
    active_power = data_item_prop("active_power", "Active power in kW (float)")
    ac_frequency = data_item_prop("ac_frequency", "AC frequency in Hz (float)")
    grid_quality_grade_id = data_item_prop("grid_quality_grade", "Power grid quality level as integer (int)")

    @property
    def grid_quality_grade(self) -> str:
        """
        Mains status as string
        """
        return self.GRID_QUALITY.get(self.grid_quality_grade_id, "Unknown")

    total_energy_consumption = data_item_prop("total_energy_consumption", "Total energy consumption in kWh (float)")
    supply_duration_per_total = data_item_prop("supply_duration_per_total", "Total power supply duration in h (float)")


@rt_register(60003)  # Genset (supported only in the Power-M scenario)
class DeviceRTDataGenset(DeviceRTData):
    RUN_STATES = {0: "unknown", 1: "stopped", 2: "running"}

    run_state_id = data_item_prop("running_state", "Running state as integer (int)")
    output_power = data_item_prop("output_power", "Output power in kW (float)")
    load_rate = data_item_prop("load_rate", "Load rate in % (float)")


@rt_register(60043)  # SSU group (supported only in the Power-M scenario)
class DeviceRTDataSSUG(DeviceRTData):
    total_output_current = data_item_prop("total_output_current", "Total output current in A (float)")
    total_output_power = data_item_prop("total_output_power", "Total output power in W (float)")


@rt_register(60044)  # SSU (supported only in the Power-M scenario)
class DeviceRTDataSSU(DeviceRTData):
    RUN_STATES = {0: "on", 1: "off"}

    input_voltage = data_item_prop("input_voltage", "Input voltage in V (float)")
    output_voltage = data_item_prop("output_voltage", "Output voltage in V (float)")
    output_current = data_item_prop("output_current", "Output current in A (float)")
    run_state_id = data_item_prop("on_off_state", "Power-on/off status as integer (int)")


@rt_register(60092)  # Power converter (supported only in the Power-M scenario)
class DeviceRTDataPConv(DeviceRTData):
    total_runtime = data_item_prop("total_runtime", "Total runtime in h (float)")
    pv_input_voltage = data_item_prop("pv_input_voltage", "PV input voltage in V (float)")
    pv_input_current = data_item_prop("pv_input_current", "PV input current in A (float)")
    pv_input_power = data_item_prop("pv_input_power", "PV input power in kW (float)")
    inverter_voltage = data_item_prop("inverter_voltage", "Inverter voltage in V (float)")
    inverter_frequency = data_item_prop("inverter_frequency", "Inverter frequency in Hz (float)")
    ac_output_voltage = data_item_prop("ac_output_voltage", "AC output voltage in V (float)")
    ac_output_current = data_item_prop("ac_output_current", "AC output current in A (float)")
    ac_output_frequency = data_item_prop("ac_output_frequency", "AC output frequency in kW")
    ac_output_apparent_power = data_item_prop("ac_output_apparent_power", "AC output apparent power in kVA (float)")


@rt_register(60014)  # Lithium battery rack (supported only in the Power-M scenario)
class DeviceRTDataLBat(DeviceRTData):
    BATTERY_STATE = {
        0: "initial power-on",
        1: "power-off",
        2: "float charging",
        3: "boost charging",
        4: "discharging",
        5: "charging",
        6: "testing",
        7: "hibernation",
        8: "standby",
    }

    battery_state_id = data_item_prop("battery_state", "Battery status as integer (int)")

    @property
    def battery_state(self) -> str:
        """
        Battery status as string
        """
        return self.BATTERY_STATE.get(self.battery_state_id, "Unknown")

    soc = data_item_prop("soc", "State of Charge (SOC) in % (float)")
    charge_discharge_power = data_item_prop("charge_discharge_power", "Charge/Discharge power in kW (float)")
    total_discharge = data_item_prop("total_discharge", "Total energy discharged in kWh (float)")
    voltage = data_item_prop("voltage", "Voltage in V (float)")
    current = data_item_prop("current", "Current in A (float)")
    remaining_backup_time = data_item_prop("remaining_backup_time", "Remaining power reserve duration in h (float)")
    total_discharge_times = data_item_prop("total_discharge_times", "Total discharge times (float)")
    total_capacity = data_item_prop("total_capacity", "Total capacity in kWh")


@rt_register(60010)  # AC output power distribution (supported only in the Power-M scenario)
class DeviceRTDataACOut(DeviceRTData):
    ac_voltage = data_item_prop("ac_voltage", "AC voltage in V (float)")
    ac_current = data_item_prop("ac_current", "AC current in A (float)")
    ac_frequency = data_item_prop("ac_frequency", "AC frequency in Hz (float)")
    active_power = data_item_prop("active_power", "Active power in kW (float)")
