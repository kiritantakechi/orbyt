'use strict';
'require view';

// The login card's behavior (orbyt-theme D2): focus on the password, and the
// spinner on the button once the form is on its way.
return view.extend({
	render() {
		const form = document.querySelector('#login');
		const button = form.querySelector('button[type="submit"]');

		form.addEventListener('submit', () => {
			button.classList.add('spinning');
			button.textContent = _('Logging in…');
		});

		form.querySelector('input[type="password"]').focus();

		return '';
	},

	addFooter() {}
});
