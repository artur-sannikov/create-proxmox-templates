# Create Proxmox templates with Python

A small script, which automatically creates virtual machine
templates for Proxmox.

It has some flexibility, but most settings are hardcoded and
adjusted for my homelab and Proxmox setup (e.g., I use ZFS).

It requires `requests` library, which is included in Proxmox's
Python.

Public SSH key(s) should be available on the Proxmox host.
You can specify path(s) to SSH key(s) with `--public-ssh-key-path`
parameter.

## Usage

```
usage: create_proxmox_templates.py [-h] [-u URL] [-p DOWNLOAD_LOCATION] [--vm-id VM_ID]
                                   [--public-ssh-key-path PUBLIC_SSH_KEY_PATH [PUBLIC_SSH_KEY_PATH ...]] [--docker | --no-docker]

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     Direct url to the image
  -p DOWNLOAD_LOCATION, --download-location DOWNLOAD_LOCATION
                        Download location for the image
  --vm-id VM_ID         VM ID in Proxmox. Must be unique
  --public-ssh-key-path PUBLIC_SSH_KEY_PATH [PUBLIC_SSH_KEY_PATH ...]
                        Path(s) to public SSH key(s) for cloud-init
  --docker, --no-docker
                        If specified, creates an Ubuntu VM template with pre-installed Docker.
```

For example,

```sh
python3 create_proxmox_templates.py \
    -u https://download.fedoraproject.org/pub/fedora/linux/releases/41/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-41-1.4.x86_64.qcow2 \
    -p /var/lib/vz/template/iso \
    --vm-id 999 --public-ssh-key-path ~/.ssh/mypublickey.pub
```

Will create a Fedora template VM with id 999.
