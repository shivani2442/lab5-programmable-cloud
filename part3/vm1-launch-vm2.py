#!/usr/bin/env python3

import os
import time

import googleapiclient.discovery
import google.oauth2.service_account


PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
ZONE = "us-west1-b"
VM2_NAME = "lab5-part3-flask"
MACHINE_TYPE = "e2-medium"

def wait_for_operation(compute, operation):
    print("Waiting for VM-2 creation to finish...")
    while True:
        result = compute.zoneOperations().get(
            project=PROJECT,
            zone=ZONE,
            operation=operation["name"]
        ).execute()

        if result["status"] == "DONE":
            if "error" in result:
                raise RuntimeError(result["error"])
            print("VM-2 creation completed.")
            return
        time.sleep(2)

def create_vm2(compute):

    print(f"Creating VM-2: {VM2_NAME}")
    with open("/srv/vm2-startup-script.sh", "r") as f:
        startup_script = f.read()

    machine_type = (
        f"zones/{ZONE}/machineTypes/{MACHINE_TYPE}"
    )

    config = {
        "name": VM2_NAME,
        "machineType": machine_type,
        "metadata": {
            "items": [
                {
                    "key": "startup-script",
                    "value": startup_script
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

    operation = compute.instances().insert(
        project=PROJECT,
        zone=ZONE,
        body=config
    ).execute()
    print("VM-2 creation request submitted.")
    wait_for_operation(compute, operation)

def add_network_tag(compute):
    print(f"Applying network tag to {VM2_NAME}...")
    instance = compute.instances().get(
        project=PROJECT,
        zone=ZONE,
        instance=VM2_NAME
    ).execute()

    current_tags = instance.get("tags", {})
    fingerprint = current_tags.get("fingerprint")
    tags = {
        "items": ["allow-5000"],
        "fingerprint": fingerprint
    }
    operation = compute.instances().setTags(
        project=PROJECT,
        zone=ZONE,
        instance=VM2_NAME,
        body=tags
    ).execute()

    while True:
        result = compute.zoneOperations().get(
            project=PROJECT,
            zone=ZONE,
            operation=operation["name"]
        ).execute()
        if result["status"] == "DONE":
            if "error" in result:
                raise RuntimeError(result["error"])
            print("Network tag applied.")
            return
        time.sleep(2)

def main():

    print("VM-1 is launching VM-2...")
    credentials = (
        google.oauth2.service_account
        .Credentials.from_service_account_file(
            "/srv/service-credentials.json"
        )
    )
    compute = googleapiclient.discovery.build(
        "compute",
        "v1",
        credentials=credentials
    )
    create_vm2(compute)
    add_network_tag(compute)
    print("VM-2 launched successfully.")

if __name__ == "__main__":
    main()