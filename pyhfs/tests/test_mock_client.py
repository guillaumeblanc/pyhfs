import unittest
import datetime
import json
from io import StringIO

from pyhfs.tests.mock_session import MockSession
from pyhfs.api.plants import Plant
from pyhfs.api.devices import Device
from pyhfs.api.device_rt_data import DeviceRTDataSInverter, DeviceRTDataRInverter, DeviceRTDataRBattery, DeviceRTDataPSensor
from pyhfs.api.device_rpt_data import DeviceRptDataRBattery, DeviceRptDataRInverter, DeviceRptDataSInverter, DeviceRptDataCI
from pyhfs.api.alarm_data import AlarmData
from pyhfs.api.plant_data import PlantHourlyData, PlantDailyData, PlantMonthlyData, PlantYearlyData
import pyhfs


class TestMockClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = pyhfs.Client(MockSession())

    def test_plan_list(self):
        # All plants
        plants_dict = self.client.get_plant_list()
        plants = list(plants_dict.values())

        self.assertEqual([plant.name for plant in plants], ["NMplant1", "plant2"])
        self.assertEqual(plants[0].code, "NE=12345678")
        self.assertEqual(plants[0].address, None)
        self.assertEqual(plants[0].longitude, 3.1415)
        self.assertEqual(plants[0].latitude, None)
        self.assertEqual(plants[0].capacity, 146.5)
        self.assertEqual(plants[0].contact_person, "")
        self.assertEqual(plants[0].contact_method, "")

        self.assertEqual(
            plants[0].grid_connection_date.astimezone(datetime.timezone.utc),
            datetime.datetime(
                2022,
                11,
                21,
                16 - 8,
                23,
                00,
                tzinfo=datetime.timezone(datetime.timedelta(hours=0)),
            ),
        )

    def test_devices_list(self):
        plants_dict = self.client.get_plant_list()
        devices_dict = self.client.get_device_list(plants_dict)

        plants = list(plants_dict.values())
        devices = list(devices_dict.values())

        self.assertEqual([device.name for device in devices], ["5fbfk4", "6fbfk11"])
        self.assertEqual(devices[0].id, -214543629611879)
        self.assertEqual(devices[0].unique_id, "NE=45112560")
        self.assertEqual(devices[0].plant, plants[0])
        self.assertEqual(devices[0].station_code, "NE=12345678")
        self.assertEqual(devices[0].serial_number, "5fbfk4")
        self.assertEqual(devices[0].dev_type_id, 1)
        self.assertEqual(devices[0].dev_type, "Inverter")
        self.assertEqual(devices[0].software_version, "V100R001PC666")
        self.assertEqual(devices[0].inverter_type, "SUN2000-17KTL")
        self.assertEqual(devices[0].optimizers, None)
        self.assertEqual(devices[0].longitude, None)
        self.assertEqual(devices[0].latitude, None)

        # List of plants should be modified to contain devices
        self.assertEqual(plants[0].devices, devices)
        self.assertEqual(plants[1].devices, [])

    def test_save_devices(self):
        plants_dict = self.client.get_plant_list()
        self.client.get_device_list(plants_dict)

        plants = list(plants_dict.values())

        # Save plants and devices
        f = StringIO()
        data = [plant.data for plant in plants]
        json.dump(data, f)

        # Reload plants and devices
        f.seek(0)
        data = json.load(f)

        plants_dict = Plant.from_list(data)
        plants = list(plants_dict.values())

        self.assertEqual([plant.name for plant in plants], ["NMplant1", "plant2"])
        self.assertEqual([device.name for device in plants[0].devices], ["5fbfk4", "6fbfk11"])
        self.assertEqual([device.name for device in plants[1].devices], [])

    def test_plant_realtime_data(self):
        plants = self.client.get_plant_list()

        data = self.client.get_plant_realtime_data(plants)

        self.assertEqual([item.plant.name for item in data], ["NMplant1", "plant2"])

        self.assertEqual(data[0].day_power, 17543)
        self.assertEqual(data[0].month_power, 4345732.000)
        self.assertEqual(data[0].total_power, 345732.000)
        self.assertEqual(data[0].day_income, 45.67)
        self.assertEqual(data[0].total_income, 2088.000)
        self.assertEqual(data[0].health_state_id, 3)
        self.assertEqual(data[0].health_state, "healthy")

    def test_device_realtime_data(self):
        plants = self.client.get_plant_list()
        devices = self.client.get_device_list(plants)

        data = self.client.get_device_realtime_data(devices)

        self.assertEqual(len(data), 2)

        self.assertIsInstance(data[0], DeviceRTDataSInverter)
        self.assertEqual(data[0].inverter_state, "Standby: initializing")

    def test_device_realtime_1(self):
        plants = self.client.get_plant_list()
        devices = self.client.get_device_list(plants)
        data = self.client.get_device_realtime_data(devices)

        self.assertIsInstance(data[0], DeviceRTDataSInverter)

        d: DeviceRTDataSInverter = data[0]
        self.assertEqual(d.run_state, "Disconnected")
        self.assertEqual(d.inverter_state, "Standby: initializing")
        self.assertEqual(d.device, devices[-214543629611879])
        self.assertEqual(d.diff_voltage, {"AB": 0, "BC": 1, "CA": 2})
        self.assertEqual(d.voltage, {"A": 0, "B": 1, "C": 2})
        self.assertEqual(d.current, {"A": 3, "B": 4, "C": 5})
        self.assertEqual(d.efficiency, 10)
        self.assertEqual(d.temperature, 10)
        self.assertEqual(d.power_factor, 0)
        self.assertEqual(d.elec_freq, 10)
        self.assertEqual(d.active_power, 10)
        self.assertEqual(d.reactive_power, 10)
        self.assertEqual(d.day_cap, 10)
        self.assertEqual(d.mppt_power, 10)
        self.assertEqual(d.pv_voltage, {i: i for i in range(1, 29)})
        self.assertEqual(d.pv_current, {i: i for i in range(1, 29)})
        self.assertEqual(d.total_cap, 10)
        self.assertEqual(d.open_time, datetime.datetime(2017, 8, 18, 10, 56, 37))
        self.assertEqual(d.mppt_total_cap, 10)
        self.assertEqual(d.mppt_cap, {i: i for i in range(1, 11)})

    def get_default_devices(self, name: str, type_id: int):
        plant = Plant({"plantCode": 123456})
        plants = {plant.code: plant}
        device = Device(
            {"stationCode": 123456, "id": 123456, "devName": name, "devTypeId": type_id, "softwareVersion": None},
            plants,
        )
        return {device.id: device}

    def test_device_realtime_38(self):
        devices = self.get_default_devices("Residential inverter", 38)
        self.client.session.post_suffix = "-38"
        data = self.client.get_device_realtime_data(devices)

        self.assertIsInstance(data[0], DeviceRTDataRInverter)

        d: DeviceRTDataRInverter = data[0]

        self.assertEqual(d.run_state, "Connected")
        self.assertEqual(d.inverter_state, "Grid-connected")
        self.assertEqual(d.device, devices[123456])
        self.assertEqual(d.diff_voltage, {"AB": 238.6, "BC": 0.0, "CA": 0.0})
        self.assertEqual(d.voltage, {"A": 118.4, "B": 0.0, "C": 0.0})
        self.assertEqual(d.current, {"A": 2.244, "B": 0.0, "C": 0.0})
        self.assertEqual(d.efficiency, 100.0)
        self.assertEqual(d.temperature, 41.9)
        self.assertEqual(d.power_factor, 1.0)
        self.assertEqual(d.elec_freq, 49.99)
        self.assertEqual(d.active_power, 0.518)
        self.assertEqual(d.reactive_power, 0.0)
        self.assertEqual(d.day_cap, 10.13)
        self.assertEqual(d.mppt_power, 0.435)
        self.assertEqual(d.pv_voltage, {1: 453.5, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0})
        self.assertEqual(d.pv_current, {1: 1.02, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0})
        self.assertEqual(d.total_cap, 1482.36)
        self.assertEqual(d.open_time, datetime.datetime(2024, 7, 21, 6, 54, 40))
        self.assertEqual(d.mppt_total_cap, 10)
        self.assertEqual(d.mppt_cap, {1: 1569.24, 2: 0.0, 3: 0.0, 4: 0.0})

    def test_device_realtime_39(self):
        devices = self.get_default_devices("Battery", 39)
        self.client.session.post_suffix = "-39"
        data = self.client.get_device_realtime_data(devices)

        self.assertIsInstance(data[0], DeviceRTDataRBattery)

        d: DeviceRTDataRBattery = data[0]

        self.assertEqual(d.run_state, "Connected")
        self.assertEqual(d.battery_status, "running")
        self.assertEqual(d.max_charge_power, 2500.0)
        self.assertEqual(d.max_discharge_power, 2500.0)
        self.assertEqual(d.ch_discharge_power, -89.0)
        self.assertEqual(d.voltage, 453.0)
        self.assertEqual(d.soc, 86.0)
        self.assertEqual(d.soh, 0.0)
        self.assertEqual(d.charge_mode, "automatic charge/discharge")
        self.assertEqual(d.charge_cap, 5.41)
        self.assertEqual(d.discharge_cap, 2.94)

    def test_device_realtime_47(self):
        devices = self.get_default_devices("Power sensor", 47)
        self.client.session.post_suffix = "-47"
        data = self.client.get_device_realtime_data(devices)

        self.assertIsInstance(data[0], DeviceRTDataPSensor)

        d: DeviceRTDataPSensor = data[0]

        self.assertEqual(d.run_state, "Connected")
        self.assertEqual(d.meter_status, "Normal")
        self.assertEqual(d.voltage, 238.5)
        self.assertEqual(d.current, 1.04)
        self.assertEqual(d.active_power, 0.0)
        self.assertEqual(d.reactive_power, 296.0)
        self.assertEqual(d.power_factor, 0.0)
        self.assertEqual(d.grid_frequency, 49.99)
        self.assertEqual(d.active_cap, 650.65)
        self.assertEqual(d.reverse_active_cap, 296.8)
        self.assertEqual(d.diff_voltage, {"AB": None, "BC": None, "CA": None})
        self.assertEqual(d.voltage_phase, {"A": None, "B": None, "C": None})
        self.assertEqual(d.current_phase, {"A": None, "B": None, "C": None})
        self.assertEqual(d.active_power_phase, {"A": None, "B": None, "C": None})

    def test_alarm(self):
        plants = self.client.get_plant_list()
        self.client.get_device_list(plants)

        now = datetime.datetime.now()
        data = self.client.get_alarms_list(plants, now, now - datetime.timedelta(days=1))

        self.assertEqual(len(data), 2)

        self.assertIsInstance(data[0], AlarmData)
        d: AlarmData = data[0]

        self.assertEqual(d.plant, plants["NE=12345678"])
        self.assertEqual(d.device, d.plant.devices[0])

        self.assertEqual(d.station_code, "NE=12345678")
        self.assertEqual(d.name, "The device is abnormal.")
        self.assertEqual(d.dev_name, "5fbfk4")
        self.assertEqual(
            d.repair_suggestion,
            "Turn off the AC and DC switches, wait for 5 minutes, and then turn on the AC and DC switches. If the fault persists, contact your dealer or technical support.",
        )
        self.assertEqual(d.dev_sn, "5fbfk4")
        self.assertEqual(d.dev_type, "Inverter")
        self.assertEqual(d.cause, "An unrecoverable fault has occurred in the internal circuit of the device.")
        self.assertEqual(d.alarm_type, "exception alarm")
        self.assertEqual(d.raise_time, datetime.datetime(2022, 10, 31, 2, 31, 1))
        self.assertEqual(d.id, 2064)
        self.assertEqual(d.station_name, "NMplant1")
        self.assertEqual(d.level, "major")
        self.assertEqual(d.status, "not processed (active)")

    def test_plant_hourly_data(self):
        date = datetime.datetime(2024, 1, 1, 0, 0, 0)

        plants = self.client.get_plant_list()
        data = self.client.get_plant_hourly_data(plants, date)

        self.assertEqual(len(data), 8)
        self.assertIsInstance(data[0], PlantHourlyData)

        d: PlantHourlyData = data[0]

        self.assertEqual(d.station_code, "NE=12345678")
        self.assertEqual(d.plant, plants["NE=12345678"])
        self.assertEqual(d.radiation_intensity, 0.6968)
        self.assertEqual(d.theory_power, 17559.36)
        self.assertEqual(d.inverter_power, 18330)
        self.assertEqual(d.ongrid_power, 18330)
        self.assertEqual(d.power_profit, 34320)

        self.assertEqual(
            [d.collect_time for d in data],
            [
                datetime.datetime(2017, 8, 4, 18, 0),
                datetime.datetime(2017, 8, 4, 19, 0),
                datetime.datetime(2017, 8, 4, 21, 0),
                datetime.datetime(2017, 8, 4, 22, 0),
                datetime.datetime(2017, 8, 4, 23, 0),
                datetime.datetime(2017, 8, 5, 0, 0),
                datetime.datetime(2017, 8, 5, 1, 0),
                datetime.datetime(2017, 8, 5, 1, 0),
            ],
        )

    def test_plant_daily_data(self):
        date = datetime.datetime(2024, 1, 1, 0, 0, 0)

        plants = self.client.get_plant_list()
        data = self.client.get_plant_daily_data(plants, date)

        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], PlantDailyData)

        d: PlantDailyData = data[0]

        self.assertEqual(d.installed_capacity, 25200)
        self.assertEqual(d.radiation_intensity, 0.6968)
        self.assertEqual(d.theory_power, 17559.36)
        self.assertEqual(d.performance_ratio, 89)
        self.assertEqual(d.inverter_power, 18330)
        self.assertEqual(d.ongrid_power, 18330)
        self.assertEqual(d.power_profit, 34320)
        self.assertEqual(d.perpower_ratio, 0.727)
        self.assertEqual(d.reduction_total_co2, 18.275)
        self.assertEqual(d.reduction_total_coal, 7.332)
        self.assertEqual(d.buy_power, 0)
        self.assertEqual(d.charge_cap, 0)
        self.assertEqual(d.discharge_cap, 0)
        self.assertEqual(d.self_use_power, 0)
        self.assertEqual(d.self_provide, 0)

        self.assertEqual(
            [d.collect_time for d in data], [datetime.datetime(2017, 8, 3, 18, 0), datetime.datetime(2017, 8, 3, 18, 0)]
        )

    def test_plant_monthly_data(self):
        date = datetime.datetime(2024, 1, 1, 0, 0, 0)

        plants = self.client.get_plant_list()
        data = self.client.get_plant_monthly_data(plants, date)

        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], PlantMonthlyData)

        d: PlantMonthlyData = data[0]

        self.assertEqual(d.installed_capacity, 25200)
        self.assertEqual(d.radiation_intensity, 0.6968)
        self.assertEqual(d.theory_power, 17559.36)
        self.assertEqual(d.performance_ratio, 89)
        self.assertEqual(d.inverter_power, None)
        self.assertEqual(d.ongrid_power, 18330)
        self.assertEqual(d.power_profit, 34320)
        self.assertEqual(d.perpower_ratio, 0.727)
        self.assertEqual(d.reduction_total_co2, 18.275)
        self.assertEqual(d.reduction_total_coal, 7.332)
        self.assertEqual(d.buy_power, 0)
        self.assertEqual(d.charge_cap, 0)
        self.assertEqual(d.discharge_cap, 0)
        self.assertEqual(d.self_use_power, 0)
        self.assertEqual(d.self_provide, 0)

        self.assertEqual(
            [d.collect_time for d in data],
            [datetime.datetime(2017, 7, 31, 18, 0), datetime.datetime(2017, 7, 31, 18, 0)],
        )

    def test_plant_yearly_data(self):
        date = datetime.datetime(2024, 1, 1, 0, 0, 0)

        plants = self.client.get_plant_list()
        data = self.client.get_plant_yearly_data(plants, date)

        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], PlantYearlyData)

        d: PlantYearlyData = data[0]

        self.assertEqual(d.installed_capacity, 25200)
        self.assertEqual(d.radiation_intensity, 0.6968)
        self.assertEqual(d.theory_power, 17559.36)
        self.assertEqual(d.performance_ratio, 89)
        self.assertEqual(d.inverter_power, None)
        self.assertEqual(d.ongrid_power, 18330)
        self.assertEqual(d.power_profit, 34320)
        self.assertEqual(d.perpower_ratio, 0.727)
        self.assertEqual(d.reduction_total_co2, 18.275)
        self.assertEqual(d.reduction_total_coal, 7.332)
        self.assertEqual(d.buy_power, 0)
        self.assertEqual(d.charge_cap, 0)
        self.assertEqual(d.discharge_cap, 0)
        self.assertEqual(d.self_use_power, 0)
        self.assertEqual(d.self_provide, 0)

        self.assertEqual(
            [d.collect_time for d in data],
            [datetime.datetime(2016, 12, 31, 17, 0), datetime.datetime(2016, 12, 31, 17, 0)],
        )

    def test_device_daily_data(self):
        date = datetime.datetime(2024, 1, 1, 0, 0, 0)

        plants = self.client.get_plant_list()
        devices = self.client.get_device_list(plants)
        data = self.client.get_device_daily_data(devices, date)

        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], DeviceRptDataSInverter)

        d: DeviceRptDataSInverter = data[0]

        self.assertEqual(d.installed_capacity, 30.24)
        self.assertEqual(d.product_power, 300)
        self.assertEqual(d.perpower_ratio, 9.921)

        self.assertEqual(
            [d.collect_time for d in data],
            [datetime.datetime(2017, 8, 3, 18, 0), datetime.datetime(2017, 8, 3, 18, 0)],
        )

    def test_device_daily_data_38(self):
        devices = self.get_default_devices("Residential inverter", 38)
        self.client.session.post_suffix = "-38"
        data = self.client.get_device_daily_data(devices, datetime.datetime.now())

        self.assertIsInstance(data[0], DeviceRptDataRInverter)

        d: DeviceRptDataRInverter = data[0]

        self.assertEqual(d.product_power, 15.970000000000027)
        self.assertEqual(d.perpower_ratio, 2.661666666666671)
        self.assertEqual(d.installed_capacity, 6.0)

        self.assertEqual(
            [d.collect_time for d in data],
            [
                datetime.datetime(2024, 7, 1, 1, 0),
                datetime.datetime(2024, 7, 2, 1, 0),
                datetime.datetime(2024, 7, 3, 1, 0),
                datetime.datetime(2024, 7, 4, 1, 0)
            ]
        )

    def test_device_daily_data_39(self):
        devices = self.get_default_devices("Residential battery", 39)
        self.client.session.post_suffix = "-39"
        data = self.client.get_device_daily_data(devices, datetime.datetime.now())

        self.assertIsInstance(data[0], DeviceRptDataRBattery)

        d: DeviceRptDataRBattery = data[0]

        self.assertEqual(d.charge_cap, 6.21)
        self.assertEqual(d.discharge_cap, 6.07)
        self.assertEqual(d.charge_time, 10.166666666666666)
        self.assertEqual(d.discharge_time, 5.5)

        self.assertEqual(
            [d.collect_time for d in data],
            [
                datetime.datetime(2024, 7, 1, 1, 0),
                datetime.datetime(2024, 7, 2, 1, 0),
                datetime.datetime(2024, 7, 3, 1, 0),
                datetime.datetime(2024, 7, 4, 1, 0)
            ]
        )

    def test_device_monthly_data(self):
        date = datetime.datetime(2024, 1, 1, 0, 0, 0)

        plants = self.client.get_plant_list()
        devices = self.client.get_device_list(plants)
        data = self.client.get_device_monthly_data(devices, date)

        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], DeviceRptDataSInverter)

        d: DeviceRptDataSInverter = data[0]

        self.assertEqual(d.installed_capacity, 30.24)
        self.assertEqual(d.product_power, 300)
        self.assertEqual(d.perpower_ratio, None)

        self.assertEqual(
            [d.collect_time for d in data],
            [datetime.datetime(2017, 7, 31, 18, 0), datetime.datetime(2017, 7, 31, 18, 33, 20)],
        )

    def test_device_yearly_data(self):
        date = datetime.datetime(2024, 1, 1, 0, 0, 0)

        plants = self.client.get_plant_list()
        devices = self.client.get_device_list(plants)
        data = self.client.get_device_yearly_data(devices, date)

        self.assertEqual(len(data), 1)
        self.assertIsInstance(data[0], DeviceRptDataSInverter)

        d: DeviceRptDataSInverter = data[0]

        self.assertEqual(d.installed_capacity, 30.24)
        self.assertEqual(d.product_power, 300)
        self.assertEqual(d.perpower_ratio, None)

        self.assertEqual(
            [d.collect_time for d in data],
            [datetime.datetime(2017, 7, 31, 18, 0)],
        )


if __name__ == "__main__":
    unittest.main()
