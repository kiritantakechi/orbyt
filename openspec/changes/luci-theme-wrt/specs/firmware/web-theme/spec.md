# Spec Delta

## Purpose
Defines how the web interface looks and behaves across devices: the image's own LuCI theme as the default, light and dark modes, phone-width use, coverage of every widget LuCI's applications use, and independence from anything outside the router.

## ADDED Requirements

### Requirement: The image's own theme by default
The image SHALL ship its own LuCI theme and use it as LuCI's theme on a fresh install, and on the first boot of an upgrade that brings it. Once it has been installed, an administrator's choice of theme SHALL survive upgrades. LuCI's stock theme SHALL stay installed and selectable.

#### Scenario: Fresh install
- **WHEN** a freshly installed router's management interface is opened
- **THEN** the page is drawn by the image's theme

#### Scenario: An upgrade that brings the theme
- **WHEN** a router whose configuration names the stock theme and does not know the image's theme boots an image that brings it
- **THEN** LuCI uses the image's theme

#### Scenario: An administrator's choice across an upgrade
- **WHEN** an administrator has chosen the stock theme and a configuration-preserving upgrade follows
- **THEN** LuCI still uses the stock theme

### Requirement: Light and dark
The theme SHALL follow the browser's light or dark preference, and SHALL let the user pin light or dark from every page; a pinned choice SHALL hold in that browser across pages and sessions. The dark mode SHALL be signalled the way LuCI's own modules read it, so that their pages turn dark with it.

#### Scenario: A browser that prefers dark
- **WHEN** a browser that prefers a dark color scheme opens a page, with nothing pinned
- **THEN** the page is dark, and LuCI's modules see dark mode

#### Scenario: Dark pinned in a light browser
- **WHEN** the user pins dark in a browser that prefers light, and opens another page
- **THEN** that page is dark too

### Requirement: Usable at phone width
At the width of a phone the theme SHALL keep every page usable: the menu SHALL open and close as a drawer, forms SHALL stack their labels over their fields, and only wide tables MAY scroll sideways, each within its own box, never the page.

#### Scenario: A page at phone width
- **WHEN** a page is opened in a browser 375 pixels wide
- **THEN** the menu is a drawer that opens and closes, and the page does not scroll sideways

### Requirement: Every widget styled
The theme SHALL style every widget LuCI's applications draw: every class that LuCI's stock theme styles SHALL be styled by it too, except where a reviewed list names a class with its reason.

#### Scenario: Compare with the stock theme
- **WHEN** the classes the stock theme's stylesheet styles are compared with the theme's
- **THEN** every class is styled by the theme or named in the reviewed list

### Requirement: Nothing from outside the router
The theme MUST NOT load anything from outside the router: no font, stylesheet, script or image from another host.

#### Scenario: The theme's files and pages
- **WHEN** the theme's files and the login page it serves are searched for references to other hosts
- **THEN** none is found
