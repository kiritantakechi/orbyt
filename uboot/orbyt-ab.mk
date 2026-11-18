# Build glue of the A/B U-Boot (r4s-ab-rollback design D3, board-model D3):
# uboot-rockchip builds the U-Boot of every board with it, uboot-orbyt-qemu the
# emulator's. The tree links this directory in as env/uboot. uboot-rockchip
# includes it after its variants' definitions, which it extends.

ORBYT_AB_DIR := $(TOPDIR)/env/uboot

# The boards, each as <U-Boot variant>:<board id>:<environment directory in the
# U-Boot tree> (scripts/lib/boards.sh writes them from boards/*.json).
include $(TOPDIR)/env/orbyt-boards.mk

# OrbytAB/config <board>: the configuration fragments after the defconfig in
# UBOOT_CONFIG.
OrbytAB/config = orbyt-ab board-$(1)

# OrbytAB/Build <board>,<environment directory in the U-Boot tree>: build the
# package's variant with the slot logic. Preparing it puts the fragments where
# U-Boot finds them, and writes the board constants followed by the shared
# logic as the variant's default environment, orbyt.env (ENV_SOURCE_FILE).
define OrbytAB/Build
PKG_FILE_DEPENDS += $(ORBYT_AB_DIR)/

define Build/Prepare
	$$(call Build/Prepare/Default)
	$$(INSTALL_DIR) $$(PKG_BUILD_DIR)/board/orbyt
	$$(CP) $(ORBYT_AB_DIR)/orbyt-ab.config $(ORBYT_AB_DIR)/board-$(1).config $$(PKG_BUILD_DIR)/board/orbyt/
	cat $(ORBYT_AB_DIR)/board-$(1).env $(ORBYT_AB_DIR)/orbyt-ab.env >$$(PKG_BUILD_DIR)/$(2)/orbyt.env
endef
endef

define OrbytAB/newline


endef

# A board's variant: its definition gains the fragments, on a line of their own
# after its last, and the package the slot logic.
ORBYT_AB_BOARD := $(subst :, ,$(filter $(BUILD_VARIANT):%,$(ORBYT_AB_BOARDS)))
ifneq ($(ORBYT_AB_BOARD),)
ORBYT_AB_CONFIG := $(call OrbytAB/config,$(word 2,$(ORBYT_AB_BOARD)))
U-Boot/$(BUILD_VARIANT) += $(OrbytAB/newline)UBOOT_CONFIG += $(ORBYT_AB_CONFIG)
$(eval $(call OrbytAB/Build,$(word 2,$(ORBYT_AB_BOARD)),$(word 3,$(ORBYT_AB_BOARD))))
endif
