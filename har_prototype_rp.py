import asyncio
from bleak import BleakClient, BleakScanner
import json
import csv
from datetime import datetime

SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
CHARACTERISTIC_UUID = "abcd1234-5678-1234-5678-123456789abc"


global_data = {
    "esp1": None,
    "esp2": None,
    "esp3": None,
    "esp4": None,
    "esp5": None,
    "activity": None
}
data_lock = asyncio.Lock()


def initialize_csv_files():
    for i in range(1, 6):
        filename = f"esp{i}.csv"
        with open(filename, mode="w", newline="") as file:
            writer = csv.writer(file)
            headers = [
                "mpu1_ax", "mpu1_ay", "mpu1_az", "mpu1_gx", "mpu1_gy", "mpu1_gz",
                "mpu2_ax", "mpu2_ay", "mpu2_az", "mpu2_gx", "mpu2_gy", "mpu2_gz",
                "HMC_x", "HMC_y", "HMC_z", "Heading_degrees", "Date", "Time"
            ]
            writer.writerow(headers)


def append_to_csv(device_index, data):
    filename = f"esp{device_index}.csv"
    with open(filename, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(data)


async def connect_and_listen(device_name, device_address, device_index):
    while True:
        try:
            async with BleakClient(device_address) as client:
                print(f"Connected to {device_name} at {device_address}")


                def notification_handler(sender, data):
                    try:
                        decoded_data = data.decode()
                        sensor_data = json.loads(decoded_data)


                        now = datetime.now()
                        date_str = now.strftime("%Y-%m-%d")
                        time_str = now.strftime("%H:%M:%S")


                        row = [
                            sensor_data.get("mpu1", {}).get("ax", "N/A"),
                            sensor_data.get("mpu1", {}).get("ay", "N/A"),
                            sensor_data.get("mpu1", {}).get("az", "N/A"),
                            sensor_data.get("mpu1", {}).get("gx", "N/A"),
                            sensor_data.get("mpu1", {}).get("gy", "N/A"),
                            sensor_data.get("mpu1", {}).get("gz", "N/A"),
                            sensor_data.get("mpu2", {}).get("ax", "N/A"),
                            sensor_data.get("mpu2", {}).get("ay", "N/A"),
                            sensor_data.get("mpu2", {}).get("az", "N/A"),
                            sensor_data.get("mpu2", {}).get("gx", "N/A"),
                            sensor_data.get("mpu2", {}).get("gy", "N/A"),
                            sensor_data.get("mpu2", {}).get("gz", "N/A"),
                            sensor_data.get("HMCx", "N/A"),
                            sensor_data.get("HMCy", "N/A"),
                            sensor_data.get("HMCz", "N/A"),
                            sensor_data.get("Heading", "N/A"),
                            date_str,
                            time_str
                        ]

                        append_to_csv(device_index, row)
                        print(f"{device_name} - Data written to esp{device_index}.csv.")

                    except Exception as e:
                        print(f"{device_name} - Error processing data: {e}")


                await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                print(f"Listening to {device_name}... Press Ctrl+C to exit.")


                while True:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"Error with {device_name}: {e}")
        print(f"Reconnecting to {device_name}...")
        await asyncio.sleep(5)


async def connect_and_listen_android(device_name, device_address):
    while True:
        try:
            async with BleakClient(device_address) as client:
                print(f"Connected to Android App ({device_address})")


                def notification_handler(sender, data):
                    try:
                        decoded_data = data.decode()
                        activity_data = json.loads(decoded_data)

                        global_data["activity"] = activity_data
                        print(f"Received activity data: {activity_data}")
                    except Exception as e:
                        print(f"Error processing activity data: {e}")

                await client.start_notify(CHARACTERISTIC_UUID, notification_handler)


                while client.is_connected:
                    async with data_lock:

                        esp_data = {
                            "esp1": global_data.get("esp1"),
                            "esp2": global_data.get("esp2"),
                            "esp3": global_data.get("esp3"),
                            "esp4": global_data.get("esp4"),
                            "esp5": global_data.get("esp5"),
                        }

                    try:
                        if any(esp_data.values()):
                            encoded_data = json.dumps(esp_data).encode()
                            await client.write_gatt_char(CHARACTERISTIC_UUID, encoded_data)
                            print(f"Sent sensor data to Android App: {esp_data}")
                    except Exception as e:
                        print(f"Error sending sensor data to Android App: {e}")

                    await asyncio.sleep(1)
        except Exception as e:
            print(f"Error with Android App: {e}")
        print(f"Reconnecting to Android App...")
        await asyncio.sleep(5)


async def main():
    initialize_csv_files()

    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()


    esp1_devices = [device for device in devices if "ESP32-1" in device.name]
    esp2_devices = [device for device in devices if "ESP32-2" in device.name]
    esp3_devices = [device for device in devices if "ESP32-3" in device.name]
    esp4_devices = [device for device in devices if "ESP32-4" in device.name]
    esp5_devices = [device for device in devices if "ESP32-5" in device.name]

    android_devices = [device for device in devices if "AndroidApp" in device.name]

    if not any([esp1_devices, esp2_devices, esp3_devices, esp4_devices, esp5_devices, android_devices]):
        print("No devices found!")

    tasks = []

    if esp1_devices:
        for device in esp1_devices:
            tasks.append(asyncio.create_task(connect_and_listen(device.name, device.address, 1)))
            await asyncio.sleep(1)

    if esp2_devices:
        for device in esp2_devices:
            tasks.append(asyncio.create_task(connect_and_listen(device.name, device.address, 2)))
            await asyncio.sleep(1)

    if esp3_devices:
        for device in esp3_devices:
            tasks.append(asyncio.create_task(connect_and_listen(device.name, device.address, 3)))
            await asyncio.sleep(1)

    if esp4_devices:
        for device in esp4_devices:
            tasks.append(asyncio.create_task(connect_and_listen(device.name, device.address, 4)))
            await asyncio.sleep(1)

    if esp5_devices:
        for device in esp5_devices:
            tasks.append(asyncio.create_task(connect_and_listen(device.name, device.address, 5)))
            await asyncio.sleep(1)

    if android_devices:
        for device in android_devices:
            tasks.append(asyncio.create_task(connect_and_listen_android(device.name, device.address)))


    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nProgram terminated.")
