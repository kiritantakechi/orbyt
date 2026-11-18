'use strict';
'require baseclass';
'require ui';

// luci-theme-orbyt's menu (luci-theme-orbyt D4): the mode's first level as the
// sidebar's groups, their pages as links, the third level as tabs, the page's
// place in the top bar; the drawer below 800 pixels, and the light/dark switch.

const OPEN_GROUPS = 'luci-theme-orbyt-menu';

// An outline icon per first-level node LuCI and its applications use; others
// get the generic one.
const ICONS = {
	status: 'M3.5 18a9 9 0 1 1 17 0M12 14l4-4',
	system: 'M6 6h12v12H6zM9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4',
	services: 'M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8M12 13v8',
	network: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18',
	vpn: 'M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z',
	nas: 'M3 12h18v8H3zM5 12l2.5-7h9L19 12M16 16h.01',
	statistics: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
	docker: 'M3 9h4v4H3zM8 9h4v4H8zM13 9h4v4h-4zM8 4h4v4H8zM3 15c0 3 3 5 8 5 6 0 9-3 10-7',
	logout: 'M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 17l-5-5 5-5M5 12h11'
};
const GENERIC = 'M4 6h16M4 12h16M4 18h10';
const CHEVRON = 'M6 9l6 6 6-6';

function icon(path, extra) {
	const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
	const shape = document.createElementNS('http://www.w3.org/2000/svg', 'path');

	svg.setAttribute('class', extra ? `icon ${extra}` : 'icon');
	svg.setAttribute('viewBox', '0 0 24 24');
	svg.setAttribute('aria-hidden', 'true');
	shape.setAttribute('d', path);
	svg.appendChild(shape);

	return svg;
}

function storedGroups() {
	try {
		return new Set(JSON.parse(localStorage.getItem(OPEN_GROUPS) ?? '[]'));
	}
	catch (e) {
		return new Set();
	}
}

function storeGroups(groups) {
	try {
		localStorage.setItem(OPEN_GROUPS, JSON.stringify([...groups]));
	}
	catch (e) {}
}

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

		let node = tree;
		let url = '';
		const trail = [];

		for (let i = 0; i < 3 && node; i++) {
			node = node.children?.[path[i]];
			url = url + (url ? '/' : '') + path[i];
			if (node && i > 0)
				trail.push(node);
		}

		if (node)
			this.renderTabMenu(node, url, 0, trail);

		this.renderCrumbs(trail);
	},

	renderMenu(mode, path) {
		const nav = document.querySelector('#mainmenu');
		const open = storedGroups();

		ui.menu.getChildren(mode).forEach((category) => {
			const pages = ui.menu.getChildren(category);
			const active = path[1] === category.name;
			const glyph = ICONS[category.name] ?? GENERIC;

			if (pages.length === 0) {
				nav.appendChild(E('a', {
					'class': `menu-leaf${active ? ' active' : ''}`,
					'href': L.url(mode.name, category.name)
				}, [ icon(glyph), E('span', {}, [ _(category.title) ]) ]));
				return;
			}

			const expanded = active || open.has(category.name);
			const list = E('ul', { 'class': 'menu-items' }, pages.map((page) => {
				const current = active && path[2] === page.name;

				return E('li', {}, [
					E('a', {
						'class': current ? 'active' : null,
						'href': L.url(mode.name, category.name, page.name),
						'aria-current': current ? 'page' : null
					}, [ _(page.title) ])
				]);
			}));
			const head = E('button', {
				'class': 'menu-head',
				'type': 'button',
				'aria-expanded': String(expanded)
			}, [ icon(glyph), E('span', {}, [ _(category.title) ]), icon(CHEVRON, 'chevron') ]);
			const group = E('div', {
				'class': `menu-group${expanded ? '' : ' closed'}${active ? ' current' : ''}`
			}, [ head, list ]);

			head.addEventListener('click', () => {
				const closed = group.classList.toggle('closed');

				head.setAttribute('aria-expanded', String(!closed));
				if (closed)
					open.delete(category.name);
				else
					open.add(category.name);
				storeGroups(open);
			});

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
			trail.push(activeNode);
			this.renderTabMenu(activeNode, `${url}/${activeNode.name}`, level + 1, trail);
		}
	},

	renderCrumbs(trail) {
		const crumbs = document.querySelector('#crumbs');

		trail.forEach((node, index) => {
			const last = index === trail.length - 1;

			crumbs.appendChild(E(last ? 'b' : 'span', { 'class': last ? null : 'trail' }, [ _(node.title) ]));
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

	bindThemeSwitch() {
		const buttons = document.querySelectorAll('#theme-switch [data-choice]');
		const show = () => {
			const choice = document.documentElement.getAttribute('data-theme-choice');

			buttons.forEach((button) => {
				button.setAttribute('aria-pressed', String(button.dataset.choice === choice));
			});
		};

		buttons.forEach((button) => {
			button.addEventListener('click', () => {
				window.wrtTheme(button.dataset.choice);
				show();
			});
		});
		show();
	}
});
