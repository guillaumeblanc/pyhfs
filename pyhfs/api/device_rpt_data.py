import logging
from .devices import Device
from .util import data_prop, data_item_prop, from_timestamp, ffmt

logger = logging.getLogger(__name__)

# Registered derive classes for reporting queries
RPT_DEVICE_CLASSES = {}


def rpt_register(dev_type_id):
    """ Register a class for realtime support"""
    def _wrapper(cls):
        global RPT_DEVICE_CLASSES

        if dev_type_id in RPT_DEVICE_CLASSES:
            raise ValueError(f"Reporting data class for device {dev_type_id} already defined")

        RPT_DEVICE_CLASSES[dev_type_id] = cls
        return cls

    return _wrapper


@rpt_register(-1)  # Default if none found
class DeviceRptData:
    """
    Base class for reporting Device Data API (Hourly, daily, monthly, yearly)
    This class is derived by sub-classes depending on device type
    """

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
        return list(RPT_DEVICE_CLASSES.keys())

    @staticmethod
    def from_list(data: list, devices: dict[str, Device]) -> list["DeviceRptData"]:
        """
        Parse reporting data from a response

        Args:
          data: consumption data
          devices: dictionary of devices

        Returns:
          list: list of realtime data
        """
        global RPT_DEVICE_CLASSES

        result = []
        for item in data:
            dev_id = item["devId"]
            if dev_id not in devices:
                raise ValueError(f"Device {dev_id} not found for device reporting data")
            device = devices[dev_id]
            if device.dev_type_id not in RPT_DEVICE_CLASSES:
                logging.error(f"Reporting data class for device {device} not implemented - using default")
                DataCls = RPT_DEVICE_CLASSES[-1]
            else:
                DataCls = RPT_DEVICE_CLASSES[device.dev_type_id]

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

    collect_time = data_prop("collectTime", "Collection time (datetime)", conv=from_timestamp)

    def __str__(self) -> str:
        return f"Device {self.device} - {self.run_state}"


@rpt_register(39) # Residential battery
class DeviceRptDataRBattery(DeviceRptData):

    charge_cap = data_item_prop("charge_cap", "Charged energy in kWh (float)")
    discharge_cap = data_item_prop("discharge_cap", "Discharged energy in kWh (float)")
    charge_time = data_item_prop("charge_time", "Charging duration in h (float)")
    discharge_time = data_item_prop("discharge_time", "Discharging duration in h (float)")

    def __str__(self) -> str:
        return f"""
{super().__str__()}
  {ffmt(self.charge_cap)} kWh  {ffmt(self.discharge_cap)} kWh
  {ffmt(self.charge_time)} h   {ffmt(self.discharge_time)} h
  """



@rpt_register(1) # String inverter
class DeviceRptDataSInverter(DeviceRptData):

    installed_capacity = data_item_prop("installed_capacity", "Installed capacity in kWp (float)")
    product_power = data_item_prop("product_power", "Yield in kWh (float)")
    perpower_ratio = data_item_prop("perpower_ratio", "Specific energy in kWh/kWp (float)")

    def __str__(self) -> str:
        return f"""
{super().__str__()}
  {ffmt(self.product_power)} kWh  {ffmt(self.charge_time)} h
  """

@rpt_register(38) # Residential inverter
class DeviceRptDataRInverter(DeviceRptDataSInverter):
    # Same as String inverter
    pass


@rpt_register(41) # C&I and utility ESS
class DeviceRptDataCI(DeviceRptData):

    charge_cap = data_item_prop("charge_cap", "Charged energy in kWh (float)")
    discharge_cap = data_item_prop("discharge_cap", "Discharged energy in kWh (float)")

    def __str__(self) -> str:
        return f"""
{super().__str__()}
  {ffmt(self.charge_cap)} kWh  {ffmt(self.discharge_cap)} kWh
  """