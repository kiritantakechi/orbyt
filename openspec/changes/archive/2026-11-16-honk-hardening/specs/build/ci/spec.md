## MODIFIED Requirements

### Requirement: Cache keyed on actual inputs
The host stage's cache key SHALL be determined only by the inputs that affect what it builds:
- the contents, as patched, of the tools and toolchain directories of the openwrt repository, of its generic kernel files, from which the toolchain's kernel headers come, of its build files that name the host packages' stamps, and of the Go and Rust directories of the packages feed;
- the definition of the target and subtarget the boards select: the makefiles that name their architecture, CPU type, features and kernel version;
- the options of the board-neutral configuration, set or not set, and not its comments;
- the build environment;
- the scripts that build and pack the stage.

Every stage SHALL keep a compiler cache for each language it compiles: C and C++, Go, and Rust. Each stage's compiler cache SHALL hold only what that stage's latest build used, so that the caches of all stages fit the repository's cache quota.

#### Scenario: Only the packages feed updated
- **WHEN** the packages feed's SHA in `upstream.lock` changes, but not its Go or Rust directories
- **THEN** the host stage's cache still hits

#### Scenario: Toolchain inputs change
- **WHEN** the tools or toolchain directories of the openwrt repository, its generic kernel files, its build files that name the host packages' stamps, or the Go or Rust directories of the packages feed, change
- **THEN** the host stage's cache is invalidated and rebuilt

#### Scenario: Kernel version of the target changes
- **WHEN** the boards' target selects another kernel version, and nothing else of the key's inputs changes
- **THEN** the host stage's cache is invalidated and rebuilt

#### Scenario: A device added to the target
- **WHEN** the boards' target gains a device, and nothing else of the key's inputs changes
- **THEN** the host stage's cache still hits

#### Scenario: A comment of a seed changes
- **WHEN** a seed's comment changes, and nothing else of the key's inputs changes
- **THEN** the host stage's cache still hits

#### Scenario: Rebuild from warm compiler caches
- **WHEN** a stage builds sources it has built before, with its compiler cache restored
- **THEN** the caches serve every C, C++, Go and Rust compilation of a source the stage has compiled before, and each language's report shows misses only for sources the build generates anew

#### Scenario: One compiler cache per stage
- **WHEN** a CI run's caches have been pruned
- **THEN** the ref holds one compiler cache for the host stage and one for each board, each holding no entry its stage's latest build left unused

#### Scenario: Stage names with a hyphen
- **WHEN** a ref holds compiler caches of the stages `r6s` and `r6s-plus`, and its caches are pruned
- **THEN** the newest compiler cache of each stage stays
