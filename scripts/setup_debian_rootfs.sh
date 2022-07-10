#! /bin/bash
# This script sets up the Debian root file system to boot from an encrypted OS partition.
# In details:
# * Configure crypttab to add a second key to the OS partition to make the kernel unlock
#   the partition by itself without requiring user input
# * Configure /etc/fstab to point to the correct devices
# * Regenerate Grub in removable so that the only unencrypted script just points to
#   the Grub scripts inside the encrypted partition
# * Update the initramfs to take the modifications to the config files into account.

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
LOOP_DEVICE_ID=""

usage()
{
    cat << USAGE >&2
Usage:
    $0 --loop-device LOOP_DEVICE_ID
    -d LOOP_DEVICE_ID | --loop-device-id=LOOP_DEVICE_ID   Device ID of the disk image.
USAGE
}

while test -n "$1"; do
  case "$1" in
  -d | --loop-device-id)
    LOOP_DEVICE_ID=$2
    shift
    ;;
  esac
  shift
done

if [ -z "${LOOP_DEVICE_ID}" ]; then
  usage
  exit 1
fi

# The original password of the OS partition. Must be provided by the caller of the script.
BOOT_KEY_FILE="${SCRIPT_DIR}/os_partition.key"

BOOT_PARTITION_DEVICE_ID="${LOOP_DEVICE_ID}p1"
OS_PARTITION_DEVICE_ID="${LOOP_DEVICE_ID}p2"

BOOT_PARTITION_UUID=$(blkid --match-tag=UUID --output=value "${BOOT_PARTITION_DEVICE_ID}" )
OS_PARTITION_UUID=$(blkid --match-tag=UUID --output=value "${OS_PARTITION_DEVICE_ID}" )

# Create key file to unlock the disk at boot
mkdir -p /etc/cryptsetup-keys.d
KEY_FILE="/etc/cryptsetup-keys.d/luks-${OS_PARTITION_UUID}.key"
dd if=/dev/urandom bs=1 count=33|base64 -w 0 > "${KEY_FILE}"
chmod 0600 "${KEY_FILE}"
cryptsetup \
  --key-slot 1 \
  --iter-time 1 \
  --key-file "${BOOT_KEY_FILE}" \
  luksAddKey "${OS_PARTITION_DEVICE_ID}" \
  "${KEY_FILE}"

# Tell the kernel to look for keys in /etc/cryptsetup-keys.d
echo "KEYFILE_PATTERN=\"/etc/cryptsetup-keys.d/*\"" >>/etc/cryptsetup-initramfs/conf-hook

# Reduce the accessibility of the initramfs
echo "UMASK=0077" >> /etc/initramfs-tools/initramfs.conf

# Configure Grub and crypttab
echo "GRUB_ENABLE_CRYPTODISK=y" >> /etc/default/grub
echo "cr_root UUID=${OS_PARTITION_UUID} ${KEY_FILE} luks" >> /etc/crypttab
cat << EOF > /etc/fstab
/dev/mapper/cr_root / ext4 rw,discard,errors=remount-ro 0 1
UUID=${BOOT_PARTITION_UUID} /boot/efi vfat defaults 0 0
EOF

# Install Grub and regenerate grub.cfg
mount /boot/efi
grub-install --target=x86_64-efi --removable
grub-install --target=x86_64-efi --recheck
grub-mkconfig -o /boot/grub/grub.cfg
umount /boot/efi

# Update initramfs after changes to fstab and crypttab
update-initramfs -u