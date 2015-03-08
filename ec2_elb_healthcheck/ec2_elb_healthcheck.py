#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015 Riccardo Freixo

"""
Simple Ansible module to health check instances in an ELB
"""

DOCUMENTATION = '''
---
module: ec2_elb_healthcheck
version_added: "1.8"
short_description: Get instance Health Check state from ELBs
description:
    - Gets instance Health Check states from ELBs.
author: Riccardo Freixo
options:
  region:
    description:
      - The AWS region to use. If not specified then the value of the EC2_REGION environment variable, if any, is used.
    required: false
    aliases: ['aws_region', 'ec2_region']
  name:
    description:
      - The name of the ELB.
    required: true
  instances:
    description:
      - A list of instance IDs to get Health Check states from.
    required: false

extends_documentation_fragment: aws
'''

EXAMPLES = '''
# Check health of two instances attached to elb myelb
- ec2_elb_healthcheck:
    region: eu-west-1
    name: my-elb
    instances:
      - i-1157af42
      - i-b514da21

# Check health of all instances attached to elb myelb
- ec2_elb_healthcheck:
    region: eu-west-1
    name: my-elb
'''

import sys

try:
    import boto
    import boto.ec2
    import boto.ec2.elb
    import boto.ec2.elb.attributes
except ImportError:
    print "failed=True msg='boto required for this module'"
    sys.exit(1)

from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *


def check_instances_health(connection, elb, ids):
    """
    Returns a dict with the state of each instance in 'ids'.
    :type connection: :class:`boto.ec2.connection.EC2Connection`
    :param connection: a connection to ec2

    :type elb: str
    :param elb: the name of the ELB to health check.

    :type ids: list
    :param ids: a list of instance IDs to health check.

    :rtype: dict
    :return: Returns a dict with the state of each instance in 'ids'.
    """
    try:
        instances = connection.describe_instance_health(elb)
    except boto.exception.EC2ResponseError, error:
        module.fail_json(msg=str(error))

    healthcheck = {instance.instance_id: instance.state for instance in instances if instance.instance_id in ids}
    for instance_not_found in set(ids) - set(healthcheck.keys()):
        healthcheck[instance_not_found] = 'NotFound'
    instances_in_service = [k for k, v in healthcheck.iteritems() if v == 'InService']
    all_in_service = True if len(instances_in_service) == len(ids) else False

    return dict(
            all_in_service=all_in_service,
            instances=healthcheck
            )


def check_all_instances_health(connection, elb):
    """
    Returns a dict with the state of each instance attached to the ELB 'elb'.

    :type connection: :class:`boto.ec2.connection.EC2Connection`
    :param connection: a connection to ec2

    :type elb: str
    :param elb: the name of the ELB to health check.

    :rtype: dict
    :return: Returns a dict with the state of each instance attached to the ELB 'elb'.
    """
    try:
        instances = connection.describe_instance_health(elb)
    except boto.exception.EC2ResponseError, error:
        module.fail_json(msg=str(error))

    healthcheck = {instance.instance_id: instance.state for instance in instances}
    instances_in_service = [k for k, v in healthcheck.iteritems() if v == 'InService']
    all_in_service = True if len(instances_in_service) == len(instances) else False

    return dict(
            all_in_service=all_in_service,
            instances=healthcheck
            )


def main():
    """Main function"""
    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type='str', required=True),
            instances=dict(type='list')
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    region, ec2_url, aws_connect_params = get_aws_connection_info(module)
    try:
        connection = connect_to_aws(boto.ec2.elb, region, **aws_connect_params)
        if not connection:
            module.fail_json(msg="failed to connect to AWS for the given region: %s" % str(region))
    except boto.exception.NoAuthHandlerFound, error:
        module.fail_json(msg=str(error))

    name = module.params.get('name')
    instances = module.params.get('instances')

    if instances is not None:
        results = check_instances_health(connection, name, ids=instances)
    else:
        results = check_all_instances_health(connection, name)

    module.exit_json(
            changed=False,
            **results
            )

if __name__ == "__main__":
    main()
