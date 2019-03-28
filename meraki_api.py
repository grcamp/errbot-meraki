#########################################################################
# Gregory Camp
# grcamp@cisco.com
# meraki_api.py
#
#
# Testing Summary:
#
# Usage:
#   ./meraki_api.py
#
# Example config.json:
# {
#     "email": {
#         "smtp": "outbound.cisco.com",
#         "from": "grcamp@cisco.com",
#         "to": "someone@somewhere.com,someoneelse@somewhere.com",
#         "cc": "someone@someplace.com,someoneelse@someplace.com"
#     }
# }
#
#
# Global Variables:
#    logger = Used for Debug output and script info
#
#########################################################################

import requests
import logging

# Define global variables
logger = logging.getLogger(__name__)
baseurl = 'https://dashboard.meraki.com/api/v0'
headers = ""

def info(msg):
    logger.info(msg)


def warning(msg):
    logger.warning(msg)


def error(msg):
    logger.error(msg)


def fatal(msg):
    logger.fatal(msg)
    exit(1)


#########################################################################
# Class Organization
#
# Container for networks
#########################################################################
class Organization:
    def __init__(self, id, name, headers):
        self.id = id
        self.name = name
        self.headers = headers
        self.networks = []

    def get_networks(self):
        '''
        :return:
        '''
        # Log step
        info("Obtaining List of Networks for Organization {} with ID {}".format(self.name, self.id))
        # Discover networks
        response = requests.get("{}/organizations/{}/networks".format(baseurl, self.id), headers=self.headers)
        networks = response.json()

        # Obtain devices for each network
        for network in networks:
            new_network = Network(str(network.get('id')), str(network.get('name')), str(network.get('type')),
                                  self)
            self.networks.append(new_network)

        # Return None
        return None

    def get_uplink_loss_and_latency(self, ip, timespan, uplink):
        # Return wan_devices
        my_org = {'org_name': self.name,
                  'org_id': self.id,
                  'networks': []}

        # Obtain data for each network
        for network in self.networks:
            wan_devices = network.get_uplink_loss_and_latency(ip, timespan, uplink)

            # Check if wan_devices found
            if len(wan_devices) > 0:
                new_devices = []

                # Append device dictionaries
                for device in wan_devices:
                    new_device = {'device_name': device.name,
                                  'device_serial': device.serial,
                                  'perf_data': device.perf_data
                                  }
                    new_devices.append(new_device)

                new_network = {'network_name': network.name,
                               'network_id': network.id,
                               'devices': new_devices
                               }
                my_org['networks'].append(new_network)

        # Return my_org
        return my_org

#########################################################################
# Class Network
#
# Container for networks
#########################################################################
class Network:
    def __init__(self, id, name, type, organization):
        self.id = id
        self.name = name
        self.type = type
        self.organization = organization
        self.devices = []

    def get_devices(self):
        '''
        :return:
        '''
        # Log step
        info("Obtaining List of Devices for Network {} with ID {}".format(self.name, self.id))
        # Discover devices
        response = requests.get("{}/networks/{}/devices".format(baseurl, self.id), headers=self.organization.headers)
        devices = response.json()

        # Build device list
        for device in devices:
            new_device = Device(str(device.get('serial')), str(device.get('name')), str(device.get('model')), self)
            self.devices.append(new_device)

        # Return None
        return None

    def get_uplink_loss_and_latency(self, ip, timespan, uplink):
        # Set return value
        wan_devices = []

        # Obtain uplink data if an MX exists
        for device in self.devices:
            if device.model.startswith('MX'):
                if (device.get_uplink_loss_and_latency(ip, timespan, uplink)):
                    wan_devices.append(device)

        # Return wan_devices
        return wan_devices


#########################################################################
# Class Device
#
# Container for devices
#########################################################################
class Device:
    def __init__(self, serial, name, model, network):
        self.serial = serial
        self.name = name
        self.model = model
        self.network = network
        self.perf_data = {}


    def get_uplink_loss_and_latency(self, ip, timespan, uplink):
        '''
        :return:
        '''
        # Log step
        info("Obtaining Uplink Loss Percentage for Device {} with Serial {}".format(self.name, self.serial))
        # Discover devices
        response = requests.get(
            "{}/networks/{}/devices/{}/lossAndLatencyHistory?ip={}&timespan={}&uplink={}".format(baseurl,
                                                                                                 self.network.id,
                                                                                                 self.serial,
                                                                                                 ip,
                                                                                                 str(timespan),
                                                                                                 uplink),
                                headers=self.network.organization.headers)
        samples = response.json()

        # If no samples are found, exit
        if len(samples) == 0:
            # Return None
            return False

        # Return value
        self.perf_data = {'avg_latency': float(0),
                          'avg_loss_percent': float(0),
                          'min_latency': float(1000),
                          'min_loss_percent': 100,
                          'max_latency': float(0),
                          'max_loss_percent': 0,
                          'samples': []
                          }

        total_latency = 0.0
        total_loss_percent = 0

        # Build loop through list for calculations
        for sample in samples:
            # Check for max loss
            if sample.get('lossPercent') > self.perf_data.get('max_loss_percent'):
                self.perf_data['max_loss_percent'] = sample.get('lossPercent')
            # Check for min loss
            if sample.get('lossPercent') < self.perf_data.get('min_loss_percent'):
                self.perf_data['min_loss_percent'] = sample.get('lossPercent')
            # Check for min loss
            if sample.get('latencyMs') > self.perf_data.get('max_latency'):
                self.perf_data['max_latency'] = sample.get('latencyMs')
            # Check for min loss
            if sample.get('latencyMs') < self.perf_data.get('min_latency'):
                self.perf_data['min_latency'] = sample.get('latencyMs')

            # Add to total
            total_latency += sample.get('latencyMs')
            total_loss_percent += sample.get('lossPercent')
            # Append sample to list
            self.perf_data['samples'].append(sample)

        # Compute averages
        self.perf_data['avg_latency'] = float(total_latency) / float(len(samples))
        self.perf_data['avg_loss_percent'] = float(total_loss_percent) / float(len(samples))

        # Return None
        return True


class Meraki_Dashboard_Client:
    def __init__(self, api_key):
        '''
        :param api_key:
        '''
        # Declare variables
        self.headers = {'X-Cisco-Meraki-API-Key': api_key,'Content-Type': 'application/json'}
        self.organizations = []

    def login(self):
        # Set return value
        return_val = False

        # Log step
        info("Obtaining List of Organizations Associated to Meraki Dashboard with API Key")

        try:
            result = requests.get("{}/organizations".format(baseurl), headers=self.headers)
            orgs = result.json()
            self._discover_networks(orgs)
            return_val = True
        except:
            return_val = False

        # Return return_val
        return return_val


    def _discover_networks(self, orgs):
        # For each org in list, build an org data structure
        for org in orgs:
            new_org = Organization(str(org.get('id')), org.get('name'), self.headers)
            self.organizations.append(new_org)
            new_org.get_networks()

        # Return None
        return None

    def discover_devices(self):
        # For each org in list, obtain device list
        for org in self.organizations:
            for network in org.networks:
                network.get_devices()

        # Return True
        return True

    def get_uplink_loss_and_latency(self):
        # Set list of devices
        org_data = []
        # For each org in list, obtain device list
        for org in self.organizations:
            org_data.append(org.get_uplink_loss_and_latency("8.8.8.8", 86400, "wan1"))

        # Return True
        return org_data
