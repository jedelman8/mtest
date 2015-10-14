#!/usr/bin/env python

# Copyright 2015 Jason Edelman <jedelman8@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DOCUMENTATION = '''
---

module: cable_check
short_description: Checks current cabling against desired cable topology
description:
    - Checks and validates cabling
author: Jason Edelman (@jedelman8)
requirements:
    - NX-API 1.0
    - NX-OS 6.1(2)I3(1)
    - pycsco
notes:
    - While username and password are not required params, they are
      if you are not using the .netauth file.  .netauth file is recommended
      as it will clean up the each task in the playbook by not requiring
      the username and password params for every tasks.
    - Using the username and password params will override the .netauth file
options:
    desired:
        description:
            - File that documents the desired cabling topology
        required: true
        default: null
        choices: []
        aliases: []
    existing_file:
        description:
            - File that documents the existing neighboring/cabling topology
        required: false
        default: null
        choices: []
        aliases: []
    existing:
        description:
            - List of dictionaries that document existing neighboring topology
        required: false
        default: null
        choices: []
        aliases: []
'''

EXAMPLES = '''

'''

import yaml


def main():

    module = AnsibleModule(
        argument_spec=dict(
            desired=dict(required=True),
            existing_file=dict(),
            existing=dict(),
            hostname=dict(required=True)
        ),
        supports_check_mode=False,
        required_one_of=[['existing', 'existing_file']]

    )

    existing = module.params['existing']
    existing_file = module.params['existing_file']
    desired = module.params['desired']
    hostname = module.params['hostname']

    if existing_file:
        existing_cabling = yaml.load(open(existing_file)).get('cabling')
    elif existing:
        existing_cabling = existing

    des = yaml.load(open(desired)).get('cabling')

    desired_single = des.get(hostname)
    if not desired_single:
        module.fail_json(msg='hostname not found in desired cabling file or no neighbors defined',
                         hostname=hostname)

    errors = []

    desired_local_interfaces = [each.get('local_interface') for each in desired_single]

    existing_local_interfaces = [each.get('local_interface') for each in existing]

    interface_existing_but_not_documented_in_desired = list(set(existing_local_interfaces).difference(desired_local_interfaces))

    for link in desired_single:
        use_desired = True
        desired_local_interface = link.get('local_interface')
        desired_neighbor_interface = link.get('neighbor_interface')
        desired_neighbor = link.get('neighbor')
        for each in existing:
            status = None
            if each.get('local_interface') == desired_local_interface:
                existing_neighbor_interface = each.get('neighbor_interface')
                existing_neighbor = each.get('neighbor')
                existing_local_interface = each.get('local_interface')
                if existing_neighbor != desired_neighbor:
                    status = 'FAIL_001: NEIGHBORS DO NOT MATCH'
                elif desired_neighbor_interface != existing_neighbor_interface:
                    status = 'FAIL_002: NEIGHBOR INTERFACES DO NOT MATCH. '
                    status += 'CURRENT IS: ' + existing_neighbor_interface

                else:
                    status = 'OK'
            elif each.get('local_interface') in interface_existing_but_not_documented_in_desired:
                status = 'FAIL_004: NEIGHBOR FOUND IN EXISTING, BUT NOT FOUND IN DESIRED'
                index = interface_existing_but_not_documented_in_desired.index(each.get('local_interface'))
                interface_existing_but_not_documented_in_desired.pop(index)
                existing_neighbor_interface = each.get('neighbor_interface')
                existing_neighbor = each.get('neighbor')
                existing_local_interface = each.get('local_interface')
                use_desired = False

            if status and use_desired:
                err = dict(local_interface=desired_local_interface, neighbor=desired_neighbor, neighbor_interface=desired_neighbor_interface, status=status)
                errors.append(err)
            elif not use_desired:
                err = dict(local_interface=existing_local_interface, neighbor=existing_neighbor, neighbor_interface=existing_neighbor_interface, status=status)
                errors.append(err)
            use_desired = True

        if desired_local_interface not in existing_local_interfaces:
            status = 'FAIL_003: NEIGHBOR DOCUMENTED IN DESIRED, BUT NOT FOUND IN EXISTING'
            err = dict(local_interface=desired_local_interface, neighbor=desired_neighbor, neighbor_interface=desired_neighbor_interface, status=status)
            errors.append(err)

    results = {}
    results['desired'] = yaml.load(open(desired)).get('cabling')
    results['existing'] = existing_cabling
    results['result'] = errors

    module.exit_json(**results)

from ansible.module_utils.basic import *
main()
