# How to build guest images

This guide is intended for Aleph developers aiming at supporting a new distribution
for confidential VMs. The goal here is, for any distribution, to install packages required 
to support full disk encryption, to extract the root file system of the image and then
provide it to users as a tarball. Users can then use this tarball to generate their own
OS image.

Theoretically, users can build encrypted images for any Linux distribution.
The only requirements are:

* GRUB EFI tools
* `cryptsetup`.

## Debian

The Debian "nocloud" images contain most of the tools needed, except for cryptsetup.
Debian provides images in the `qcow2` format, i.e. images that can be loaded directly
in Qemu. To configure the VM image, we will start the image, log into the VM,
install a new kernel, install cryptsetup and fix a few settings.
Then, we will extract the root file system to a tarball for later use.

### 1. Download an image

Any "nocloud" Debian image will do. As an example:

```shell
curl https://cloud.debian.org/images/cloud/bullseye/20220613-1045/debian-11-nocloud-amd64-20220613-1045.qcow2
```

### 2. Start the VM with Qemu

```shell
qemu-system-x86_64 \
  -drive format=qcow2,file=debian-11-nocloud-amd64-20220613-1045.qcow2 \
  -enable-kvm \
  -m 2048 \
  -nic user,model=virtio \
  -nographic \
  -serial mon:stdio
```

If the boot is successful, a login prompt will appear in the terminal.
Debian provides a password-less root user by default, so simply
log in as `root`.

### 3. Install a newer kernel

There is an issue with Linux 5.10 and SEV guests that causes the kernel to panic during the early boot
sequence, causing the VM to reboot (without any kernel log). This issue can be resolved by upgrading
the kernel to a new version. Run the following commands:

```shell
apt-cache search linux-image
apt install linux-image-5.18.0-0.bpo.1-cloud-amd64
reboot

# Remove the old kernel
apt remove --purge linux-image-5.10.0-15-amd64 # or whatever kernel was installed beforehand
update-grub2
reboot

# Check that the image still boots and runs the expected kernel
uname -r    # Should print 5.18.0-0.bpo.1-cloud-amd64
```

> Note that we use Linux 5.18 in this example, but any version above will probably do the trick.
> We tested 5.18 and know it to work.

### 4. Install cryptsetup

```shell
apt update
apt install cryptsetup guestmount
```

You can then halt the VM and exit Qemu (Ctrl-A, then X).

### 5. Properly configure sshd

Debian 11 sshd will fail to run normally out of the box. To fix this, simply regenerate
the system host keys with:

```shell
ssh-keygen -A
```

### 6. Extract the root filesystem

The easiest way to provide the base image to users is to extract the root file system
as a tarball. To do so, we simply need to mount the raw image with `guestmount`.

> Make sure that you stop the VM before exporting the root filesystem.

```shell
sudo mkdir -p /mnt/debian
sudo guestmount \
  --format=qcow2 \
  -a ./debian-11-nocloud-amd64-20220613-1045.qcow2 \
  -o allow_other \
  -i /mnt/debian
```

Then, you can simply copy the root file system to any directory, set your own user
as the owner of the directory and then compress it.

```shell
ROOT_DIR=debian-11-nocloud-amd64-20220613-1045+cryptsetup
mkdir ${ROOT_DIR}
sudo cp -R /mnt/debian/* ${ROOT_DIR}
sudo chown -R ${USER}:${USER} ${ROOT_DIR}
tar -czvf ${ROOT_DIR}.tar.gz ${ROOT_DIR}
```
