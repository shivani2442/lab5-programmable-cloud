#!/usr/bin/env python3

import argparse
import os
import time
from pprint import pprint
import googleapiclient.discovery
import google.auth

ZONE = "us-west1-b"
SOURCE_INSTANCE = "lab5-programmatic-vm"
SNAPSHOT_NAME = f"base-snapshot-{SOURCE_INSTANCE}"
MACHINE_TYPE = "e2-medium"
NEW_INSTANCES = [
    "lab5-clone-1",
    "lab5-clone-2",
    "lab5-clone-3",
]

credentials, project = google.auth.default()

compute = googleapiclient.discovery.build(
    "compute",
    "v1",
    credentials=credentials
)

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

def get_boot_disk(compute, project, zone, instance_name):

    instance = compute.instances().get(
        project=project,
        zone=zone,
        instance=instance_name
    ).execute()

    for disk in instance["disks"]:

        if disk.get("boot", False):

            source = disk["source"]

            disk_name = source.split("/")[-1]

            return disk_name

    raise RuntimeError(
        f"Could not find boot disk for {instance_name}"
    )

def create_snapshot(compute, project, zone, disk_name):

    print()
    print("=" * 60)
    print("Creating snapshot")
    print("=" * 60)
    print(f"Source disk: {disk_name}")
    print(f"Snapshot: {SNAPSHOT_NAME}")

    snapshot_body = {
        "name": SNAPSHOT_NAME
    }

    operation = compute.disks().createSnapshot(
        project=project,
        zone=zone,
        disk=disk_name,
        body=snapshot_body
    ).execute()

    wait_for_zone_operation(
        compute,
        project,
        zone,
        operation
    )

    print(f"Snapshot '{SNAPSHOT_NAME}' created successfully.")

def create_instance_from_snapshot(
    compute,
    project,
    zone,
    instance_name
):

    print()
    print(f"Creating VM: {instance_name}")
    disk_config = {
        "boot": True,
        "autoDelete": True,
        "initializeParams": {
            "sourceSnapshot": (
                f"projects/{project}/global/snapshots/"
                f"{SNAPSHOT_NAME}"
            )
        }
    }

    config = {
        "name": instance_name,

        "machineType": (
            f"zones/{zone}/machineTypes/{MACHINE_TYPE}"
        ),

        "disks": [
            disk_config
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

    start_time = time.perf_counter()

    operation = compute.instances().insert(
        project=project,
        zone=zone,
        body=config
    ).execute()

    wait_for_zone_operation(
        compute,
        project,
        zone,
        operation
    )

    end_time = time.perf_counter()

    elapsed = end_time - start_time

    print(
        f"{instance_name} created in "
        f"{elapsed:.2f} seconds."
    )

    return elapsed

def main():

    print("=" * 60)
    print("CSCI 5253 - Lab 5 - Part 2")
    print("=" * 60)
    print(f"Project: {project}")
    print(f"Zone: {ZONE}")
    print(f"Source VM: {SOURCE_INSTANCE}")
    print(f"Snapshot: {SNAPSHOT_NAME}")
    print()
    print("Finding source VM boot disk...")

    disk_name = get_boot_disk(
        compute,
        project,
        ZONE,
        SOURCE_INSTANCE
    )
    print(f"Boot disk found: {disk_name}")
    create_snapshot(
        compute,
        project,
        ZONE,
        disk_name
    )
    print()
    print("=" * 60)
    print("Creating three VMs from snapshot")
    print("=" * 60)

    timings = {}

    for instance_name in NEW_INSTANCES:
        elapsed = create_instance_from_snapshot(
            compute,
            project,
            ZONE,
            instance_name
        )
        timings[instance_name] = elapsed

    print()
    print("=" * 60)
    print("PART 2 COMPLETE")
    print("=" * 60)
    print()
    print("VM creation times:")

    for instance_name, elapsed in timings.items():
        print(
            f"{instance_name}: "
            f"{elapsed:.2f} seconds"
        )

    with open("TIMING.md", "w") as file:

        file.write("# Part 2 VM Creation Timing\n\n")
        file.write(f"Source VM: `{SOURCE_INSTANCE}`\n\n")
        file.write(f"Snapshot: `{SNAPSHOT_NAME}`\n\n")
        file.write("| Instance | Creation Time |\n")
        file.write("|---|---:|\n")
        for instance_name, elapsed in timings.items():
            file.write(
                f"| `{instance_name}` | "
                f"{elapsed:.2f} seconds |\n"
            )
    print()
    print("TIMING.md created successfully.")

if __name__ == "__main__":
    main()