# Create Proxmox templates with Python

A small script, which automatically creates virtual machine
templates for Proxmox.

It has some flexibility, but most settings are hardcoded and
adjusted for my homelab and Proxmox setup (e.g., I use ZFS).

It requires `requests` library, which is included in Proxmox's
Python.

Public SSH key(s) should be available on the Proxmox host.
You can specify path(s) for SSH key(s) with `--public-ssh-key-path`
parameter.
