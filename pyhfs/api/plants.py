import datetime

from .devices import Device
from .util import data_prop


class Plant:
    """
    API class for "Plant List API" response
    """

    def __init__(self, data: dict):
        """
        Initialize from JSON response

        Args:
          data: response from the API for a Plant or from saved
                data.
        """
        self._data = data
        self._devices: dict[str, Device] = {}

        # Only present if loading from a file
        if "devices" in data:
            for dev_data in data["devices"]:
                # Calls self.add_device
                Device(dev_data, {self.code: self})

    @staticmethod
    def from_list(data: list) -> dict[str, "Plant"]:
        """
        Create a list of plants from a response

        Args:
          data: list of plants from Api

        Returns:
          dict: dictionary plant code -> Plant
        """
        plants = [Plant(item) for item in data]
        return {plant.code: plant for plant in plants}

    def __str__(self) -> str:
        return f"{self.name} ({self.code}) - {self.capacity} kWp"

    def add_device(self, device: Device) -> None:
        """
        Add a device to this station if it does not already exist

        args:
            device: Device to add
        """
        self._devices[device.name] = device

    code = data_prop("plantCode", "Plant code (str)")
    name = data_prop("plantName", "Plant name (str)")
    address = data_prop("plantAddress", "Detailed address of the plant (str)")
    longitude = data_prop("longitude", "Plant longitude (float)")
    latitude = data_prop("latitude", "Plant latitude (float)")
    capacity = data_prop("capacity", "Total capacity in kWp (float)")
    contact_person = data_prop("contactPerson", "Plant contact (str)")
    contact_method = data_prop(
        "contactMethod",
        "Contact information of the plant contact, such as the mobile phone number or email address (str)",
    )
    grid_connection_date = data_prop(
        "gridConnectionDate",
        "Grid connection time of the plant, including the time zone (datetime)",
        conv=datetime.datetime.fromisoformat,
    )

    @property
    def devices(self) -> list[Device]:
        """
        List of devices linked to this station once it has been populated
        """
        return list(self._devices.values())

    @property
    def data(self) -> dict:
        """
        Return original data to be saved. If devices are present, it includes
        data from the devices, so different from the original request.
        """
        self._data["devices"] = [device.data for device in self.devices]
        return self._data
