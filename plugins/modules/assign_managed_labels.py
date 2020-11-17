from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

DOCUMENTATION = r'''
---
module: respiro.illumio.assign_managed_labels

short_description: This is the module to assign labels to managed workloads from the csv file.

version_added: "1.0.0"

description: This module assigns labels to managed workloads. First the csv file is read and workloads from
csv file is compared to managed workloads in PCE and labels are assigned to those workloads.

options:
    user:
        description: This takes the user key value to access Illumio API
        required: true
        type: str
    password:
        description: This takes the user passkey to access Illumio API
        required: true
        type: str
    pce:
        description: This takes the url link to Illumio PCE
        required: true
        type: str
    org-href:
        description: This takes the organisation href for Illumio PCE
        required: true
        type: str
    workload:
        description: This takes the path to csv file contatining workload information
        required: true
        type: str

author:
    - Safal Khanal (@Safalkhanal)
'''

EXAMPLES = r'''
- name: Test with a message
  respiro.illumio.assign_managed_labels:
    user: "testusername"
    password: "testpassword"
    pce: "https://poc1.illum.io"
    org_href: "orgs/85"
    workload: 'workload.csv'
'''

RETURN = r'''
original_message:
    type: str
    returned: always
    sample: {
         "msg": {
            "changed": true,
            "failed": false,
            "labels_assigned": [
                "192.168.1.113"
            ],
            "not_assigned": [
                "19.16.1.111"
            ],
        }
    }
'''

from ansible.module_utils.compat.paramiko import paramiko
from ansible.module_utils.basic import AnsibleModule
import csv
import json
import requests
import aiohttp
import asyncio
from requests.auth import HTTPBasicAuth


def run_module():
    module_args = dict(
        workload=dict(type='str', required=True),
        user=dict(type='str', required=True),
        password=dict(type='str', required=True),
        pce=dict(type='str', required=True),
        org_href=dict(type='str', required=True),
    )
    result = dict()
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
    workload = module.params['workload']
    user = module.params["user"]
    password = module.params["password"]
    org_href = module.params["org_href"]
    pce = module.params["pce"]
    API = pce + "/api/v2/" + org_href + "/workloads?managed=true"
    labels_API = pce + "/api/v2/" + org_href + "/labels"
    list = {}
    list['assigned'] = []
    list['not_assigned'] = []

    if module.check_mode:
        module.exit_json(**result)

    # If the API data gets large(>500), async function is called
    async def async_api(api):
        async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(user, password)) as session:
            async with session.get(api) as resp:
                response = await resp.read()
        return response

    # Function to get the list of labels from PCE
    def display_labels():
        response = requests.get(labels_API, auth=HTTPBasicAuth(user, password))
        if len(response.content) == 500:
            response = async_api(labels_API)
        obj = json.loads(response.content)
        labels = dict()
        labels['role'] = dict()
        labels['app'] = dict()
        labels['env'] = dict()
        labels['loc'] = dict()
        for label_data in obj:
            if label_data['key'] == "role":
                labels['role'][label_data['value']] = label_data['href']
            if label_data['key'] == "app":
                labels['app'][label_data['value']] = label_data['href']
            if label_data['key'] == "env":
                labels['env'][label_data['value']] = label_data['href']
            if label_data['key'] == "loc":
                labels['loc'][label_data['value']] = label_data['href']
        return labels

    # Function to add labels to PCE
    def create_label(type, name):
        return requests.post(labels_API, auth=HTTPBasicAuth(user, password),
                             data=json.dumps({"key": type, "value": name})).content

    # Main code: Checks csv file and compares labels in pce and labels in csv file, and assign labels to worloads
    labels_details = display_labels()
    # getting data from the csv file and do the required operations
    with open(workload, 'r') as details:
        workload_details = csv.DictReader(details, delimiter=",")
        for rows in workload_details:
            public_ip = rows["ip"]
            role = rows['role']
            app = rows['app']
            env = rows['env']
            loc = rows['loc']
            
            # Get managed workload
            response = requests.get(API, auth=HTTPBasicAuth(user, password))
            obj = json.loads(response.text)

            # Check if label already exists in PCE. If not add to PCE and get its href.
            if role is not None:
                if role in labels_details['role']:
                    role_href = labels_details['role'][role]
                else:
                    href = create_label("role", role)[0]
                    labels_details['role'][role] = href
                    role_href = href
            if app is not None:
                if app in labels_details['app']:
                    app_href = labels_details['app'][app]
                else:
                    href = create_label("app", app)[0]
                    labels_details['app'][app] = href
                    app_href = href
            if env is not None:
                if env in labels_details['env']:
                    env_href = labels_details['env'][env]
                else:
                    href = create_label("env", env)[0]
                    labels_details['env'][env] = href
                    env_href = href
            if loc is not None:
                if loc in labels_details['loc']:
                    loc_href = labels_details['loc'][loc]
                else:
                    href = create_label("loc", loc)[0]
                    labels_details['loc'][loc] = href
                    loc_href = href

            # check the managed workload with workload from csv file and assign labels
            check = 0
            for values in obj:
                for data in values['interfaces']:
                    if data['address'] == public_ip or values['public_ip'] == public_ip:
                        check = 1
                        label = []
                        if role_href:
                            label.append({"href": role_href})
                        if app_href:
                            label.append({"href": app_href})
                        if env_href:
                            label.append({"href": env_href})
                        if loc_href:
                            label.append({"href": loc_href})
                        uri = pce + "/api/v2" + values['href']
                        response = requests.put(uri, auth=HTTPBasicAuth(user, password),
                                                data=json.dumps({'labels': label}))
                        list['assigned'].append(public_ip)    
            if check==0:
                list['not_assigned'].append(public_ip)
        module.exit_json(changed=True, labels_assigned=list['assigned'], not_assigned=list['not_assigned'])


def main():
    run_module()


if __name__ == '__main__':
    main()
