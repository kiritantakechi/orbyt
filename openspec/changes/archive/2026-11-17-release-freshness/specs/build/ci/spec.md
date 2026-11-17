# Spec Delta

## MODIFIED Requirements

### Requirement: Image and kmods from the same build
Each build SHALL output a manifest that records at least: the board it was built for and the board's OpenWrt device, the build run identifier, the hash of `upstream.lock`, the commit of this repository it was built from, marked as changed when the working tree differed from that commit in any file, an untracked file that is not ignored included, the kernel version identifier (vermagic), and the checksum of every file it hands on, each named by its path in the build: the images, the package indexes and the packages among them. The image and the package repository MUST be handed to the downstream release process as a single unit.

#### Scenario: Complete manifest
- **WHEN** a build finishes successfully
- **THEN** the artifacts include this manifest, it names the board that was built and its device, it lists every other file of the artifacts with its checksum, and the vermagic it records matches the image kernel and the kmods in the repository

#### Scenario: A file not committed
- **WHEN** a build runs in a working tree that holds a file that is neither committed nor ignored, and no other change
- **THEN** its manifest marks the commit it names as changed

### Requirement: Cache keyed on actual inputs
The host stage's cache key SHALL be determined only by the inputs that affect what it builds:
- the contents, as patched, of the tools and toolchain directories of the openwrt repository, of its generic kernel files, from which the toolchain's kernel headers come, of its build files and build scripts (`rules.mk`, `include/` and `scripts/`), which the host tools' and the toolchain's makefiles include and run, and of the Go and Rust directories of the packages feed;
- the definition of the target and subtarget the boards select: the makefiles that name their architecture, CPU type, features and kernel version;
- the options of the board-neutral configuration, set or not set, and not its comments;
- the build environment;
- the scripts that build and pack the stage.

Every stage SHALL keep a compiler cache for each language it compiles: C and C++, Go, and Rust. Each stage's compiler cache SHALL hold only what that stage's latest build used, so that the caches of all stages fit the repository's cache quota. Only a run whose commit is current for its ref, as publishing reads it (release/publishing), SHALL delete the ref's caches: a run of a commit its ref has moved past by a change to a file the build workflow runs for, a re-run among them, MUST NOT delete any cache.

#### Scenario: Only the packages feed updated
- **WHEN** the packages feed's SHA in `upstream.lock` changes, but not its Go or Rust directories
- **THEN** the host stage's cache still hits

#### Scenario: Toolchain inputs change
- **WHEN** the tools or toolchain directories of the openwrt repository, its generic kernel files, or the Go or Rust directories of the packages feed, change
- **THEN** the host stage's cache is invalidated and rebuilt

#### Scenario: A build file of OpenWrt changes
- **WHEN** a file of the openwrt repository's `include/` or `scripts/` changes, and nothing else of the key's inputs changes
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

#### Scenario: A re-run of a superseded run
- **WHEN** a re-run of an older run of a ref ends after the newer run of that ref, whose commit changes a file the build workflow runs for, has pruned the ref's caches
- **THEN** every cache the newer run left is still there, and the re-run says that the newer run prunes
