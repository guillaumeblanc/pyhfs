from .plants import Plant
from .util import data_prop, data_item_prop, data_item_prop_opt, from_timestamp, ffmt


class PlantRealTimeData:
    """
    API class for "Real-Time Plant Data API"
    """

    REAL_HEALTH_STATE = {
        1: "disconnected",
        2: "faulty",
        3: "healthy",
    }

    UNKNOWN_HEALT_STATE = "Unknown"

    def __init__(self, data: dict, plants: dict[str, Plant]):
        """
        Initialize from JSON response
        """
        self._data = data
        if "plant" in self._data:
            # Reload from saved JSON file
            self._plant = Plant(self._data["plant"])

        else:
            if self.station_code not in plants:
                raise ValueError(f"Plant/Station {self.station_code} not found for plant data {self}")
            self._plant = plants[self.station_code]

    @staticmethod
    def from_list(data: list, plants: dict[str, "Plant"]) -> list["PlantRealTimeData"]:
        """
        Parse real time data from a response

        Args:
          data: consumption data
          plants: dictionary of plants

        Returns:
          list: list of realtime data
        """
        return [PlantRealTimeData(item, plants) for item in data]

    def __str__(self) -> str:
        return f"""
Station {self.plant} {self.health_state}
  Power      day: {ffmt(self.day_power)} kWh  month: {ffmt(self.month_power)} kWh year: {ffmt(self.total_power)}
  Income     day: {ffmt(self.day_income)}      total: {ffmt(self.total_income)}
        """

    station_code = data_prop("stationCode", "Station/plant code (str)")
    day_power = data_item_prop("day_power", "Yield today in kWh (float)", conv=float)
    month_power = data_item_prop("month_power", "Yield this month in kWh (float)", conv=float)
    total_power = data_item_prop("total_power", "Total yield in kWh (float)", conv=float)
    day_income = data_item_prop(
        "day_income", "Revenue today, in the currency specified in the management system (float)", conv=float
    )
    total_income = data_item_prop(
        "total_income", "Total revenue, in the currency specified in the management system (float)", conv=float
    )
    health_state_id = data_item_prop("real_health_state", "Plant health status as integer (int)", conv=int)

    @property
    def plant(self) -> Plant:
        """
        Plant related to this data
        """
        return self._plant

    @property
    def health_state(self) -> str:
        """
        Plant health status as string
        """
        return PlantRealTimeData.REAL_HEALTH_STATE.get(self.health_state_id, PlantRealTimeData.UNKNOWN_HEALT_STATE)

    @property
    def data(self) -> dict:
        """
        Return raw data with "plant" as an additional field
        """
        self._data["plant"] = self._plant.data
        return self._data


class PlantHourlyData:
    """
    API class for "Hourly Plant Data API"
    """

    def __init__(self, data: dict, plants: dict[str, Plant]):
        """
        Initialize from JSON response
        """
        self._data = data
        if "plant" in self._data:
            # Reload from saved JSON file
            self._plant = Plant(self._data["plant"])

        else:
            if self.station_code not in plants:
                raise ValueError(f"Plant/Station {self.station_code} not found for plant data {self}")
            self._plant = plants[self.station_code]

    @staticmethod
    def from_list(data: list, plants: dict[str, "Plant"]) -> list["PlantHourlyData"]:
        """
        Parse hourly data from a response

        Args:
          data: consumption data
          plants: dictionary of plants

        Returns:
          list: list of hourly data inside the day
        """
        return [PlantHourlyData(item, plants) for item in data]

    def __str__(self) -> str:
        return f"""
{self.plant.name} - {self.collect_time}
Inverter power: {ffmt(self.inverter_power)} kWh   On-Grid power: {ffmt(self.ongrid_power)} kWh
        """

    collect_time = data_prop("collectTime", "Collect time in milliseconds", conv=from_timestamp)
    station_code = data_prop("stationCode", "Plant ID")

    @property
    def plant(self) -> Plant:
        """
        Related Plant/Station
        """
        return self._plant

    radiation_intensity = data_item_prop("radiation_intensity", "Global irradiation in kWh/m² (float)")
    theory_power = data_item_prop("theory_power", "Theoretical yield in kWh (float)")
    inverter_power = data_item_prop("inverter_power", "Inverter yield in kWh (float)")
    ongrid_power = data_item_prop("ongrid_power", "Feed-in energy in kWh (float)")
    power_profit = data_item_prop("power_profit", "Revenue in currency specified in the management system (float)")

    # Not documented but can be present
    charge_cap = data_item_prop_opt("chargeCap", 0, "Charged energy in kWh (float)")
    discharge_cap = data_item_prop_opt("dischargeCap", 0, "Discharged energy in kWh (float)")
    pv_yield = data_item_prop_opt("PVYield", 0, "PV energy in kWh (float)")
    inverted_yield = data_item_prop_opt("inverterYield", 0, "Inverter energy in kWh (float)")
    self_provide = data_item_prop_opt("selfProvide", 0, "Energy consumed from PV in kWh (float)")

    @property
    def data(self) -> dict:
        """
        Raw data
        """
        return self._data


class PlantDailyData:
    """
    API class for "Daily Plant Data API"
    """

    def __init__(self, data: dict, plants: dict[str, Plant]):
        """
        Initialize from JSON response
        """
        self._data = data
        if "plant" in self._data:
            # Reload from saved JSON file
            self._plant = Plant(self._data["plant"])

        else:
            if self.station_code not in plants:
                raise ValueError(f"Plant/Station {self.station_code} not found for plant data {self}")
            self._plant = plants[self.station_code]

    @staticmethod
    def from_list(data: list, plants: dict[str, "Plant"]) -> list["PlantDailyData"]:
        """
        Parse daily data from a response

        Args:
          data: consumption data
          plants: dictionary of plants

        Returns:
          list: list of daily data inside the month
        """
        return [PlantDailyData(item, plants) for item in data]

    def __str__(self) -> str:
        return f"""
{self.plant.name}: {self.installed_capacity} kWp - {self.collect_time}
Radiation intensity: {ffmt(self.radiation_intensity)} kWh/m²   Theory power: {ffmt(self.theory_power)} kWh ({self.performance_ratio}%)
Inverter power:      {ffmt(self.inverter_power)} kWh   On-Grid power: {ffmt(self.ongrid_power)} kWh
Buy power:           {ffmt(self.buy_power)} kWh  Use power: {ffmt(self.self_use_power)} kWh  Self provide: {ffmt(self.self_provide)} kWh
        """

    collect_time = data_prop("collectTime", "Collect time in milliseconds", conv=from_timestamp)
    station_code = data_prop("stationCode", "Plant ID")

    @property
    def plant(self) -> Plant:
        """
        Related Plant/Station
        """
        return self._plant

    installed_capacity = data_item_prop("installed_capacity", "Installed capacity in kWp (float)")
    inverter_power = data_item_prop("inverter_power", "Inverter yield in kWh (float)")
    perpower_ratio = data_item_prop("perpower_ratio", "Specific energy in kWh/kWp (float)")
    reduction_total_co2 = data_item_prop("reduction_total_co2", "CO2 emission reduction in Ton (float)")
    reduction_total_coal = data_item_prop("reduction_total_coal", "Standard coal saved in Ton (float)")
    buy_power = data_item_prop_opt("buyPower", 0, "Energy from grid in kWh (float)")
    charge_cap = data_item_prop_opt("chargeCap", 0, "Charged energy in kWh (float)")
    discharge_cap = data_item_prop_opt("dischargeCap", 0, "Discharged energy in kWh (float)")
    self_use_power = data_item_prop_opt("selfUsePower", 0, "Consumed PV energy in kWh (float)")
    self_provide = data_item_prop_opt("selfProvide", 0, "Energy consumed from PV in kWh (float)")

    # Documented but absent
    radiation_intensity = data_item_prop_opt("radiation_intensity", 0, "Global irradiation in kWh/m² (float)")
    theory_power = data_item_prop_opt("theory_power", 0, "Theoretical yield in kWh (float)")
    performance_ratio = data_item_prop_opt("performance_ratio", 0, "Performance ratio in % (float)")
    ongrid_power = data_item_prop_opt("ongrid_power", 0, "Feed-in energy in kWh (float)")
    power_profit = data_item_prop_opt("power_profit", 0, "Revenue in currency specified in the management system (float)")

    # Not documented but present
    pv_yield = data_item_prop_opt("pv_yield", 0, "PV Yield in kWh (float)")

    @property
    def data(self) -> dict:
        """
        Raw data
        """
        return self._data


class PlantMonthlyData(PlantDailyData):
    """
    API class for "Monthly Plant Data API"
    """

    @staticmethod
    def from_list(data: list, plants: dict[str, "Plant"]) -> list["PlantMonthlyData"]:
        """
        Parse daily data from a response

        Args:
          data: consumption data
          plants: dictionary of plants

        Returns:
          list: list of montly data inside the month
        """
        return [PlantMonthlyData(item, plants) for item in data]


class PlantYearlyData(PlantDailyData):
    """
    API class for "Yearly Plant Data API"
    """

    @staticmethod
    def from_list(data: list, plants: dict[str, "Plant"]) -> list["PlantYearlyData"]:
        """
        Parse daily data from a response

        Args:
          data: consumption data
          plants: dictionary of plants

        Returns:
          list: list of montly data inside the month
        """
        return [PlantYearlyData(item, plants) for item in data]
