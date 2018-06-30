#!/usr/bin/python3

import click
import dbus
import dbus.mainloop.glib
import logging
import time
from threading import Thread
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

from bluetooth_peripheral.bluez_peripheral import Peripheral
from bluetooth_peripheral.dtniotsc_gatt_service import IoTSCService, IoTSCUuids


logger = logging.getLogger(__name__)

@click.group()
@click.pass_context
@click.option('--collector', '-c', required=False, help="Collects info or sends info (default = False)")
@click.option('--bluetooth', '-b', required=False, help="Bluetooth device")
def dtniotsc_cli(ctx, collector, bluetooth):
    if not collector:
        collector = False
    ctx.obj = DTNIoTSCDaemon(collector, bluetooth)


@dtniotsc_cli.command(name='start', help="start GATT service and advertisements")
@click.option('--deviceid', '-d', required=True, help="Host Name of Hub, %IP is replaced with the current IP address")
@click.option('--alias', '-a', required=True, help="Bluetooth Alias Name")
#@click.option('--config-file', '-f', required=True, help="Input file consisting of sensor and mqtt configurations")
@click.option('--verbose', '-v', count=True, help="Print info messages (-vv for debug messages)")
@click.option('--auto-advertise', is_flag=True, help="Disable BLE advertising when not needed")
@click.option('--log-file', '-l', required=False, help="Output file for log/debug")
@click.pass_context
def dtniotsc_start(ctx, deviceid, alias, verbose, auto_advertise, log_file): #config_file, verbose, auto_advertise, log_file):
    if not log_file:
        log_file = "log.txt"
    
    log_format = '%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
    if verbose >= 2:
        logging.basicConfig(filename=log_file, level=logging.DEBUG, format=log_format, filemode='w')
    elif verbose >= 1:
        logging.basicConfig(filename=log_file, level=logging.INFO, format=log_format, filemode='w')
    else:
        logging.basicConfig(filename=log_file, level=logging.WARNING, format=log_format, filemode='w')
    ctx.obj.run(deviceid, alias, auto_advertise) #config_file, auto_advertise)

class DTNIoTSCDaemon(object):
    """
    Daemon to enable Bluetooth Low Energy.
    The run() method creates the Bluetooth GATT server.
    """
    
    def __init__(self, is_collector, bluetooth_adapter):
        """
        Initializes the object. It can then be started with run().
        :param wlan_adapter: name of the WLAN adapter (i.e. 'wlan0')
        :param bluetooth_adapter: name of the bluetooth adapter (i.e. 'hci0')
        """
        self._is_collector = is_collector
        self._bluetooth_adapter = bluetooth_adapter
        self._gatt_service = None
        self._ble_peripheral = None
        self._auto_advertise = False
        self._deviceid = None
        self._iotsc_dashboard = None
        #self._config_file = None

    def run(self, deviceid, bluetooth_alias, auto_advertise): #"""config_file,""" auto_advertise):
        self._deviceid = deviceid
        self._auto_advertise = auto_advertise
        #self._config_file = config_file
        
        # prepare BLE GATT Service:
        self._ble_peripheral = Peripheral(bluetooth_alias, self._bluetooth_adapter)
        gatt_service = IoTSCService(self._ble_peripheral.bus, 0, self._is_collector, self._deviceid, "1.0")
        self._gatt_service = gatt_service
        self._ble_peripheral.add_service(gatt_service)
        if self._is_collector:
            self._ble_peripheral.add_advertised_service_uuid(IoTSCUuids.COLLECTOR_SERVICE)
            #self._iotsc_dashboard = IoTSCDashboard(self._config_file, , False)
        else:
            self._ble_peripheral.add_advertised_service_uuid(IoTSCUuids.SENDER_SERVICE)
        self._ble_peripheral.on_remote_disconnected = self._update_advertising_state
        
        # create thread for rpc server:
        rpc_thread = Thread(target=self._start_rpc_server, daemon=True)
        rpc_thread.start()
        
        self._ble_peripheral.run()

    def _update_advertising_state(self):
        if (self._auto_advertise and
            not self._ble_peripheral.is_connected and
            self._ble_peripheral.is_advertising):
            # re-enabling advertisement is not possible while a device is connected
            # because of that we are not disabling it in the first place when a device is connected
            logging.info("BLE connected. Stopping BLE advertisements.")
            self._ble_peripheral.stop_advertising()
        elif (not self._ble_peripheral.is_advertising and
              not self._auto_advertise):
            logging.info("Starting BLE advertisements.")
            self._ble_peripheral.start_advertising()

    def _update_deviceid(self):
        deviceid = self._get_deviceid()
        logger.info("New deviceid: %s" % deviceid)
        self._gatt_service.set_deviceid(deviceid)

    def _start_rpc_server(self):
        """
        Starts a XML RPC server that can be used check if this Bluenet instance is connected
        to a setup app. (Netwatch won't stop DTNIoTSC in this case)
        """
                
        def is_dtniotsc_connected():
            return self._ble_peripheral.is_connected
                    
        server = SimpleXMLRPCServer(('127.0.0.1', 6459), requestHandler=RequestHandler)
        server.register_function(is_dtniotsc_connected)
        logger.info("Starting RPC server")
        server.serve_forever()


class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


if __name__ == '__main__':
    dtniotsc_cli()

