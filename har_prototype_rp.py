import asyncio
from bleak import BleakClient, BleakScanner
import json
import csv
from datetime import datetime
from flask import Flask, request, jsonify
from threading import Thread


SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
CHARACTERISTIC_UUID = "abcd1234-5678-1234-5678-123456789abc"

app = Flask(__name__)


global_data = {
    "esp1": None,
    "esp2": None,
    "esp3": None,
    "esp4": None,
    "esp5": None
}
activity_data = None
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


    with open("activity.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        headers = ["activity_label", "activity_start_date", "activity_start_time", "activity_end_date", "activity_end_time"]
        writer.writerow(headers)


def append_to_csv(device_index, data):
    filename = f"esp{device_index}.csv"
    with open(filename, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(data)


def append_activity_to_csv(activity):
    with open("activity.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            activity["activity_label"],
            activity["activity_start_date"],
            activity["activity_start_time"],
            activity["activity_end_date"],
            activity["activity_end_time"]
        ])


async def update_global_data(key, value):
    async with data_lock:
        global_data[key] = value

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

                        asyncio.create_task(update_global_data(f"esp{device_index}", row))
                        append_to_csv(device_index, row)
                        print(f"{device_name} - Data written to esp{device_index}.csv.")

                    except Exception as e:
                        print(f"{device_name} - Error processing data: {e}")

                await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                print(f"Listening to {device_name}... Press Ctrl+C to exit.")

                while client.is_connected:
                    await asyncio.sleep(1)

        except Exception as e:
            print(f"Error with {device_name} at {device_address}: {e}")
            print(f"Reconnecting to {device_name}...")

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

    if not any([esp1_devices, esp2_devices, esp3_devices, esp4_devices, esp5_devices]):
        print("No devices found!")
        return

    print("BLE scan complete. Connecting to devices...")
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

    await asyncio.gather(*tasks)

@app.route('/data', methods=['GET'])
def get_data():
    async def fetch_data():
        async with data_lock:
            formatted_data = {
                f"ESP{i+1}": {
                    "MPU1": {
                        "ax": data[0], "ay": data[1], "az": data[2],
                        "gx": data[3], "gy": data[4], "gz": data[5]
                    },
                    "MPU2": {
                        "ax": data[6], "ay": data[7], "az": data[8],
                        "gx": data[9], "gy": data[10], "gz": data[11]
                    },
                    "HMC": {
                        "x": data[12], "y": data[13], "z": data[14], "degrees": data[15]
                    },
                    "Timestamps": {
                        "date": data[16], "time": data[17]
                    }
                } for i, data in enumerate(global_data.values()) if data
            }
            return formatted_data

    data = asyncio.run(fetch_data())
    return jsonify(data)

@app.route('/activity', methods=['POST'])
def post_activity():
    global activity_data
    try:
        data = request.json
        required_keys = ["activity_label", "activity_start_date", "activity_start_time", "activity_end_date", "activity_end_time"]

        if not all(key in data for key in required_keys):
            return jsonify({"status": "error", "message": "Missing required keys."}), 400

        # Update global activity_data
        activity_data = {
            "activity_label": data["activity_label"],
            "activity_start_date": data["activity_start_date"],
            "activity_start_time": data["activity_start_time"],
            "activity_end_date": data["activity_end_date"],
            "activity_end_time": data["activity_end_time"]
        }

        append_activity_to_csv(activity_data)  # Write to activity.csv

        print("Activity data updated:", activity_data)
        return jsonify({"status": "success", "updated_activity": activity_data}), 200
    except Exception as e:
        print("Error processing POST request for activity:", e)
        return jsonify({"status": "error", "message": str(e)}), 400

# Flask server runner
def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)

# Run Flask in a separate thread to avoid blocking the asyncio event loop
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

# Execute the main function
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nProgram terminated.")
