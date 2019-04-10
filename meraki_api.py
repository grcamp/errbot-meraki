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
#
#
# Global Variables:
#    logger = Used for Debug output and script info
#    baseurl = URL of Meraki Cloud
#    headers = API header value used for authentication
#
#########################################################################

import requests
import logging
import datetime
from operator import itemgetter
import matplotlib.pyplot as plt

# Define global variables
logger = logging.getLogger(__name__)
baseurl = 'https://api.meraki.com/api/v0'
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
# Container for organization data
#########################################################################
class Organization:
    def __init__(self, id, name, headers):
        self.id = id
        self.name = name
        self.headers = headers
        self.networks = []

    def get_inventory(self):
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

        # Log step
        info("Obtaining List of Devices for Organization {} with ID {}".format(self.name, self.id))
        # Discover inventory
        response = requests.get("{}/organizations/{}/inventory".format(baseurl, self.id), headers=self.headers)
        devices = response.json()

        # Obtain devices for each network
        for device in devices:
            for network in self.networks:
                if device.get('networkId') == network.id:
                    network.add_device(device)

        # Return None
        return None

    def get_uplink_loss_and_latency(self, ip, timespan, uplink):
        # Return wan_devices
        my_org = {'name': self.name,
                  'id': self.id,
                  'networks': []}

        # Obtain data for each network
        for network in self.networks:
            wan_devices = network.get_uplink_loss_and_latency(ip, timespan, uplink)

            # Check if wan_devices found
            if len(wan_devices) > 0:
                new_devices = []

                # Append device dictionaries
                for device in wan_devices:
                    new_device = {'name': device.name,
                                  'serial': device.serial,
                                  'perf_data': device.perf_data
                                  }
                    new_devices.append(new_device)

                new_network = {'name': network.name,
                               'id': network.id,
                               'devices': new_devices
                               }
                my_org['networks'].append(new_network)

        # Return my_org
        return my_org

    def get_top_talkers(self, timespan, count=0):
        # Return wan_devices
        my_org = {'name': self.name,
                  'id': self.id,
                  'networks': []}

        # Obtain data for each network
        for network in self.networks:
            wan_devices = network.get_top_talkers(timespan)

            # Check if wan_devices found
            if len(wan_devices) > 0:
                new_devices = []

                found_client = False

                # Append device dictionaries
                for device in wan_devices:
                    # If clients exist, add the device to the list
                    if len(device.clients) > 0:
                        new_device = {'name': device.name,
                                      'serial': device.serial,
                                      'clients': device.clients
                                      }
                        # Trim client count
                        if count > 0:
                            new_device['clients'] = new_device['clients'][:count]

                        new_devices.append(new_device)

                        found_client = True

                if found_client:
                    # Create new network and add
                    new_network = {'name': network.name,
                                   'id': network.id,
                                   'devices': new_devices
                                   }

                    my_org['networks'].append(new_network)

        # Return my_org
        return my_org

    def graph_uplink_loss_and_latency(self, device_name, ip, timespan, uplink):
        # Find current time string
        current_time = datetime.datetime.now()
        date_string = "{}-{}-{}_{}{}{}".format(str(current_time.year).zfill(4), str(current_time.month).zfill(2),
                                               str(current_time.day).zfill(2), str(current_time.hour).zfill(2),
                                               str(current_time.minute).zfill(2), str(current_time.second).zfill(2))
        # Return wan_devices
        graphs = []

        # Obtain data for each network
        for network in self.networks:
            graphs += network.graph_uplink_loss_and_latency(device_name, date_string, ip, timespan, uplink)

        # Return images
        return graphs


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

    def add_device(self, device):
        '''
        :return:
        '''
        # Build device
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

    def get_top_talkers(self, timespan):
        # Set return value
        wan_devices = []

        # Obtain uplink data if an MX exists
        for device in self.devices:
            if device.model.startswith('MX'):
                if (device.get_top_talkers(timespan)):
                    wan_devices.append(device)

        # Return wan_devices
        return wan_devices

    def graph_uplink_loss_and_latency(self, device_name, date, ip, timespan, uplink):
        # Set return value
        graphs = []

        # Obtain uplink data if an MX exists
        for device in self.devices:
            if device.model.startswith('MX') and device_name.lower() == device.name.lower():
                graphs += device.graph_uplink_loss_and_latency(date, ip, timespan, uplink)

        # Return graphs
        return graphs

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
        self.clients = []

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
        self.perf_data['avg_latency'] = round(float(total_latency) / float(len(samples)), 1)
        self.perf_data['avg_loss_percent'] = round(float(total_loss_percent) / float(len(samples)), 1)

        # Return True
        return True


    def get_top_talkers(self, timespan):
        # Log step
        info("Obtaining Client List for Device {} with Serial {}".format(self.name, self.serial))
        # Discover devices
        response = requests.get("{}/devices/{}/clients?timespan={}".format(baseurl, self.serial, str(timespan)),
                                headers=self.network.organization.headers)
        samples = response.json()

        # Loop through samples to build clients
        for sample in samples:
            # Create new client
            new_client = {'description': str(sample.get('description')),
                          'sent_mbytes': round(sample.get('usage').get('sent') / float(1000), 1),
                          'recv_mbytes': round(sample.get('usage').get('recv') / float(1000), 1),
                          'total_mbytes': round((sample.get('usage').get('sent') + sample.get('usage').get('recv')) / float(1000), 1),
                          'ip': str(sample.get('ip')),
                          'mac': str(sample.get('mac'))
                          }

            # Append client
            self.clients.append(new_client)

        # Sort clients
        self.clients.sort(key=itemgetter('total_mbytes'), reverse=True)

        # Return True
        return True

    def graph_uplink_loss_and_latency(self, date, ip, timespan, uplink):
        '''
        :return:
        '''
        # List of graphs
        graphs = []
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
            return graphs

        # Set first time of 1
        time = 1
        times = []
        latency_values = []

        # Build loop through list for calculations
        for sample in samples:
            # Check for max loss
            sample['time'] = time
            times.append(time)
            latency_values.append(sample.get('latencyMs'))
            time += 1

        plt.plot(times, latency_values)
        file_name = "{}_{}_latency.png".format(date, self.name)
        plt.savefig(file_name)
        graphs.append(file_name)

        # Return True
        return graphs

#########################################################################
# Class Meraki_Dashboard_Client
#
# Class used to operate client and return data for use in errbot
#########################################################################
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
            self._get_inventory(orgs)
            return_val = True
        except:
            return_val = False

        # Return return_val
        return return_val


    def _get_inventory(self, orgs):
        # For each org in list, build an org data structure
        for org in orgs:
            new_org = Organization(str(org.get('id')), org.get('name'), self.headers)
            self.organizations.append(new_org)
            new_org.get_inventory()

        # Return None
        return None

    def get_uplink_loss_and_latency(self):
        # Set list of devices
        org_data = []
        # For each org in list, obtain device list
        for org in self.organizations:
            org_data.append(org.get_uplink_loss_and_latency('8.8.8.8', 86400, 'wan1'))

        # Return org_data
        return org_data

    def get_top_talkers(self, timespan=86400, count=0):
        # Set list of devices
        org_data = []
        # For each org in list, obtain device list
        for org in self.organizations:
            org_data.append(org.get_top_talkers(timespan, count))

        # Return org_data
        return org_data

    def graph_uplink_loss_and_latency(self, device_name=""):
        # Declare variables
        graphs = []
        # Check each network
        for org in self.organizations:
            graphs += org.graph_uplink_loss_and_latency(device_name, '8.8.8.8', 86400, 'wan1')

        return graphs