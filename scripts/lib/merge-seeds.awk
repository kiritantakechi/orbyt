# merge-seeds: the lines of the seed files in order, each option only in the last
# line that sets it (CONFIG_X=..., or "# CONFIG_X is not set"), where that line
# stands. A line CONFIG_X+="text" appends text to the string option's value so far,
# and stands as CONFIG_X="value text" (firmware-hygiene D7); an option with no
# string value yet has nothing to append to. Only a quoted value appends, so a
# name with a plus in it (CONFIG_PACKAGE_g++=y) is no append. Comments and blank
# lines stay (scripts/lib/seeds.sh: merge_seeds).

function appends(text) {
	return text ~ /^CONFIG_[^= ]+\+="/
}

function option(text) {
	if (appends(text)) { sub(/\+=".*/, "", text); return text }
	if (text ~ /^CONFIG_[^= ]+=/) { sub(/=.*/, "", text); return text }
	if (text ~ /^# CONFIG_[^ ]+ is not set$/) { split(text, word, " "); return word[2] }
	return ""
}

function quoted(text) {
	return text ~ /^".*"$/
}

{
	line[NR] = $0
	name = option($0)
	if (name == "") next
	if (appends($0)) {
		appended = substr($0, index($0, "+=\"") + 2)
		if (!quoted(value[name]) || !quoted(appended)) {
			printf "merge-seeds: %s: %s appends to no string value\n", FILENAME, name >"/dev/stderr"
			failed = 1
			exit 1
		}
		line[NR] = name "=" substr(value[name], 1, length(value[name]) - 1) substr(appended, 2)
	}
	value[name] = $0 ~ /^#/ ? "" : substr(line[NR], index(line[NR], "=") + 1)
	last[name] = NR
}

END {
	if (failed) exit 1
	for (i = 1; i <= NR; i++) {
		name = option(line[i])
		if (name == "" || last[name] == i) print line[i]
	}
}
