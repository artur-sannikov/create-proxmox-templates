import argparse
import getpass
import os
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

import requests


def download_image(url, download_location):
    """
    Download image from a URL to a specified location
    """

    # Create download path if does not exist
    os.makedirs(download_location, exist_ok=True)

    # Extract filename from URL
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)

    # Create final save path for the image
    save_path = os.path.join(download_location, filename)

    # If the file with the same name already exists, do not download again
    if os.path.exists(save_path):
        print(f"File already exists: {save_path}")
        return

    try:
        with requests.get(url, stream=True) as response:
            # Check for status
            response.raise_for_status()
            # Write file in chunks
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Image {filename} was downloaded to {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download file. {e}")
        sys.exit(1)


def write_cloudinit(filename, content, directory="/var/lib/vz/snippets"):
    """
    Write cloud-init configuration to a file.
    """

    # Create path
    path = os.path.join(directory, filename)

    # Create directory if does not exist
    os.makedirs(directory, exist_ok=True)

    # Write configuration
    with open(path, "w") as file:
        file.write(content)
    print(f"Cloud-init configuration written to {path}")


# Cloud-init configurations
generic_debian_config = f"""\
#cloud-config
packages:
  - qemu-guest-agent
runcmd:
  - systemctl start qemu-guest-agent
  - reboot
"""
ubuntu_docker_config = """\
#cloud-config
groups:
  - docker
system_info:
  default_user:
    groups: [docker]
packages:
  - qemu-guest-agent
  - ca-certificates
  - curl
runcmd:
  - systemctl start qemu-guest-agent
  - install -m 0755 -d /etc/apt/keyrings
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  - chmod a+r /etc/apt/keyrings/docker.asc
  - echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
  - apt-get update
  - apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  - reboot
"""
fedora_config = """\
#cloud-config
packages:
  - qemu-guest-agent
runcmd:
  - systemctl start qemu-guest-agent
  - reboot
"""


def create_template(url, vm_id, public_ssh_key_path, vm_image, docker):
    """
    Create template using Proxmox's `qm` commands.
    If docker is enabled, creates an Ubuntu VM template with pre-installed Docker.
    """

    # Parse url
    parsed_url = urlparse(url)

    # Extract OS type from the parse url
    os_type = os.path.basename(parsed_url.path).lower()

    # As user for password
    vm_password = getpass.getpass("Enter the password for VM: ")

    # Generate password hash
    hashed_vm_password = subprocess.check_output(
        ["openssl", "passwd", "-6", vm_password], text=True
    ).strip()

    # Common command for all VMs
    create_command = [
        "qm",
        "create",
        vm_id,
        "--ostype=l26",
        "--memory=1024",
        "--agent=1",
        "--cpu=host",
        "--socket=1",
        "--cores=1",
        "--vga=serial0",
        "--serial0=socket",
        "--net0",
        "virtio,bridge=vmbr0,tag=20",  # VLAN ID of my servers
    ]

    importdisk_command = ["qm", "importdisk", vm_id, vm_image, "local-zfs"]

    set_command = [
        "qm",
        "set",
        vm_id,
        "--scsihw=virtio-scsi-pci",
        f"--virtio0=local-zfs:vm-{vm_id}-disk-0,discard=on",  # I use local-zfs volume
        "--boot",
        "order=virtio0",
        "--scsi1=local-zfs:cloudinit",
        "--ciuser=artur",
        "--sshkeys",
        " ".join(public_ssh_key_path),
        "--cipassword",
        hashed_vm_password,
        "--ipconfig0",
        "ip=dhcp",
    ]

    template_command = ["qm", "template", vm_id]

    # Set command for Ubuntu machine
    if "noble" in os_type:
        if docker:
            set_command.extend(
                [
                    "--name=ubuntu-2404-cloudinit-docker-template",
                    "--cicustom",
                    "vendor=local:snippets/ubuntu-docker-cloudinit.yaml",
                    "--tags=ubuntu,cloudinit,docker",
                ]
            )
        else:
            set_command.extend(
                [
                    "--name=ubuntu-2404-cloudinit-template",  # When new Ubuntu comes out, it needs to be changed
                    "--cicustom",
                    "vendor=local:snippets/debian-cloudinit.yaml",
                    "--tags=ubuntu,cloudinit",
                ]
            )

    # Set command for Debian machine
    elif "debian" in os_type:
        if docker:
            print(
                "Debian with Docker not supported. Proceeding with normal Debian installation"
            )

        set_command.extend(
            [
                "--name=debian-bookworm-cloudinit-template",
                "--cicustom",
                "vendor=local:snippets/debian-cloudinit.yaml",
                "--tags debian,cloudinit",
            ]
        )

    # Set command for Fedora machine
    elif "fedora" in os_type:
        if docker:
            print(
                "Fedora with Docker not supported. Proceeding with normal Fedora installation"
            )

        set_command.extend(
            [
                "--name=fedora-41-cloudinit-template",
                "--cicustom",
                "vendor=local:snippets/fedora-cloudinit.yaml",
                "--tags=fedora,cloudinit",
            ]
        )

    # Create VMs with Python's subprocess
    try:
        print(f"Creating VM {vm_id}...")
        subprocess.run(create_command, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error creating VM: {e}")
        print("Error output:", e.stderr)
        sys.exit(1)

    try:
        print(f"Importing disk...")
        subprocess.run(importdisk_command, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error importing disk: {e}")
        print("Error output:", e.stderr)
        sys.exit(1)

    try:
        print("Configuring VM...")
        subprocess.run(set_command, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error configuring VM: {e}")
        print("Error output:", e.stderr)
        sys.exit(1)

    try:
        print("Creating template...")
        subprocess.run(template_command, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error creating template: {e}")
        print("Error output:", e.stderr)
        sys.exit(1)

    print(f"Template {vm_id} successfully created.")


def main():
    parser = argparse.ArgumentParser()

    # Add CLI arguments
    parser.add_argument("-u", "--url", help="Direct url to the image")
    parser.add_argument(
        "-p", "--download-location", help="Download location for the image"
    )
    parser.add_argument("--vm-id", help="VM ID in Proxmox. Must be unique")
    parser.add_argument(
        "--public-ssh-key-path",
        nargs="+",
        help="Path(s) to public SSH key(s) for cloud-init",
    )
    parser.add_argument(
        "--docker",
        action=argparse.BooleanOptionalAction,
        help="If specified, creates an Ubuntu VM template with pre-installed Docker.",
    )
    args = parser.parse_args()

    # Download the image
    download_image(args.url, args.download_location)

    # Write cloud-init configurations
    write_cloudinit(
        filename="debian-cloudinit.yaml",
        content=generic_debian_config,
    )
    write_cloudinit(
        filename="ubuntu-docker-cloudinit.yaml",
        content=ubuntu_docker_config,
    )
    write_cloudinit(
        filename="fedora-cloudinit.yaml",
        content=fedora_config,
    )

    # Get the filename to be used for VM image creation
    parsed_url = urlparse(args.url)
    filename = os.path.basename(parsed_url.path)

    # Create VM template
    create_template(
        url=args.url,
        vm_id=args.vm_id,
        vm_image=os.path.join(args.download_location, filename),
        public_ssh_key_path=args.public_ssh_key_path,
        docker=args.docker,
    )


if __name__ == "__main__":
    main()
