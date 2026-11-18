include $(TOPDIR)/rules.mk

PKG_NAME:=orbyt-ab
PKG_VERSION:=1
PKG_RELEASE:=4

PKG_MAINTAINER:=kiritantakechi <kiritantakechi@gmail.com>
PKG_LICENSE:=GPL-2.0-only

include $(INCLUDE_DIR)/package.mk

define Package/orbyt-ab
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=A/B slots: upgrade, health check, slot switch
  DEPENDS:=@TARGET_rockchip +uboot-envtools +ucode +ucode-mod-fs +ucode-mod-ubus +ucode-mod-uci
  PKGARCH:=all
endef

define Package/orbyt-ab/description
  The Linux side of the A/B slots (r4s-ab-rollback): sysupgrade writes only the
  inactive slot and makes it the trial slot, orbyt-healthcheck confirms a trial
  slot or reboots it so that U-Boot can roll back, orbyt-trial reboots a trial
  boot still undecided at its deadline, and orbyt-slot shows the state or
  switches slots by hand.
endef

define Package/orbyt-ab/conffiles
/etc/config/orbyt-ab
endef

define Build/Compile
endef

define Package/orbyt-ab/install
	$(CP) ./files/* $(1)/
	$(INSTALL_DIR) $(1)/etc/healthcheck.d
endef

$(eval $(call BuildPackage,orbyt-ab))
