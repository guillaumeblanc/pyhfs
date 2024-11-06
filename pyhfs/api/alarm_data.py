import datetime
import logging

from .plants import Plant
from .devices import Device
from .util import data_prop, from_timestamp

logger = logging.getLogger(__name__)


class AlarmData:
    """
    API for "Querying Active Alarms"
    """

    ALARM_TYPES = {
        0: "other alarms",
        1: "transposition signal",
        2: "exception alarm",
        3: "protection event",
        4: "notification status",
        5: "alarm information",
    }

    LEVELS = {
        1: "critical",
        2: "major",
        3: "minor",
        4: "warning",
    }

    STATUS = {
        1: "not processed (active)",
    }

    def __init__(self, data: dict, plants: dict[str, Plant]):
        """
        Initialize from JSON response

        Args:
            data: response from the API for a Device
            plant: dictionary of plants
        """
        self._data = data
        if self.station_code not in plants:
            raise ValueError(f"Plant/Station {self.station_code} not found for device {self}")
        self._plant = plants[self.station_code]
        self._device = None
        for dev in self._plant.devices:
            if self.dev_name == dev.name:
                self._device = dev
                break
        if self._device is None:
            logger.warning("Did not find a device matching alarm {self}")

    @staticmethod
    def from_list(data: list, plants: dict[str, "Plant"]) -> list["AlarmData"]:
        """
        Create a list of alarms from a response

        Args:
          data: list of devices from Api
          plants: dictionary of plants

        Returns:
          list: of alarms
        """
        return [AlarmData(item, plants) for item in data]

    def __str__(self) -> str:
        return f"""{self.plant} {self.dev_name}: {self.name}
{self.level.upper()} {self.cause_id}: {self.cause} - {self.type}
{self.repair_suggestion}
        """

    @property
    def plant(self) -> Plant:
        """
        Related plant/station
        """
        return self._plant

    @property
    def device(self) -> Plant:
        """
        Related device
        """
        return self._device

    station_code = data_prop("stationCode", "Plant ID, which uniquely identifies a plant (str)")
    name = data_prop("alarmName", "Alarm name (str)")
    dev_name = data_prop("devName", "Device name (str)")
    repair_suggestion = data_prop("repairSuggestion", "")
    dev_sn = data_prop("esnCode", "Device SN")
    dev_type_id = data_prop("devTypeId", "Device type as integer (int)")

    @property
    def dev_type(self) -> str:
        """
        Device type as string
        """
        return Device.DEVICE_TYPES.get(self.dev_type_id, Device.UNKNOWN_DEVICE)

    cause_id = data_prop("causeId", "Cause ID (int)")
    cause = data_prop("alarmCause", "Cause (str)")
    alarm_type_id = data_prop("alarmType", "Alarm type as integer (int)")

    @property
    def alarm_type(self) -> str:
        """
        Alarm type as string
        """
        return self.ALARM_TYPES.get(self.alarm_type_id, "Unknown")

    raise_time = data_prop("raiseTime", "Raise time (datetime)", conv=from_timestamp)
    id = data_prop("alarmId", "Alarm ID (int)")
    station_name = data_prop("stationName", "Plant name (str)")
    level_id = data_prop("lev", "Level as integer (int)")

    @property
    def level(self) -> str:
        """
        Alarm type as string
        """
        return self.LEVELS.get(self.level_id, "Unknown")

    status_id = data_prop("status", "Alarm status as integer")

    @property
    def status(self) -> str:
        """
        Alarm status as string
        """
        return self.STATUS.get(self.status_id, "Unknown")
