"""
Support for getting Energy bill  data from Mahadiscom portal.

configuration.yaml

sensor:
  - platform: mahadiscom
    ConsumerNo: 170020034907
    BuNumber: 4637
    consumerType: 2
    scan_interval: 30
"""
from __future__ import annotations

import logging
from datetime import timedelta
import voluptuous as vol
import requests
import json
import time
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.const import ( CONF_RESOURCES  )
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

DOMAIN = "mahadiscom_hass"
DEFAULT_NAME = "MahaDiscom Energy Bill"

_LOGGER = logging.getLogger(__name__)

CONF_CONSUMERNO = "ConsumerNo"
CONF_BUNUMBER = "BuNumber"
CONF_CONSUMERTYPE = "consumerType"

BASE_URL = 'https://wss.mahadiscom.in/wss/'
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)

SENSOR_PREFIX = 'mahadiscom_'
SENSOR_TYPES = {
    'billMonth': ['Bill Month',  'mdi:calendar'],
    'billAmount': ['Bill Amount',  'mdi:cash-100'],
    'consumptionUnits': ['Consumption Units', 'mdi:weather-sunny'],
    'billDate': ['Bill Date',  'mdi:calendar'],
    'dueDate': ['Due Date',  'mdi:calendar'],
    'promptPaymentDate': ['Prompt payment date', 'mdi:calendar'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_CONSUMERNO): cv.string,
    vol.Required(CONF_BUNUMBER): cv.string,
    vol.Required(CONF_CONSUMERTYPE): cv.string,
    vol.Required(CONF_RESOURCES, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)])
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the Mahadiscom Energy bill sensor."""
    consumer_no = config.get(CONF_CONSUMERNO)
    bu_number = config.get(CONF_BUNUMBER)
    consumer_type = config.get(CONF_CONSUMERTYPE)

    try:
        data = MahadiscomEnergyBillData(consumer_no, bu_number, consumer_type)
    except RuntimeError:
        _LOGGER.error("Unable to connect to Mahadiscom Portal %s:%s",
                      BASE_URL)
        return False

    entities = []
    entities.append(MahadiscomEnergyBillSensor(data, "billMonth", consumer_no))
    entities.append(MahadiscomEnergyBillSensor(data, "billAmount", consumer_no))
    entities.append(MahadiscomEnergyBillSensor(data, "consumptionUnits", consumer_no))
    entities.append(MahadiscomEnergyBillSensor(data, "billDate", consumer_no))
    entities.append(MahadiscomEnergyBillSensor(data, "dueDate", consumer_no))
    entities.append(MahadiscomEnergyBillSensor(data, "promptPaymentDate", consumer_no))
    add_entities(entities)
    
    return True


# pylint: disable=abstract-method
class MahadiscomEnergyBillData(object):
    """Representation of a Mahadiscom Energy Bill."""

    def __init__(self, consumer_no, bu_number, consumer_type):
        """Initialize the portal."""
        self.consumer_details = {}
        self.consumer_details['ConsumerNo'] = consumer_no
        self.consumer_details['BuNumber'] = bu_number
        self.consumer_details['consumerType'] = consumer_type
        self.data = None
        self.Captcha = ""


    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update the data from the portal."""
         
        session = requests.Session()
        _LOGGER.info("requesting captcha")
        self.Captcha = self._fetch_captcha(session)
        
        view_details = {
            'txtInput': self.Captcha,
            'BuNumber': "",
            'ConsumerNo': self.consumer_details['ConsumerNo'],
        }
        
        actionUrl = 'wss?uiActionName=postViewPayBill&IsAjax=true'
        url = BASE_URL + actionUrl

        _LOGGER.info("requesting")
        try:
            response = session.post(url, data=view_details)
            self.data = json.loads(response.text)
            _LOGGER.info("Successfully fetched data from Mahadiscom Portal")
        except requests.ConnectionError as e:
            _LOGGER.info("OOPS!! Connection Error. Make sure you are connected to Internet. Technical Details given below.\n")
            _LOGGER.error(str(e))
        except requests.Timeout as e:
            _LOGGER.info("OOPS!! Timeout Error")
            _LOGGER.error(str(e))
        except requests.RequestException as e:
            _LOGGER.info("OOPS!! General Error")
            _LOGGER.error(str(e))
        except KeyboardInterrupt:
            _LOGGER.warning("Someone closed the program")
            
        self.Captcha = ""
        
    def _fetch_captcha(self, session) -> str:
        
        actionurl = 'wss?uiActionName=RefreshCaptchaViewPay&IsAjax=true'
        url = BASE_URL + actionurl

        view_details = {
            'FormName': 'NewConnection'
        }

        try:
            response = session.get(url, data=view_details)
            if response.status_code == 200:
                return json.loads(response.text)
        except Exception as err:
            _LOGGER.error("Error fetching captcha: %s", err)
        return ""


class MahadiscomEnergyBillSensor(Entity):
    """Representation of a MahadiscomEnergyBill sensor."""

    def __init__(self, data, sensor_type, consumer_no):
        """Initialize the sensor."""
        self.data = data
        self.type = sensor_type
        self._name = sensor_type
        self._state = None
        self.update()


    @property
    def name(self):
        """Return the name of the sensor."""
        return SENSOR_TYPES[self.type][0]

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
    
    @property
    def unique_id(self):
        """Unique ID for Home Assistant entity registry."""
        return self._name
    
    @property
    def icon(self):
        """Return the icon for the sensor."""
        return SENSOR_TYPES[self.type][1]
    
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement, if any."""
        if self.type == "consumptionUnits":
            return "kWh"
        elif self.type == "billAmount":
            return "₹"
        return None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.data.consumer_details['ConsumerNo'])},
            "name": "Mahadiscom Energy Meter",
            "manufacturer": "Mahadiscom",
            "entry_type": "service"
        }
        
        
    def update(self):
        """Get the latest data and use it to update our sensor state."""
        self.data.update()
        billdetails = self.data.data
        if (billdetails and billdetails != 'error'):
            if self.type == 'billMonth':
                self._state = billdetails.get('billMonth')
            elif self.type == 'billAmount':
                self._state = billdetails.get('billAmount')
            elif self.type == 'consumptionUnits':
                self._state = billdetails.get('consumptionUnits')
            elif self.type == 'billDate':
                self._state = billdetails.get('billDate')
            elif self.type == 'dueDate':
                self._state = billdetails.get('dueDate')
            elif self.type == 'promptPaymentDate':
                val = billdetails['promptPaymentDate'].split('(', 1)[1].split(')')[0]
                self._state = time.strftime("%d-%b-%Y", time.localtime(int(val)/1000))