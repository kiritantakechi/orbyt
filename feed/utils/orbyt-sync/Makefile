include $(TOPDIR)/rules.mk

PKG_NAME:=orbyt-sync
PKG_VERSION:=1
PKG_RELEASE:=2

PKG_MAINTAINER:=kiritantakechi <kiritantakechi@gmail.com>
PKG_LICENSE:=GPL-2.0-only

include $(INCLUDE_DIR)/package.mk

define Package/orbyt-sync
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=Local repository of releases, and upgrades from it
  DEPENDS:=+orbyt-data +podman +flock +usign +ucert +ucode +ucode-mod-fs +ucode-mod-uclient +ucode-mod-uloop
  PKGARCH:=all
endef

define Package/orbyt-sync/description
  The device side of r4s-release-pipeline (D4): orbyt-sync fetches the newest
  release through a container on podman's network, so honk routes it like the
  LAN's traffic, into /mnt/data/repo, and activates it only once its signed
  manifest, its files and its package indexes verify. apk installs from that
  repository; orbyt-update upgrades to its image.
endef

define Package/orbyt-sync/conffiles
/etc/config/orbyt-sync
endef

define Build/Compile
endef

define Package/orbyt-sync/install
	$(CP) ./files/. $(1)/
endef

$(eval $(call BuildPackage,orbyt-sync))
