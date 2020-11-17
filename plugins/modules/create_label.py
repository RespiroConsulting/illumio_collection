from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

DOCUMENTATION = r'''
---
module: respiro.illumio.create_labels

short_description: This module adds labels to PCE

version_added: "1.0.7"

description: This module contains two approaches to add labels to PCE. One is to pass argument as name and type of label
and the other approach is to pass the path of csv file containing the list of new labels.

options:
    name:
        description: This is the name of the label.
        required: true
        type: str
    type:
        description: This is the type of label
        required: true
        type: str
    path:
        description: This takes the path of csv file containing the list of labels
        required: true
        type: str
    user:
        description: This takes the user key value to access Illumio API. Generate the API key from PCE and place the Authentication Username here.
        required: true
        type: str
    password:
        description: This takes the user passkey to access Illumio API. From API key, place the Secret value here
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

author:
    - Safal Khanal (@safalkhanal)
'''

EXAMPLES = r'''
# Pass in a path
- name: Test the module with csv path
  respiro.illumio.create_label:
    user: testuser
    password: testpass
    pce: pce_url
    org_href: org_href
    path: "labels.csv"

# pass in single label information
- name: Test with a single label information
  respiro.illumio.create_label:
    user: "testuser"
    password: "testpass"
    pce: "pce_url"
    org_href: "org_href"
    name: "test_application"
    type: "app"
# fail the module
- name: Test failure of the module
  respiro.illumio.create_label:
    user: "testuser"
    password: "testpass"
    pce: "pce_url"
    org_href: "org_href"
    name: "test_application"
    type: "ap"
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
error:
    description: List of label that module was not able to add to PCE.
    type: list
    returned: always
    sample:  [
            "Invalid type:ap. Type should be either env,app,loc,role"
        ],

success:
    description: List of label that module was able to add to PCE.
    type: list
    returned: always
    sample:  [
            "app : new_app3"
        ],
'''


from ansible.module_utils.basic import AnsibleModule
import json
import csv
import requests
from requests.auth import HTTPBasicAuth


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        name=dict(type='str', required=False),
        type=dict(type='str', required=False),
        path=dict(type='str', required=False),
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
    l_name = module.params['name']
    l_type = module.params['type']
    l_path = module.params['path']
    login = module.params["user"]
    password = module.params["password"]
    org_href = module.params["org_href"]
    pce = module.params["pce"]
    API = pce + "/api/v2/" + org_href + "/labels"

    if module.check_mode:
        module.exit_json(**result)
    list = {"success": [], "error": []}
    try:
        if l_path:
            with open(l_path, 'r') as data_file:
                label_value = csv.DictReader(data_file, delimiter=",")
                for rows in label_value:
                    key = rows["type"]
                    value = rows["name"]
                    if key == 'loc' or key == 'env' or key == 'role' or key == 'app':
                        response = requests.post(API, auth=HTTPBasicAuth(login, password), data=json.dumps({"key": key, "value": value}))
                        list["success"].append(key + " : " + value)
                    else:
                        list["error"].append("Invalid type:" + key + ". Type should be either env,app,loc,role")
        elif l_type and l_name:
            if l_type == 'env' or l_type == 'loc' or l_type == 'app' or l_type == 'role':
                y = {"key": l_type, "value": l_name}
                list["success"].append(l_type + " : " + l_name)
                response = requests.post(API, auth=HTTPBasicAuth(login, password), data=json.dumps({"key": l_type, "value": l_name}))
            else:
                module.exit_json(msg="Invalid type value.", failed=l_type)
        else:
            module.exit_json(msg="Parameter mismatch.")
        module.exit_json(error=list["error"], success=list["success"])
    except Exception as e:
        module.fail_json(msg="Error!!")


def main():
    run_module()


if __name__ == '__main__':
    main()
