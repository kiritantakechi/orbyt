# orbyt-sync: what orbyt-sync and orbyt-update share (r4s-release-pipeline D4). POSIX
# sh, so no locals: every function keeps its variables under an orbyt_ prefix.

# orbyt_sync_device: print the router's OpenWrt device, after which a release
# names the router's asset set (board-model D10).
orbyt_sync_device() {
	tr ',' '_' </tmp/sysinfo/board_name
}
