# luci-theme-orbyt: the image's own LuCI theme (luci-theme-orbyt D1): a sidebar of
# LuCI's menu, a top bar with the page's place, LuCI's indicators and a light/dark
# switch, and the page's sections as cards; light and dark by LuCI's data-darkmode.
# Builds on LuCI's luci.mk from the luci feed, as luci-app-honk does.

include $(TOPDIR)/rules.mk

PKG_MAINTAINER:=kiritantakechi <kiritantakechi@gmail.com>
PKG_LICENSE:=Apache-2.0

LUCI_TITLE:=orbyt theme
LUCI_DEPENDS:=+luci-base
LUCI_PKGARCH:=all
# The stylesheet ships as written: luci.mk minifies CSS with csstidy, whose
# CSS 2.1 rules do not know color-mix(), :is() or media features of today.
LUCI_MINIFY_CSS:=0

define Package/luci-theme-orbyt/postrm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || {
	uci -q delete luci.themes.Orbyt
	uci commit luci
}
endef

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature
