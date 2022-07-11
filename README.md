# Confidential Computing CLI

A command-line interface to interact with 
the [confidential Compute Resource Node](https://github.com/aleph-im/confidential-computing-api) prototype.

This CLI tool interacts with a confidential CRN API to upload an encrypted VM image, go through
the AMD SEV launch sequence and start the VM. The end result is a virtual machine that is accessible
through SSH and is completely encrypted in RAM, making it inaccessible from the point of view
of the hypervisor.

## Requirements

To use this CLI tool, you need the following programs:

* Docker (to run SEV Tool)
* Qemu + KVM

## Create an encrypted VM image

The first step is to build an encrypted VM image. Logically, this step is separated in two parts:

1. Configure a Linux root filesystem to make it compatible with AMD SEV
2. Create an encrypted VM image based on this root filesystem.

The first step should be performed once per supported distribution, and will typically be performed
by Aleph maintainers. [This guide](./docs/guest-images.md) describes how to configure and extract
a root filesystem for Debian 11.

The second step must be performed by end users for each VM they want to create: they will choose
a password, add their SSH keys and possibly install additional applications.
At the time of writing, we only provide a simple demo script in this repository: `scripts/build_debian_image.sh`.
This script will create a 4GB disk image with an encrypted (LUKS1) OS partition and a custom boot 
partition for local testing (see next section).

### Launch the VM locally

We provide a simple means to test VM images locally. You will need a recent version of Qemu (>6.0), KVM 
and OVMF (a UEFI firmware for virtual machines). You will also need to enable virtualization support
in your BIOS.

> We advise to use the same version of Qemu as the one used on confidential CRNs. You can use the same
> [install script](https://github.com/aleph-im/confidential-computing-api/blob/main/tools/qemu/install_qemu.sh).
> To install KVM, simply search for "install kvm <your-distribution>", instructions are readily available
> online.

```shell
/usr/local/bin/qemu-system-x86_64 \
  -enable-kvm \
  -m 4096 \
  -boot menu=on \
  -bios /usr/share/ovmf/OVMF.fd \
  -drive format=raw,file=YOUR-IMAGE.img \
  -nic user,model=virtio \  # Enables network access
  -nographic -serial mon:stdio
```

The bootloader will ask you to enter your passphrase to unlock the disk and will then boot the OS.
You are then free to make any modification you like to the disk image.

> Note that the size of the disk image is limited to a few GB (4GB by default in our example).
> This is because the OS image will need to be uploaded to the CRN, and larger sizes make
> the upload harder. The expected flow for larger disk sizes is to add another disk through
> the CRN, encrypt it from within the VM and then download any large files you would need
> from within the VM.

## Launch a VM

Next, we will upload the image you created above on a confidential CRN.
At the moment, this requires:

* access to a confidential CRN (https://epyc.bearmetaldev.com is the only one so far)
* credentials.

> The commands below are bound to evolve rapidly in future versions. Some parameters are fixed
> at the moment:the VM will run with one core and 4GB of RAM, and the SEV policy must be 0x1.

> Launching a VM on a confidential CRN is an interactive process between the user and the CRN.
> Automatic VM launch is a tricky problem to solve in a decentralized environment: the user
> needs to delegate trust to a 3rd party entity to store his disk password and validate
> the launch process properly. This is technically achievable with the AMD SEV-SNP extension
> and the concept of Migration Agents.

First, allocate a VM:

```shell
crn-cli --server-url ${SERVER_URL} vm create
```

This will allocate a slot for a VM on the CRN. You will then receive a UUID to use as VM ID
for the next operations. 
The following commands will address the UUID you received as `${VM_ID}`.
At this stage nothing is running on the CRN, you just informed it that you want to create a virtual machine.

The next step is to generate certificates called the **Guest Owner certificates**. Communication
with the Security Processor of the CRN requires the establishment of an encrypted channel.
This channel is established by downloading the **platform certificates** and then generating
our own certificates to encrypt the communication. The next operations do exactly that:

```shell
crn-cli --server-url ${SERVER_URL} platform get-certificates
SEV_POLICY=0x1  # Default value
crn-cli --server-url ${SERVER_URL} vm upload-certificates ${VM_ID} ${SEV_POLICY}
```

Next, you will upload your VM image. The protocol we use requires the image to be compressed
to accelerate the upload. Note that the upload takes several minutes.

```shell
tar -czvf your-vm-image.tar.gz your-vm-image.img
crn-cli \
  --server-url ${SERVER_URL} \
  vm upload-image ${VM_ID} your-vm-image.tar.gz your-vm-image.img
```

With this, we are now ready to start the VM.
The process runs in several parts:

* Let the hypervisor (Qemu) provision the VM and preload the firmware
* Ask for a measurement of the VM memory to check that the hypervisor loaded the correct firmware
* Encrypt and inject the disk key to let the bootloader unlock the disk
* Launch the VM.

Using the CLI, we first notify the CRN to start the VM:

```shell
crn-cli --server-url ${SERVER_URL} vm start ${VM_ID}
```

We then ask the CRN for a measurement of the firmware, verify it and inject the disk decryption
key if the measurement corresponds to the firmware:

```shell
crn-cli --server-url ${SERVER_URL} vm inject-secret ${VM_ID} ${DISK_DECRYPTION_KEY}
```

Upon success, the tool will show an address and port to SSH into.
Wait 1-2 minutes for the VM to start, and you should be able to ssh into the VM:

```shell
ssh ${SERVER_HOSTNAME} -p ${SSH_PORT}
```
