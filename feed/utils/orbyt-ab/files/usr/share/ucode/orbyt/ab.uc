// orbyt.ab: the two slots on the boot disk (r4s-ab-rollback D1, D4): the running
// slot, the other one, and the U-Boot variables that pick and confirm a slot.
// The sysupgrade hook keeps these facts in shell (/lib/functions/orbyt-ab.sh),
// as its second stage runs from a RAM root without ucode.
'use strict';

import { popen, readfile } from 'fs';

// RESULT: where the health check records this boot's result, which orbyt-slot
// shows and the trial watchdog waits for (firmware-hygiene D6).
export const RESULT = '/var/run/orbyt-healthcheck.json';

// seconds(): seconds since the kernel's start, on the monotonic clock, which
// setting the time of day does not move, as NTP does once the router is online
// (trial-boot-resilience D4).
export function seconds() {
	return clock(true)[0];
}

// slot(): the running slot, "a" or "b", as U-Boot passed it to the kernel; null
// on a system not booted from a slot.
export function slot() {
	let found = match(readfile('/proc/cmdline') ?? '', /(^|\s)orbyt\.slot=(a|b)(\s|$)/);

	return found ? found[2] : null;
}

// environment(cmdline): the copies of the U-Boot environment that the bootloader
// named on the kernel command line (orbyt.env=<size>@<offset>,...), as { size,
// offset } in its hexadecimal notation: the only places the system may read and
// write it (trial-boot-resilience D2, D3). null when it named none, as a
// bootloader from before two copies does. cmdline defaults to this boot's.
export function environment(cmdline) {
	let found = match(cmdline ?? readfile('/proc/cmdline') ?? '', /(^| )orbyt\.env=([^ \n]+)/);
	let copies = [];

	for (let copy in split(found?.[2] ?? '', ',')) {
		let place = match(copy, /^(0x[0-9A-Fa-f]+)@(0x[0-9A-Fa-f]+)$/);

		if (!place)
			return null;

		push(copies, { size: place[1], offset: place[2] });
	}

	return length(copies) ? copies : null;
}

// other(running): the slot that is not running.
export function other(running) {
	return running == 'a' ? 'b' : 'a';
}

// variables(): the U-Boot environment, an object of its variables; null when it
// cannot be read, as where no place for it is configured: a variable that is not
// set and an environment that cannot be read are not the same.
export function variables() {
	let tool = popen('fw_printenv 2>/dev/null');
	let text = tool.read('all') ?? '';

	if (tool.close() != 0)
		return null;

	let found = {};

	for (let line in split(text, '\n')) {
		let equals = index(line, '=');

		if (equals > 0)
			found[substr(line, 0, equals)] = substr(line, equals + 1);
	}

	return found;
}

// setenv(values): write U-Boot variables at once, then flush them to the disk:
// a panic or watchdog reset does not wait for writeback. True when both worked.
// A tool that ends before it reads them must fail the write, not end the caller
// with SIGPIPE.
export function setenv(values) {
	let previous = signal('SIGPIPE');

	signal('SIGPIPE', 'ignore');

	let tool = popen('fw_setenv -s - && sync', 'w');

	for (let name in values)
		tool.write(`${name} ${values[name]}\n`);

	let written = tool.close() == 0;

	signal('SIGPIPE', previous);

	return written;
}
