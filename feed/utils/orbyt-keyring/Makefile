include $(TOPDIR)/rules.mk

PKG_NAME:=orbyt-keyring
PKG_VERSION:=1
PKG_RELEASE:=2

PKG_MAINTAINER:=kiritantakechi <kiritantakechi@gmail.com>
PKG_LICENSE:=GPL-2.0-only

include $(INCLUDE_DIR)/package.mk

define Package/orbyt-keyring
  SECTION:=base
  CATEGORY:=Base system
  TITLE:=Release public keys of Orbyt
  PKGARCH:=all
endef

define Package/orbyt-keyring/description
  The trust anchors of the release build (r4s-release-pipeline D1): the release
  keys' public halves, for apk (/etc/apk/keys) and for firmware signatures
  (/etc/usign/keys, as usign and ucert read them). It replaces openwrt-keyring
  and holds more than one key of each during a key rotation.
endef

define Build/Compile
endef

# files/ mirrors the root filesystem; scripts/release-keys.sh adds the keys. A
# keyring without a key of each kind trusts nothing: its build fails.
define Package/orbyt-keyring/install
	$(INSTALL_DIR) $(1)/etc/apk/keys $(1)/etc/usign/keys
	ls ./files/etc/apk/keys/*.pem ./files/etc/usign/keys/* >/dev/null
	$(CP) ./files/. $(1)/
endef

$(eval $(call BuildPackage,orbyt-keyring))
