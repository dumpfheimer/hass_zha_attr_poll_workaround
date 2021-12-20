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

if not "websocket_url" in config:
    print("ERROR: No websocket_url configured")
    exit()


if not "access_token" in config:
    print("ERROR: No access_token configured")
    exit()


if not "devices" in config:
    print("ERROR: No devices configured")
    exit()

if len(config["devices"]) == 0:
    print("ERROR: No devices configured (devices entry present, but 0 devices found)")
    exit()

print("Configured with %d devices" % len(config["devices"]))

def next_id():
    global nextId
    nextId = nextId + 1
    return nextId

async def ws_thread():
    global websocket, callbacks, shutdown
    logging.info("ws_thread started")
    while not shutdown:
        try:
            logging.info("connecting new websocket connection")

            websocket = await asyncws.connect(config["websocket_url"])

            await websocket.send(json.dumps({'type': 'auth', 'access_token': config["access_token"]}))

            while not shutdown:
                message = await websocket.recv()
                logging.info(message)

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
    logging.info("updating energies")
    for ieee in config.devices:
        await update_energy_for(ieee)


def update_all_energy_tick():
    logging.info("updating energies tick")
    threading.Timer(60, update_all_energy_tick).start()
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().run_until_complete(update_all_energy())

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S')

    def callback(state):
        logging.info(state)
    threading.Timer(5, update_all_energy_tick).start()

    start()
