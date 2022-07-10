#! /bin/bash

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DEBIAN_ROOT_DIR="/home/odesenfans/git/odesenfans/sandbox/qemu/basic_tests/debian-11-nocloud-amd64-linux-5.18+cryptsetup/"

IMAGE_FILE="debian-11-linux-5.18.img"
IMAGE_SIZE=4GB
BOOT_PARTITION_SIZE=100MiB

KEY_FILE="${SCRIPT_DIR}/os_partition.key"

truncate -s "${IMAGE_SIZE}" "${IMAGE_FILE}"

# Create two partitions: a FAT32 boot partition for Grub and an ext4 partition for Debian
# TODO: is there a way to do all this without sudo?
echo "Creating partitions..."
sudo parted "${IMAGE_FILE}" mklabel gpt
sudo parted "${IMAGE_FILE}" mkpart primary 1Mib "${BOOT_PARTITION_SIZE}"
sudo parted "${IMAGE_FILE}" mkpart primary "${BOOT_PARTITION_SIZE}" 100%

# Mark partition 1 as boot+ESP
sudo parted "${IMAGE_FILE}" set 1 esp on
sudo parted "${IMAGE_FILE}" set 1 boot on

# Mount the disk as a loop device and get the device ID
LOOP_DEVICE_ID=$(sudo losetup --partscan --find --show "${IMAGE_FILE}")
BOOT_PARTITION_DEVICE_ID="${LOOP_DEVICE_ID}p1"
OS_PARTITION_DEVICE_ID="${LOOP_DEVICE_ID}p2"

# Format the boot partition
echo "Formatting the boot partition..."
sudo mkfs.vfat "${BOOT_PARTITION_DEVICE_ID}"

echo "Encrypting and formatting the OS partition..."
MAPPER_NAME=cr_root
MAPPED_DEVICE_ID="/dev/mapper/${MAPPER_NAME}"
MOUNT_POINT="/mnt/cr_root"
echo -n "verysecure" > "${KEY_FILE}"

sudo cryptsetup --batch-mode --type luks1 --key-file "${KEY_FILE}" luksFormat "${OS_PARTITION_DEVICE_ID}"
sudo cryptsetup open --key-file "${KEY_FILE}" "${OS_PARTITION_DEVICE_ID}" "${MAPPER_NAME}"
sudo mkfs.ext4 "${MAPPED_DEVICE_ID}"

echo "Copying root file system to the new OS partition..."
sudo mount "${MAPPED_DEVICE_ID}" "${MOUNT_POINT}"
sudo cp -R "${DEBIAN_ROOT_DIR}"/* "${MOUNT_POINT}"

echo "Configuring root file system..."
for m in run sys proc dev; do sudo  mount --bind /$m ${MOUNT_POINT}/$m; done
sudo cp "${SCRIPT_DIR}/setup_debian_rootfs.sh" "${KEY_FILE}" "${MOUNT_POINT}"
sudo chroot "${MOUNT_POINT}" bash setup_debian_rootfs.sh --loop-device-id "${LOOP_DEVICE_ID}"
sudo rm "${MOUNT_POINT}/setup_debian_rootfs.sh" "${KEY_FILE}"

echo "Cleaning up..."
sudo umount --recursive "${MOUNT_POINT}"
sudo cryptsetup close "${MAPPED_DEVICE_ID}"
sudo losetup -d "${LOOP_DEVICE_ID}"

echo "Done! The new image is available as ${IMAGE_FILE}."
