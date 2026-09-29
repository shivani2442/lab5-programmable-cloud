#!/usr/bin/env python3

import os
import time
import googleapiclient.discovery
import google.oauth2.service_account

ZONE = "us-west1-b"
VM1_NAME = "lab5-part3-launcher"
MACHINE_TYPE = "e2-medium"
SERVICE_ACCOUNT_FILE = "service-credentials.json"

credentials = (
    google.oauth2.service_account
    .Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE
    )
)

project = credentials.project_id
compute = googleapiclient.discovery.build(
    "compute",
    "v1",
    credentials=credentials
)

with open("vm1-launch-vm2.py", "r") as f:
    vm2_launcher_code = f.read()
with open("vm2-startup-script.sh", "r") as f:
    vm2_startup_script = f.read()
with open(SERVICE_ACCOUNT_FILE, "r") as f:
    service_credentials = f.read()

vm1_startup_script = """#!/bin/bash

set -e

echo "Starting VM-1 setup..."

apt-get update
apt-get install -y python3 python3-pip

mkdir -p /srv

curl http://metadata/computeMetadata/v1/instance/attributes/vm2-startup-script \
    -H "Metadata-Flavor: Google" \
    > /srv/vm2-startup-script.sh

curl http://metadata/computeMetadata/v1/instance/attributes/service-credentials \
    -H "Metadata-Flavor: Google" \
    > /srv/service-credentials.json

curl http://metadata/computeMetadata/v1/instance/attributes/vm1-launch-vm2-code \
    -H "Metadata-Flavor: Google" \
    > /srv/vm1-launch-vm2.py

export GOOGLE_CLOUD_PROJECT=$(curl -s \
    http://metadata/computeMetadata/v1/project/project-id \
    -H "Metadata-Flavor: Google")

export GOOGLE_APPLICATION_CREDENTIALS=/srv/service-credentials.json

pip3 install --upgrade \
    google-api-python-client \
    google-auth \
    google-auth-httplib2 \
    google-auth-oauthlib

chmod +x /srv/vm1-launch-vm2.py

python3 /srv/vm1-launch-vm2.py \
    > /var/log/vm1-launch-vm2.log 2>&1

echo "VM-1 finished launching VM-2."
"""

def create_vm1():

    machine_type = (
        f"zones/{ZONE}/machineTypes/{MACHINE_TYPE}"
    )

    config = {

        "name": VM1_NAME,
        "machineType": machine_type,
        "metadata": {
            "items": [
                {
                    "key": "startup-script",
                    "value": vm1_startup_script
                },
                {
                    "key": "vm2-startup-script",
                    "value": vm2_startup_script
                },
                {
                    "key": "vm1-launch-vm2-code",
                    "value": vm2_launcher_code
                },
                {
                    "key": "service-credentials",
                    "value": service_credentials
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
                        "global/images/family/ubuntu-2204-lts"
                    )
                }
            }
        ],

        "networkInterfaces": [
            {
                "network": "global/networks/default",
                "accessConfigs": [
                    {
                        "type": "ONE_TO_ONE_NAT"
                    }
                ]
            }
        ]
    }

    print("=" * 60)
    print("CSCI 5253 - Lab 5 - Part 3")
    print("=" * 60)
    print(f"Project: {project}")
    print(f"Zone: {ZONE}")
    print(f"VM-1: {VM1_NAME}")
    print()
    print("Creating VM-1...")

    operation = compute.instances().insert(
        project=project,
        zone=ZONE,
        body=config
    ).execute()

    print("VM-1 creation request submitted.")

    return operation

def wait_for_operation(operation):

    print("Waiting for VM-1 creation to finish...")
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=ZONE,
            operation=operation["name"]
        ).execute()

        if result["status"] == "DONE":
            if "error" in result:
                raise RuntimeError(result["error"])
            print("VM-1 creation completed.")
            return
        time.sleep(2)

def get_external_ip():

    instance = compute.instances().get(
        project=project,
        zone=ZONE,
        instance=VM1_NAME
    ).execute()

    return (
        instance["networkInterfaces"][0]
        ["accessConfigs"][0]
        ["natIP"]
    )

def main():

    operation = create_vm1()
    wait_for_operation(operation)
    ip = get_external_ip()
    print()
    print("=" * 60)
    print("PART 3 - VM-1 CREATED")
    print("=" * 60)
    print(f"VM-1 external IP: {ip}")
    print()
    print("VM-1 will now launch VM-2 automatically.")
    print()
    print("SSH into VM-1 with:")
    print()
    print(
        f"gcloud compute ssh {VM1_NAME} "
        f"--zone={ZONE}"
    )
    print()
    print("After connecting, check:")
    print()
    print("ps aux | grep vm1-launch")
    print("cat /var/log/vm1-launch-vm2.log")


if __name__ == "__main__":
    main()