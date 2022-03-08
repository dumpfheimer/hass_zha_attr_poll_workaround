import asyncio
import logging
import sys
import threading
import traceback
import yaml
from time import sleep

import asyncws
import json

callbacks = {}
websocket: asyncws.Websocket = None
nextId = 0
shutdown = False

config = yaml.safe_load(open("config.yaml"))
import pprint
pprint.pprint(config)

update_devices_id = None
devices = []

time_between_devices = config["time_between_devices"]
time_between_cycles = config["time_between_cycles"]

if not "websocket_url" in config:
    print("ERROR: No websocket_url configured")
    exit()


if not "access_token" in config:
    print("ERROR: No access_token configured")
    exit()

def next_id():
    global nextId
    nextId = nextId + 1
    return nextId

async def ws_thread():
    global websocket, callbacks, shutdown, devices, update_devices_id
    logging.info("ws_thread started")
    while not shutdown:
        try:
            logging.info("connecting new websocket connection")

            websocket = await asyncws.connect(config["websocket_url"])

            await websocket.send(json.dumps({'type': 'auth', 'access_token': config["access_token"]}))

            while not shutdown:
                message = await websocket.recv()
                logging.info(message)
                if message is not None:
                    try:
                        obj = json.loads(message)
                        if "id" in obj:
                            if obj["id"] == update_devices_id:
                                logging.debug("devices update result received")
                                if "result" in obj and obj["success"] == True:
                                    logging.debug("devices updated successfully")
                                    devices = []
                                    for device in obj["result"]:
                                        if "model" in device and device["model"] == "TS011F":
                                            logging.info("found smart metering plug")
                                            logging.debug(device)
                                            if "connections" in device:
                                                for connection_array in device["connections"]:
                                                    if connection_array[0] == "zigbee":
                                                        #logging.info("zigbee connection found: IEEE=%s" % connection_array[1])
                                                        devices.append(connection_array[1])

                                else:
                                    logging.error("devices were not received successfully")
                    except Exception:
                        logging.error("error in message receive")
                if message is None:
                    break
        except Exception:
            logging.error("had to restart websocket")
            if not shutdown:
                sleep(1.0)


def start():
    global shutdown, websocket
    asyncio.set_event_loop(asyncio.new_event_loop())
    try:
        asyncio.get_event_loop().run_until_complete(ws_thread())
    except KeyboardInterrupt as e:
        shutdown = True
        asyncio.get_event_loop().run_until_complete(websocket.close())
    finally:
        asyncio.get_event_loop().close()

async def update_energy_for(ieee: str):
    global websocket
    logging.info("updating energy for %s" % ieee)
    await websocket.send(json.dumps({'id': next_id(), 'type': 'zha/devices/clusters/attributes/value', 'attribute': 0, 'cluster_type': 'in', 'cluster_id': 1794, 'endpoint_id': 1, 'ieee': ieee}))

async def update_all_energy():
    global devices
    logging.info("updating energies")
    for ieee in devices:
        logging.info("updating %s" % ieee);
        await update_energy_for(ieee)
        await asyncio.sleep(time_between_devices)


def update_all_energy_tick():
    logging.info("updating energies tick")
    threading.Timer(time_between_devices * len(devices) + time_between_cycles, update_all_energy_tick).start()
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().run_until_complete(update_all_energy())

async def update_devices():
    global update_devices_id
    update_devices_id = next_id()
    await websocket.send(json.dumps({'type': 'config/device_registry/list', 'id': update_devices_id}))

def update_devices_tick():
    logging.info("updating devices tick")
    threading.Timer(600, update_devices_tick).start()
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().run_until_complete(update_devices())

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S')

    def callback(state):
        logging.info(state)

    threading.Timer(1, update_devices_tick).start()
    threading.Timer(5, update_all_energy_tick).start()

    start()
