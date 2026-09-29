#!/usr/bin/env python3

import argparse
import os
import time
from pprint import pprint
import googleapiclient.discovery
import google.auth

credentials, project = google.auth.default()
compute = googleapiclient.discovery.build(
    "compute",
    "v1",
    credentials=credentials
)

ZONE = "us-west1-b"
INSTANCE_NAME = "lab5-programmatic-vm"
MACHINE_TYPE = "e2-medium"
FIREWALL_NAME = "allow-5000"
NETWORK_TAG = "allow-5000"
STARTUP_SCRIPT = """#!/bin/bash

set -e

echo "Starting Flask installation..." > /var/log/flask-startup.log

apt-get update

apt-get install -y python3 python3-pip git

cd /opt

git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial

cd flask-tutorial

python3 setup.py install
pip3 install -e .
export FLASK_APP=flaskr
flask init-db
nohup flask run -h 0.0.0.0 > /var/log/flask.log 2>&1 &
echo "Flask installation completed." >> /var/log/flask-startup.log
"""

def wait_for_zone_operation(compute, project, zone, operation):
    print("Waiting for operation to finish...")

    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation["name"]
        ).execute()

        if result["status"] == "DONE":

            if "error" in result:
                raise RuntimeError(f"Google Cloud operation failed: {result['error']}")

            print("Operation completed successfully.")
            return

        time.sleep(2)

def wait_for_global_operation(compute, project, operation):
    print("Waiting for global operation to finish...")

    while True:
        result = compute.globalOperations().get(
            project=project,
            operation=operation["name"]
        ).execute()

        if result["status"] == "DONE":

            if "error" in result:
                raise RuntimeError(f"Google Cloud operation failed: {result['error']}")

            print("Operation completed successfully.")
            return

        time.sleep(2)

def firewall_exists(compute, project, firewall_name):

    try:
        compute.firewalls().get(
            project=project,
            firewall=firewall_name
        ).execute()

        return True

    except Exception:
        return False

def create_firewall(compute, project):

    if firewall_exists(compute, project, FIREWALL_NAME):

        print(f"Firewall rule '{FIREWALL_NAME}' already exists.")
        return

    print(f"Creating firewall rule '{FIREWALL_NAME}'...")

    firewall_body = {
        "name": FIREWALL_NAME,
        "network": "global/networks/default",
        "direction": "INGRESS",
        "priority": 1000,
        "sourceRanges": [
            "0.0.0.0/0"
        ],

        "allowed": [
            {
                "IPProtocol": "tcp",
                "ports": [
                    "5000"
                ]
            }
        ],

        "targetTags": [
            NETWORK_TAG
        ]
    }

    operation = compute.firewalls().insert(
        project=project,
        body=firewall_body
    ).execute()

    wait_for_global_operation(
        compute,
        project,
        operation
    )

    print("Firewall rule created.")

def create_instance(
    compute,
    project,
    zone,
    instance_name
):

    machine_type = (f"zones/{zone}/machineTypes/{MACHINE_TYPE}")

    config = {

        "name": instance_name,

        "machineType": machine_type,
        "metadata": {
            "items": [
                {
                    "key": "startup-script",
                    "value": STARTUP_SCRIPT
                }
            ]
        },

        "disks": [
            {
                "boot": True,

                "autoDelete": True,

                "initializeParams": {
                    "sourceImage": (
                        "projects/ubuntu-os-cloud/"
                        "global/images/family/"
                        "ubuntu-2204-lts"
                    )
                }
            }
        ],

        "networkInterfaces": [
            {
                "network": (
                    "global/networks/default"
                ),

                "accessConfigs": [
                    {
                        "type": "ONE_TO_ONE_NAT"
                    }
                ]
            }
        ]
    }

    print()
    print(f"Creating VM '{instance_name}'...")

    operation = compute.instances().insert(
        project=project,
        zone=zone,
        body=config
    ).execute()

    print("VM creation request submitted.")
    return operation

def add_network_tag(
    compute,
    project,
    zone,
    instance_name
):

    print()
    print(f"Applying network tag '{NETWORK_TAG}'...")

    instance = compute.instances().get(
        project=project,
        zone=zone,
        instance=instance_name
    ).execute()

    current_tags = instance.get("tags", {})
    fingerprint = current_tags.get("fingerprint")

    tags = {
        "items": [
            NETWORK_TAG
        ],
        "fingerprint": fingerprint
    }

    operation = compute.instances().setTags(
        project=project,
        zone=zone,
        instance=instance_name,
        body=tags
    ).execute()

    wait_for_zone_operation(
        compute,
        project,
        zone,
        operation
    )
    updated_instance = compute.instances().get(
        project=project,
        zone=zone,
        instance=instance_name
    ).execute()

    final_tags = (
        updated_instance
        .get("tags", {})
        .get("items", [])
    )
    print(f"VM network tags: {final_tags}")

    if NETWORK_TAG not in final_tags:
        raise RuntimeError(
            "Network tag was not applied successfully."
        )
    print("Network tag applied successfully.")

def get_external_ip(
    compute,
    project,
    zone,
    instance_name
):

    print()
    print("Retrieving VM external IP...")
    instance = compute.instances().get(
        project=project,
        zone=zone,
        instance=instance_name
    ).execute()

    network_interfaces = (
        instance.get("networkInterfaces", [])
    )

    if not network_interfaces:
        raise RuntimeError(
            "VM has no network interfaces."
        )

    access_configs = (
        network_interfaces[0]
        .get("accessConfigs", [])
    )

    for access_config in access_configs:

        if access_config.get("type") == "ONE_TO_ONE_NAT":
            external_ip = access_config.get("natIP")
            if external_ip:
                return external_ip

    raise RuntimeError("Could not find an external IP address.")

def main():

    print("=" * 60)
    print("CSCI 5253 - Lab 5 - Part 1")
    print("=" * 60)
    print()
    print(f"Project: {project}")
    print(f"Zone: {ZONE}")
    print(f"VM: {INSTANCE_NAME}")
    print(f"Machine type: {MACHINE_TYPE}")

    create_firewall(
        compute,
        project
    )

    operation = create_instance(
        compute,
        project,
        ZONE,
        INSTANCE_NAME
    )

    wait_for_zone_operation(
        compute,
        project,
        ZONE,
        operation
    )

    add_network_tag(
        compute,
        project,
        ZONE,
        INSTANCE_NAME
    )

    external_ip = get_external_ip(
        compute,
        project,
        ZONE,
        INSTANCE_NAME
    )

    print()
    print("=" * 60)
    print("PART 1 COMPLETE")
    print("=" * 60)
    print()
    print("The Flask application will be available at:")
    print()
    print(f"http://{external_ip}:5000")
    print()
    print(
        "Note: The startup script may take a few minutes "
        "to finish installing Flask."
    )


if __name__ == "__main__":
    main()