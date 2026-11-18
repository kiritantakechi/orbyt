include $(TOPDIR)/rules.mk

PKG_NAME:=orbyt-data
PKG_VERSION:=1
PKG_RELEASE:=2

PKG_MAINTAINER:=kiritantakechi <kiritantakechi@gmail.com>
PKG_LICENSE:=GPL-2.0-only

include $(INCLUDE_DIR)/package.mk

define Package/orbyt-data
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=The USB data disk: setup and daily read-only snapshots
  DEPENDS:=+btrfs-progs +block-mount +blockd +kmod-fs-btrfs
  PKGARCH:=all
endef

define Package/orbyt-data/description
  The data disk of r4s-services: orbyt-data init erases a USB disk into btrfs
  with the subvolumes containers, downloads, shares, logs and .snapshots, and
  mounts its top level at /mnt/data by UUID; orbyt-snap takes read-only
  snapshots of containers and shares daily and keeps seven days of them.
endef

define Build/Compile
endef

define Package/orbyt-data/install
	$(CP) ./files/* $(1)/
endef

$(eval $(call BuildPackage,orbyt-data))
