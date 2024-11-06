import sys
import itertools
import datetime
import logging
from typing import Iterable

from . import session
from .api.plants import Plant
from .api.devices import Device
from .api.plant_data import PlantRealTimeData, PlantHourlyData, PlantDailyData, PlantMonthlyData, PlantYearlyData
from .api.device_rt_data import DeviceRTData
from .api.device_rpt_data import DeviceRptData
from .api.alarm_data import AlarmData
from .api.util import to_timestamp

try:
    from itertools import batched
except ImportError:
    # Added in version 3.12
    def batched(iterable: Iterable, n: int) -> Iterable:
        if n < 1:
            raise ValueError("n must be at least one")
        iterator = iter(iterable)
        while batch := tuple(itertools.islice(iterator, n)):
            yield batch

# Based on documentation iMaster NetEco V600R023C00 Northbound Interface Reference-V6(SmartPVMS)
# https://support.huawei.com/enterprise/en/doc/EDOC1100261860/

logger = logging.getLogger(__name__)

class Client:
    def __init__(self, session: session.Session):
        self.session = session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_plant_list(self) -> dict[str, Plant]:
        """
        Get basic plants information.
        Implementation wraps a call to the Plant List Interface, see documentation 7.1.3
        This implementation will query all available pages

        Returns:
            dict[str,Plant]: dict of code->Plant
        """
        plants = {}
        for page in itertools.count(start=1):
            param = {"pageNo": page, "pageSize": 100}
            logger.debug(f"Get plant list for page {page}")
            response = self.session.post(endpoint="stations", parameters=param)["data"]
            plants.update(Plant.from_list(response.get("list", [])))
            if page >= response["pageCount"]:
                return plants

    def _get_plant_data(self, endpoint, plants: dict[str, Plant], parameters=None, batch_size=100) -> list[dict]:
        """
        Batches calls to by groups of 'batch_size' plants. 100 is the usual limit for FusionSolar.

        Args:
            endpoint: API endpoint
            plants: dictionary code->Plant for the plants
            parameters (Optional): dictionary of request parameters
            batch_size (Optional): maximum size for the batch request

        Returns:
            list[dict]: data per plant, not converted to class
        """
        data = []
        parameters = parameters or {}
        unique_plants = list(plants.values())
        for batch in batched(unique_plants, batch_size):
            parameters["stationCodes"] = ",".join([plant.code for plant in batch])
            response = self.session.post(endpoint=endpoint, parameters=parameters)
            data = data + response.get("data", [])
        return data

    def get_plant_realtime_data(self, plants: dict[str, Plant]) -> list[PlantRealTimeData]:
        """
        Get real-time plant data by plant ID set.
        Implementation wraps a call to the Plant Data Interfaces, see 7.1.4.1
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        """
        logger.debug("Get realtime plant data")
        return PlantRealTimeData.from_list(self._get_plant_data("getStationRealKpi", plants, batch_size=100), plants)

    def _get_plant_timed_data(self, endpoint, plants: list, date: datetime.datetime) -> list:
        """
        Internal function for getting plant data by plants ID set and date.
        """
        # Time is in milliseconds
        parameters = {"collectTime": to_timestamp(date)}
        return self._get_plant_data(endpoint, plants, parameters)

    def get_plant_hourly_data(self, plants: list, date: datetime.datetime) -> list[PlantHourlyData]:
        """
        Get hourly plant data by plants ID set.

        Args:
            plants: dict of code->Plant
            date: datetime to query hour data inside this specific day

        returns:
            list of PlantHourlyData
        """
        logger.debug("Get station hour data")
        return PlantHourlyData.from_list(
            self._get_plant_timed_data("getKpiStationHour", plants=plants, date=date), plants
        )

    def get_plant_daily_data(self, plants: list, date: datetime.datetime) -> list[PlantDailyData]:
        """
        Get daily plant data by plants ID set.

        Args:
            plants: dict of code->Plant
            date: datetime to query hour data inside this specific day

        returns:
            list of PlantDailyData
        """
        logger.debug("Get station daily data")
        return PlantDailyData.from_list(
            self._get_plant_timed_data("getKpiStationDay", plants=plants, date=date), plants
        )

    def get_plant_monthly_data(self, plants: list, date: datetime.datetime) -> list[PlantMonthlyData]:
        """
        Get monthly plant data by plants ID set.
        Implementation wraps a call to the Plant Hourly Data Interfaces, see 7.1.4.4
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        """
        logger.debug("Get station monthly data")
        return PlantMonthlyData.from_list(
            self._get_plant_timed_data("getKpiStationMonth", plants=plants, date=date), plants
        )

    def get_plant_yearly_data(self, plants: list, date: datetime.datetime) -> list:
        """
        Get yearly plant data by plants ID set.
        Implementation wraps a call to the Plant Hourly Data Interfaces, see 7.1.4.5
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        """
        logger.debug("Get station yearly data")
        return PlantYearlyData.from_list(
            self._get_plant_timed_data("getKpiStationYear", plants=plants, date=date), plants
        )

    def get_device_list(self, plants: dict[str, Plant]) -> dict[str, Device]:
        """
        Get device list per plant
        Implementation wraps a call to the Device List API

        Args:
            plants: dict code->Plant
            batch_size: maximum batch size for grouping the requests per Plant.
        """
        data = {}
        batch_size = 100
        unique_plants = list(plants.values())
        for batch in [unique_plants[i : i + batch_size] for i in range(0, len(unique_plants), batch_size)]:
            parameters = {"stationCodes": ",".join([plant.code for plant in batch])}
            logger.debug(f"Get device list for stations {parameters['stationCodes']}")
            response = self.session.post(endpoint="getDevList", parameters=parameters)
            data.update(Device.from_list(response.get("data", []), plants))
        return data

    def _get_device_data(
        self, endpoint, devices: dict[str, Device], parameters=None, batch_size=100, device_filter=None
    ) -> list[dict]:
        """
        Return realtime data for a dictionary of devices

        Args:
            endpoint: endpoint for the request
            devices: dict dev_id->Device of devices
            parameters: optional dict of parameters for the request
            batch_size: maximum batch size
            device_filter: list of devices supporting data request

        Returns:
            list: response
        """
        data = []
        parameters = parameters or {}
        device_filter = device_filter or []
        sorted_devices = sorted(devices.values(), key=lambda d: d.dev_type_id)
        for dev_type_id, devices_group in itertools.groupby(sorted_devices, key=lambda d: d.dev_type_id):
            device_name = Device.DEVICE_TYPES.get(dev_type_id, Device.UNKNOWN_DEVICE)
            if dev_type_id not in device_filter:
                logger.debug(f"Ignoring device data request for {dev_type_id}: {device_name}")
            else:
                logger.debug(f"Requesting device data for {dev_type_id}: {device_name}")
                for batch in batched(devices_group, batch_size):
                    parameters["devIds"] = ",".join([str(d.id) for d in batch])
                    parameters["devTypeId"] = dev_type_id
                    response = self.session.post(endpoint=endpoint, parameters=parameters)
                    data = data + response.get("data", [])
        return data

    def get_device_realtime_data(self, devices: dict[str, Device]) -> list[DeviceRTData]:
        """
        Get realtime data for devices

        Args:
            devices: dict dev_id->Device of devices
            batch_size: Maximum batch size

        Returns:
            list of DeviceRTData
        """
        return DeviceRTData.from_list(
            self._get_device_data(
                "getDevRealKpi",
                devices,
                batch_size=100,
                device_filter=DeviceRTData.supported_devices(),
            ),
            devices,
        )

    def get_device_history_data(
        self,
        devices: dict[str, Device],
        begin: datetime.datetime,
        end: datetime.datetime
    ) -> list[DeviceRTData]:
        """
        Get history of realtime data for devices (Max 3 days), from start to end

        Args:
            devices: dict dev_id->Device of devices
            begin: datetime of collection start
            end: datetime of collection end
            batch_size: Maximum batch size

        Returns:
            list of DeviceRTData
        """
        assert end > begin, "End time needs to be after begin time"
        parameters = {
            "startTime": to_timestamp(begin),
            "endTime": to_timestamp(end)
        }
        return DeviceRTData.from_list(
            self._get_device_data(
                "getDevHistoryKpi",
                devices,
                parameters=parameters,
                batch_size=10,
                device_filter=DeviceRTData.supported_devices()
            ),
            devices
        )

    def get_device_daily_data(self, devices: dict[str, Device], date: datetime.datetime) -> list[DeviceRptData]:
        """
        Get daily data for devices at selected date

        Args:
            devices: dict dev_id->Device of devices
            date: datetime for collection

        Returns:
            list of DeviceRptData
        """
        parameters = {
            "collectTime": to_timestamp(date)
        }
        return DeviceRptData.from_list(
            self._get_device_data(
                "getDevKpiDay",
                devices,
                parameters=parameters,
                batch_size=100,
                device_filter=DeviceRptData.supported_devices()
            ),
            devices
        )

    def get_device_monthly_data(self, devices: dict[str, Device], date: datetime.datetime) -> list[DeviceRptData]:
        """
        Get montly data for devices at selected date

        Args:
            devices: dict dev_id->Device of devices
            date: datetime for collection

        Returns:
            list of DeviceRptData
        """
        parameters = {
            "collectTime": to_timestamp(date)
        }
        return DeviceRptData.from_list(
            self._get_device_data(
                "getDevKpiMonth",
                devices,
                parameters=parameters,
                batch_size=100,
                device_filter=DeviceRptData.supported_devices()
            ),
            devices
        )

    def get_device_yearly_data(self, devices: dict[str, Device], date: datetime.datetime) -> list[DeviceRptData]:
        """
        Get yearly data for devices at selected date

        Args:
            devices: dict dev_id->Device of devices
            date: datetime for collection

        Returns:
            list of DeviceRptData
        """
        parameters = {
            "collectTime": to_timestamp(date)
        }
        return DeviceRptData.from_list(
            self._get_device_data(
                "getDevKpiYear",
                devices,
                parameters=parameters,
                batch_size=100,
                device_filter=DeviceRptData.supported_devices()
            ),
            devices
        )


    def get_alarms_list(
        self, plants: dict[str, Plant], begin: datetime.datetime, end: datetime.datetime, language="en_US"
    ) -> list:
        """Get the current (active) alarm information of a device.
        Implementation wraps a call to the Device Alarm Interface.
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        Language can be any of zh_CN (Chinese), en_US (English), ja_JP (Japanese), it_IT (Italian),
        nl_NL (Dutch), pt_BR (Portuguese), de_DE (German), fr_FR (French), es_ES (Spanish), pl_PL (Polish)
        """
        parameters = {"language": language, "beginTime": to_timestamp(begin), "endTime": to_timestamp(end)}
        return AlarmData.from_list(self._get_plant_data("getAlarmList", plants=plants, parameters=parameters), plants)


class ClientSession(Client):
    def __init__(self, user: str, password: str):
        return super().__init__(session=session.Session(user=user, password=password))

    def __enter__(self):
        self.session.__enter__()
        return super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.__exit__(exc_type, exc_val, exc_tb)
        return super().__exit__(exc_type, exc_val, exc_tb)
