'use strict';
'require baseclass';
'require ui';

// luci-theme-orbyt's menu (orbyt-theme D2): the mode's first
// level as the sidebar's groups of text entries, the third level as tabs, the
// page's place as a breadcrumb above the content and logout in the header; the
// drawer below 1024 pixels, and the light/dark switch, in the header and in the
// drawer's foot.

return baseclass.extend({
	__init__() {
		this.bindDrawer();
		this.bindThemeSwitch();
		ui.menu.load().then((tree) => this.render(tree));
	},

	render(tree) {
		const modes = ui.menu.getChildren(tree);
		const path = L.env.dispatchpath;
		const mode = modes.find((node) => node.name === L.env.requestpath[0]) ?? modes[0];

		if (!mode)
			return;

		this.renderMenu(mode, path);
		this.renderModes(modes, mode);
		this.renderLogout(mode);

		let node = tree;
		let url = '';
		const trail = [];

		for (let i = 0; i < 3 && node; i++) {
			node = node.children?.[path[i]];
			url = url + (url ? '/' : '') + path[i];
			if (node && i > 0)
				trail.push({ node, url });
		}

		if (node)
			this.renderTabMenu(node, url, 0, trail);

		this.renderCrumbs(trail);
	},

	renderMenu(mode, path) {
		const nav = document.querySelector('#mainmenu');
		const entry = (href, title, current) => E('a', {
			'href': href,
			'aria-current': current ? 'page' : null
		}, [ _(title) ]);

		ui.menu.getChildren(mode).forEach((category) => {
			const pages = ui.menu.getChildren(category);
			const active = path[1] === category.name;

			// Logout has its place in the header, and in the drawer's foot.
			if (category.name === 'logout')
				return;

			// A first level without pages of its own is one entry, without a label.
			const group = E('div', { 'class': 'menu-group' });
			const entries = pages.length === 0
				? [ entry(L.url(mode.name, category.name), category.title, active) ]
				: pages.map((page) => entry(L.url(mode.name, category.name, page.name),
					page.title, active && path[2] === page.name));

			if (pages.length > 0)
				group.appendChild(E('h2', {}, [ _(category.title) ]));
			group.appendChild(E('div', { 'class': 'menu-list' }, entries));
			nav.appendChild(group);
		});
	},

	renderModes(modes, current) {
		if (modes.length < 2)
			return;

		const foot = document.querySelector('.sidebar-foot');

		foot.prepend(E('div', { 'class': 'modes' }, modes.map((node) => E('a', {
			'class': node === current ? 'active' : null,
			'href': L.url(node.name)
		}, [ _(node.title) ]))));
	},

	// Logout is a first-level node of LuCI's menu; where there is none, there is no
	// button. The header's button shows from 800 pixels up, the drawer's entry on phones.
	renderLogout(mode) {
		const node = ui.menu.getChildren(mode).find((child) => child.name === 'logout');

		if (!node)
			return;

		const href = L.url(mode.name, node.name);

		document.querySelector('.topbar').appendChild(E('a', {
			'class': 'btn ghost small logout',
			'href': href
		}, [ _(node.title) ]));
		document.querySelector('.sidebar-foot').appendChild(E('a', {
			'class': 'menu-logout',
			'href': href
		}, [ _(node.title) ]));
	},

	renderTabMenu(tree, url, level, trail) {
		const container = document.querySelector('#tabmenu');
		const children = ui.menu.getChildren(tree);
		let activeNode = null;

		if (children.length === 0)
			return;

		const ul = E('ul', { 'class': 'tabs' }, children.map((child) => {
			const active = L.env.dispatchpath[3 + level] === child.name;

			if (active)
				activeNode = child;

			return E('li', { 'class': `tabmenu-item-${child.name}${active ? ' active' : ''}` }, [
				E('a', { 'href': L.url(url, child.name) }, [ _(child.title) ])
			]);
		}));

		container.appendChild(ul);
		container.style.display = '';

		if (activeNode) {
			trail.push({ node: activeNode, url: `${url}/${activeNode.name}` });
			this.renderTabMenu(activeNode, `${url}/${activeNode.name}`, level + 1, trail);
		}
	},

	// The levels above the page link to it, as LuCI's own first pages of a level do.
	renderCrumbs(trail) {
		const crumbs = document.querySelector('#crumbs');

		trail.forEach(({ node, url }, index) => {
			crumbs.appendChild(index === trail.length - 1
				? E('span', { 'aria-current': 'page' }, [ _(node.title) ])
				: E('a', { 'href': L.url(url) }, [ _(node.title) ]));
		});
	},

	bindDrawer() {
		const toggle = document.querySelector('#menu-toggle');
		const close = () => {
			document.body.classList.remove('drawer-open');
			toggle.setAttribute('aria-expanded', 'false');
		};

		toggle.addEventListener('click', () => {
			const opened = document.body.classList.toggle('drawer-open');

			toggle.setAttribute('aria-expanded', String(opened));
		});
		document.querySelector('#scrim').addEventListener('click', close);
		document.addEventListener('keydown', (ev) => {
			if (ev.key === 'Escape')
				close();
		});
	},

	// The header's switch, and a copy in the drawer's foot for phones, where the
	// header has no room for it.
	bindThemeSwitch() {
		const copy = document.querySelector('#theme-switch').cloneNode(true);

		copy.removeAttribute('id');
		document.querySelector('.sidebar-foot').appendChild(copy);

		const buttons = document.querySelectorAll('.segmented [data-choice]');
		const show = () => {
			const choice = document.documentElement.getAttribute('data-theme-choice');

			buttons.forEach((button) => {
				button.setAttribute('aria-pressed', String(button.dataset.choice === choice));
			});
		};

		buttons.forEach((button) => {
			button.addEventListener('click', () => {
				window.orbytTheme(button.dataset.choice);
				show();
			});
		});
		show();
	}
});
