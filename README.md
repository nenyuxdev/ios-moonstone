# XNU on Moonstone

Experimental work to execute Apple's XNU kernel on the global POCO X5 5G
(`moonstone`, Qualcomm `holi`). The repository focuses on the kernel entry
path: a small ARM64 shim loads an XNU Mach-O payload, constructs a synthetic
Apple Device Tree (ADT), and transfers control to the kernel.

## What has been demonstrated

A prior diagnostic candidate was reported to display the XNU progress markers
through **30: `entering machine_startup`** on the phone. Marker 30 is printed
immediately before the call to `machine_startup`; it does not prove that the
function returned, that the kernel bootstrap or BSD completed, or that an
operating system reached userspace.

The current source is a reduced, Moonstone-named kernel bring-up tree. Its
ABI/name migration and removal of the root-filesystem, GPU, and peripheral
driver work have **not yet been rebuilt or revalidated**. Do not treat the
previous candidate's result as proof that this reduced revision builds or
boots.

This project does **not** currently boot iOS, provide a root filesystem, or
implement a complete device port. It does not include Apple's iOS or Xiaomi
firmware.

## Scope

- XNU build configuration for `MOONSTONE`.
- Early serial/framebuffer diagnostics and progress markers.
- A minimal shim, ADT generator, and payload/Android boot-image packer.
- Offline tests for payload layout, ADT values, and build tooling.
- No rootfs construction, userspace smoke test, GPU, display, touch, storage,
  battery, modem, WLAN, or other peripheral-driver port.

The Android boot image is only a container for the shim and kernel payload.
The workflow builds candidate artifacts for inspection; it does not flash,
reboot, or otherwise operate the phone.

## Build and checks

The GitHub Actions workflow `.github/workflows/moonstone-kernel.yml` builds
XNU and packages v3/v4 Android boot-image candidates. The XNU build uses the
upstream XNU source and toolchain configured by `.github/workflows/xnu.yml`.

Offline checks:

```sh
python3 -m unittest discover -s tests -p 'test_tools.py'
python3 tests/check-project.py
```

To package a previously built Moonstone kernel locally:

```sh
tools/mkboot.sh PATH_TO_KERNEL [OUTPUT.img]
```

The default boot arguments are limited to diagnostics and one CPU. Artifacts
are not installation instructions. No phone operation is part of the build
or test workflow.

## Layout

| Path | Purpose |
| --- | --- |
| `xnu/patches/` | XNU build and early-boot changes retained for the kernel bring-up |
| `shim/` | Minimal ARM64 loader, console, memory setup, and payload handoff |
| `tools/mkadt.py` | Synthetic Moonstone ADT generator |
| `tools/mkpayload.py` | XNU Mach-O payload packer |
| `tools/mkboot.sh` | Packages the shim and payload as Android boot images |
| `.github/workflows/` | XNU build and kernel-image packaging workflows |
| `tests/` | Offline tests and patch-syntax checks |

Moonstone identifiers such as `MOONSTONE`, `xiaomi,moonstone`, and
`qcom,blair` are part of the kernel configuration/ADT ABI. They are kept
consistent across the build, shim, and XNU patches; the board values remain
experimental and should not be mistaken for a complete hardware port.

## Licensing

This repository contains project code and patches for open-source XNU. It
does not redistribute Apple's iOS or proprietary Xiaomi firmware; review the
licenses of upstream components before redistributing build artifacts.
