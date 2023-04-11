import logging
import os
import itertools
import datetime

from . import session
from . import exception

# Based on documentation iMaster NetEco V600R023C00 Northbound Interface Reference-V6(SmartPVMS)
# https://support.huawei.com/enterprise/en/doc/EDOC1100261860/


class Client:
    def __init__(self, session: session.Session):
        self.session = session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @staticmethod
    def from_timestamp(timestamp: int):
        '''
        Converts fusion solar timestamp to datetime.
        Even though documentation says time is in plant time zone, it's actually utc/gmt.
        '''
        return datetime.datetime.fromtimestamp(timestamp / 1000., datetime.timezone.utc)

    @staticmethod
    def to_timestamp(time: datetime.datetime):
        '''Converts datetime to fusion solar timestamp.'''
        return int(time.timestamp() * 1000)

    def get_plant_list(self) -> list:
        '''
        Get basic plants information.
        Implementation wraps a call to the Plant List Interface, see documentation 7.1.3
        This implementation will query all available pages
        '''
        plants = []
        for page in itertools.count(start=1):
            param = {'pageNo': page, 'pageSize': 100}
            response = self.session.post(
                endpoint='stations', parameters=param)['data']
            plants = plants + response.get('list', [])
            if page >= response['pageCount']:
                return plants

    def _get_plant_data(self, endpoint, plants: list, parameters={}, batch_size=100) -> list:
        '''
        Batches calls to by groups of 'batch_size' plants. 100 is the usual limit for FusionSolar.
        '''
        data = []
        unique_plants = list(dict.fromkeys(plants))  # Remove duplicates
        for batch in [unique_plants[i:i + batch_size] for i in range(0, len(unique_plants), batch_size)]:
            parameters['stationCodes'] = ','.join(batch)
            response = self.session.post(
                endpoint=endpoint, parameters=parameters)
            data = data + response.get('data', [])
        return data

    def get_plant_realtime_data(self, plants: list) -> list:
        '''
        Get real-time plant data by plant ID set.
        Implementation wraps a call to the Plant Data Interfaces, see 7.1.4.1
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        '''
        return self._get_plant_data('getStationRealKpi', plants)

    def _get_plant_timed_data(self, endpoint, plants: list, date: datetime.datetime) -> list:
        '''
        Internal function for getting plant data by plants ID set and date.
        '''
        # Time is in milliseconds
        parameters = {'collectTime': self.to_timestamp(date)}
        return self._get_plant_data(endpoint, plants, parameters)

    def get_plant_hourly_data(self, plants: list, date: datetime.datetime) -> list:
        '''
        Get hourly plant data by plants ID set.
        Implementation wraps a call to the Plant Hourly Data Interfaces, see 7.1.4.2
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        '''
        return self._get_plant_timed_data('getKpiStationHour', plants=plants, date=date)

    def get_plant_daily_data(self, plants: list, date: datetime.datetime) -> list:
        '''
        Get daily plant data by plants ID set.
        Implementation wraps a call to the Plant Hourly Data Interfaces, see 7.1.4.3
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        '''
        return self._get_plant_timed_data('getKpiStationDay', plants=plants, date=date)

    def get_plant_monthly_data(self, plants: list, date: datetime.datetime) -> list:
        '''
        Get monthly plant data by plants ID set.
        Implementation wraps a call to the Plant Hourly Data Interfaces, see 7.1.4.4
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        '''
        return self._get_plant_timed_data('getKpiStationMonth', plants=plants, date=date)

    def get_plant_yearly_data(self, plants: list, date: datetime.datetime) -> list:
        '''
        Get yearly plant data by plants ID set.
        Implementation wraps a call to the Plant Hourly Data Interfaces, see 7.1.4.5
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        '''
        return self._get_plant_timed_data('getKpiStationYear', plants=plants, date=date)

    def get_alarms_list(self, plants: list, begin: datetime.datetime, end: datetime.datetime, language='en_US') -> list:
        '''Get the current (active) alarm information of a device.
        Implementation wraps a call to the Device Alarm Interface.
        Plant IDs can be obtained by querying get_plant_list, they are stationCode parameters.
        Language can be any of zh_CN (Chinese), en_US (English), ja_JP (Japanese), it_IT (Italian), 
        nl_NL (Dutch), pt_BR (Portuguese), de_DE (German), fr_FR: French), es_ES (Spanish), pl_PL (Polish)
        '''
        parameters = {'language': language,
                      'beginTime': self.to_timestamp(begin),
                      'endTime': self.to_timestamp(end)}
        return self._get_plant_data('getAlarmList', plants=plants, parameters=parameters)


class ClientSession(Client):
    def __init__(self, user: str, password: str):
        return super().__init__(session=session.Session(user=user, password=password))

    def __enter__(self):
        self.session.__enter__()
        return super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.__exit__(exc_type, exc_val, exc_tb)
        return super().__exit__(exc_type, exc_val, exc_tb)
