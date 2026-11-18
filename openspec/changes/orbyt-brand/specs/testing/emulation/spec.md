# Spec Delta

## MODIFIED Requirements

### Requirement: Boot the shipped artifacts
The emulator SHALL boot the shipped factory image of a board itself, through the bootloader chain:
- the firmware is `uboot-orbyt-qemu`, built from the same U-Boot source and slot logic as the boards' bootloaders (firmware/boot-rollback);
- the boot disk is this image, attached as the board's kind of disk (an SD card or an eMMC) through an SD host controller, so U-Boot and Linux both see an MMC device and the U-Boot environment sits at the same offset as on the board;
- U-Boot selects the slot, loads that slot's kernel FIT and passes the kernel command line, as on the board.

The emulator MUST NOT use a separately built kernel or root filesystem, and MUST NOT pass a kernel or kernel command line to QEMU itself.

#### Scenario: Verify artifact provenance
- **WHEN** an emulation run starts
- **THEN**:
  - the log records the sha256 of the image and of the emulator's U-Boot, and they match the values in the build manifest;
  - the running kernel is the one in the current slot's kernel FIT;
  - its command line carries `orbyt.slot=a` and `fstools_overlay_compression_type=zstd`
