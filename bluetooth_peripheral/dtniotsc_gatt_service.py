from enum import Enum
import logging

import dbus

from .dbus_bluez_interfaces import Characteristic, Service, string_to_dbus_array

logger = logging.getLogger(__name__)


class IoTSCUuids(object):
    SENDER_SERVICE = '2CD595E2-0078-40E7-AA33-6585E73FD70C'
    COLLECTOR_SERVICE = '1C2C56D0-19EB-413F-9F0A-BF71C48B9056'

    DEVICE_ID = '51F4C7BC-3A1B-43CF-BB86-6F8B93446EDC'
    HUMIDITY = '2A6F'
    TEMPERATURE = '2A1C'


class IoTSCService(Service):
    """
    Concrete implementation of a GATT service that can be used for raspberry pi3 sensors. This is based off of Bluez GATT Peripheral (https://github.com/getsenic/senic-hub/tree/master/senic_hub/bluenet)
    """

    def __init__(self, bus, index, is_collector, device_id, version):
        if is_collector:
            super().__init__(bus, index, IoTSCUuids.COLLECTOR_SERVICE, True)
        else:
            super().__init__(bus, index, IoTSCUuids.SENDER_SERVICE, True)
  
        self._is_collector = is_collector
        self._device_id_characteristic = DeviceIDCharacteristic(bus, 0, device_id, self)
        '''
        self._humidity_characteristic = HumidityCharacteristic(bus, 1, self)
        self._temperature_characteristic = TemperatureCharacteristic(bus, 2, self) 
        '''
        self.add_characteristic(self._device_id_characteristic)
        '''
        self.add_characteristic(self._humidity_characteristic)
        self.add_characteristic(self.self._temperature_characteristic)
        '''

    def set_device_id(self, device_id):
        self._device_id_characteristic.device_id = device_id


class DeviceIDCharacteristic(Characteristic):
    """
    GATT characteristic providing the version of this GATT service.

    Possible operations: Read
    Content: Version as a string (array of characters)
    """

    def __init__(self, bus, index, device_id, service):
        if service._is_collector:
            super().__init__(bus, index, IoTSCUuids.DEVICE_ID, ['write'], service)
        else:
            super().__init__(bus, index, IoTSCUuids.DEVICE_ID, ['read'], service)
        
        self.device_id = device_id

    def _read_value(self, options):
        logger.info("Sending DeviceID Value")
        return string_to_dbus_array(self.self.device_id)

    def _write_value(self, value, options):
        rec_value = bytes(value).decode()
        logger.info("Received DeviceID: %s" % rec_value)


