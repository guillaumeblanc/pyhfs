#!/usr/bin/env python3
import pyhfs
import os
import logging
from datetime import datetime, timezone, timedelta
import json
import argparse
from pathlib import Path


def get_devices(client: pyhfs.Client) -> dict[str, pyhfs.Plant]:
    """
    Get dictionary of plants and devices per plant

    Args:
        user: Username
        password: Password
    """
    plants = client.get_plant_list()
    client.get_device_list(plants)

    return plants


def plant_data(client: pyhfs.Client, plants: dict[str, pyhfs.Plant], args: argparse.Namespace):
    """
    Request data for all plants (Realtime, hourly, monthly or yearly)
    """
    logging.debug(f"Requesting plant data ({args.plant_action})")
    if args.plant_action == "real":
        data = client.get_plant_realtime_data(plants)

    elif args.plant_action == "hourly":
        data = client.get_plant_hourly_data(plants, datetime.now())

    elif args.plant_action == "daily":
        data = client.get_plant_daily_data(plants, datetime.now())

    elif args.plant_action == "monthly":
        data = client.get_plant_monthly_data(plants, datetime.now())

    else:
        data = client.get_plant_yearly_data(plants, datetime.now())

    if args.save:
        with args.save.open("w+") as f:
            json.dump([item.data for item in data], f, indent=2)

    for item in data:
        print(str(item))


def device_data(client: pyhfs.Client, plants: dict[str, pyhfs.Plant], args: argparse.Namespace):
    """
    Request data for all devices (Realtime, hourly, monthly or yearly)
    """
    logging.debug(f"Requesting device data ({args.device_action})")
    devices = {}
    for plant in plants.values():
        devices.update({d.id: d for d in plant.devices})

    if args.device_action == "real":
        data = client.get_device_realtime_data(devices)

    elif args.device_action == "history":
        if (args.end - args.start) > timedelta(days=3):
            logging.error("No more than 3 days when requesting device historical data")
            exit(-1)
        data = client.get_device_history_data(devices, args.start, args.end)

    elif args.device_action == "daily":
        data = client.get_device_daily_data(devices, datetime.now())

    elif args.device_action == "monthly":
        data = client.get_device_monthly_data(devices, datetime.now())

    else:
        data = client.get_device_yearly_data(devices, datetime.now())

    if args.save:
        with args.save.open("w+") as f:
            json.dump([item.data for item in data], f, indent=2)

    for item in data:
        print(str(item))


def alarm_data(client: pyhfs.Client, plants: dict[str, pyhfs.Plant], args: argparse.Namespace):
    """
    Request data for all devices (Realtime, hourly, monthly or yearly)
    """
    logging.debug("Requesting alarm data")
    data = client.get_alarms_list(plants, args.start, args.end)

    if args.save:
        with args.save.open("w+") as f:
            json.dump([item.data for item in data], f, indent=2)

    for item in data:
        print(str(item))


def how_to(user: str, password: str):
    """
    Demonstrates how to log in FusionSolar, query plants list and hourly data.
    """
    try:
        with pyhfs.ClientSession(user=user, password=password) as client:
            plants = client.get_plant_list()
            client.get_device_list(plants)

            # Extract list of plant codes
            plants_code = pyhfs.get_plant_codes(plants)

            # Query latest hourly data for all plants
            hourly = client.get_plant_hourly_data(plants_code, datetime.now(timezone.utc))
            print("Hourly KPIs:\n" + json.dumps(hourly, indent=2))

            # Real time plant data
            data = client.get_plant_realtime_data(plants_code)
            print("Realtime data: " + json.dumps(data, indent=2))

    except pyhfs.LoginFailed:
        logger.error("Login failed. Verify user and password of Northbound API account.")
    except pyhfs.FrequencyLimit:
        logger.error("FusionSolar interface access frequency is too high.")
    except pyhfs.Permission:
        logger.error("Missing permission to access FusionSolar Northbound interface.")


def parser():
    """
    Create parser and return arguments
    """
    parser = argparse.ArgumentParser("Fusion Solar API example")

    parser.add_argument(
        "--user",
        help="Username - If not set, get it from FUSIONSOLAR_USER environment variable",
    )
    parser.add_argument(
        "--password",
        help="Password - If not set, get it from FUSIONSOLAR_PASSWORD environment variable",
    )
    parser.add_argument(
        "--devices",
        type=Path,
        default=Path("devices.json"),
        help="JSON file to save/restore device list",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--save", type=Path, help="Save action response to this file")
    parser.add_argument(
        "--start",
        type=datetime.fromisoformat,
        default=(datetime.now() - timedelta(days=3, minutes=-5)).isoformat(),
        help="Start time for historical data (ISO format)",
    )
    parser.add_argument(
        "--end",
        type=datetime.fromisoformat,
        default=datetime.now().isoformat(),
        help="End time for historical data (ISO format)",
    )

    subparsers = parser.add_subparsers(title="action", description="select an action")

    pparser = subparsers.add_parser("plant", help="Plant data")
    pparser.add_argument(
        "plant_action", choices=("real", "hourly", "daily", "monthly", "yearly"), help="Fetch data for all plants"
    )
    pparser.set_defaults(func=plant_data)

    dparser = subparsers.add_parser("device", help="Device data")
    dparser.add_argument(
        "device_action", choices=("real", "history", "daily", "monthly", "yearly"), help="Fetch data for all devices"
    )
    dparser.set_defaults(func=device_data)

    aparser = subparsers.add_parser("alarms", help="Get alarm data")
    aparser.set_defaults(func=alarm_data)

    return parser.parse_args()


if __name__ == "__main__":
    args = parser()

    logging.basicConfig(
        format="%(module)-20s %(levelname)-8s: %(message)s",
        level=logging.DEBUG if args.debug else logging.INFO,
    )
    logger = logging.getLogger(__name__)

    user = args.user or os.environ.get("FUSIONSOLAR_USER", None)
    password = args.password or os.environ.get("FUSIONSOLAR_PASSWORD", None)

    if user is None or password is None:
        logger.fatal("Please set --user or FUSIONSOLAR_USER and --password or FUSION_SOLARPASSWORD to allow login")
        exit(-1)

    try:
        with pyhfs.ClientSession(user=user, password=password) as client:
            plants = None
            if args.devices.exists():
                logger.info(f"Reading list of devices from file {args.devices}")
                logger.info("Remove this file if you want to refresh the list of devices")
                try:
                    with args.devices.open("r") as f:
                        plants = pyhfs.Plant.from_list(json.load(f))
                except json.JSONDecodeError as e:
                    logger.error(f"Unable to read file {args.devices}: {e}")

            if plants is None:
                logger.info("Requesting list of devices.")
                plants = get_devices(client)
                with args.devices.open("w+") as f:
                    data = [plant.data for plant in plants.values()]
                    json.dump(data, f, indent=2)

            print("Plants and devices:\n")
            for plant in plants.values():
                print(f"{plant}")
                for device in plant.devices:
                    print(f"- {device}")
            print("")

            if hasattr(args, "func"):
                args.func(client, plants, args)

            else:
                logger.info("No action selected, exiting")

    except pyhfs.LoginFailed:
        logger.error("Login failed. Verify user and password of Northbound API account.")
    except pyhfs.FrequencyLimit:
        logger.error("FusionSolar interface access frequency is too high.")
    except pyhfs.Permission:
        logger.error("Missing permission to access FusionSolar Northbound interface.")
