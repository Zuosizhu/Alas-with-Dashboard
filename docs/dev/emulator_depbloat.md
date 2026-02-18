# Emulator Debloating Guide (2026 Edition)

Covers MEmu and LDPlayer. Applies to emulator versions shipping Android 9–12.
Last verified: 2026-02-18.
Sources: TameemS gists (MEmu, LDPlayer), 1broccoli automation tool, Red0Hood
LDPlayer_Debloater host list, community XDA threads, file.net process documentation.
Appraisal of community tools performed 2026-02-18 — see §5 for verdicts.

---

## Executive Summary

**Simple file deletion is largely dead.**
Guides that say "open Root Browser, delete `/system/priv-app/MEmuLauncher`"
are outdated. Android 11+ emulator builds mount that partition read-only.
File explorers either silently fail or cause boot freezes.

**ADB `pm uninstall --user 0` is the standard.**
It removes the package for the active user without touching the read-only
system partition. The APK stays on disk but stops executing. Survives reboots.
Does not require modifying protected paths.

**IP blocklists decay; program-path firewall rules do not.**
Microvirt and LDPlayer rotate their server IPs. Rules keyed on executable path
are more durable and the preferred approach for both emulators.

**Update regression is real.**
MEmu and LDPlayer updates re-enable removed packages and reset hosts overrides.
All debloat steps must be repeated after each emulator update.

---

## 1. MEmu

### 1.1 Critical Warning — Android 12 Launcher Removal

> **Do not remove `com.microvirt.launcher2` on MEmu Android 12 builds.**
> The OS freezes at approximately 59% during the next boot and does not
> recover. This affects only the Android 12 MEmu variant. Android 5.1, 7.1,
> and 9 are safe.

If you are on Android 12 and need a clean launcher experience, install a
replacement (e.g., Nova Launcher) and set it as default **before** removing
the MEmu launcher. If you remove `launcher2` and get a boot freeze, restore
via:

```cmd
adb shell cmd package install-existing com.microvirt.launcher2
```

---

### 1.2 Prerequisite — Replacement Launcher

Install a third-party launcher *before* removing `com.microvirt.launcher2`.
Without a launcher, the device has no home screen after removal.

Recommended: Nova Launcher (free tier sufficient), Lawnchair, or any AOSP
launcher APK sideloaded via `adb install`.

**Why this order matters:** `pm uninstall --user 0` takes effect immediately.
There is no grace period between removal and the next time something tries to
send you to the home screen.

---

### 1.3 Package Removal via ADB

**Prerequisites**

- Root mode enabled: MEmu Settings → Other → Root mode.
- `adb.exe` available (ships with MEmu; also available from Android Platform
  Tools).

**Connect**

```cmd
adb connect 127.0.0.1:21503
```

Why: ADB defaults to USB. MEmu exposes a TCP bridge; you must explicitly
connect before `adb shell` targets the emulator.

Debug: `failed to connect` → wrong port (check MEmu Settings → Connection;
common alternates: 21513, 21523) or ADB server not running (`adb start-server`).

Debug: device shows as `offline` or `unauthorized` → cycle the ADB server:

```cmd
adb kill-server
adb start-server
adb connect 127.0.0.1:21503
```

`offline` means the transport lost its connection. `unauthorized` means the
device's RSA key prompt was not accepted. Cycling the server clears both.
For `unauthorized`, also check that "Allow ADB debugging" was accepted inside
the emulator (MEmu pops a dialog on first connect).

**Enter a root shell**

```cmd
adb shell
su
```

Why: `pm uninstall --user 0` for system apps requires root. Without `su` you
get `Exception occurred while executing` permission errors.

Debug: `su` hangs → Root mode not enabled in MEmu settings. `su` succeeds but
uninstall still fails → the su binary is not granting full root (try a
Magisk-patched MEmu build).

**Remove packages**

```bash
pm uninstall --user 0 com.microvirt.guide
pm uninstall --user 0 com.microvirt.installer
pm uninstall --user 0 com.microvirt.launcher2   # NOT on Android 12 — see §1.1
pm uninstall --user 0 com.microvirt.launcher     # legacy variant, older builds
pm uninstall --user 0 com.microvirt.memuplay
pm uninstall --user 0 com.microvirt.market
```

Why `--user 0`: Removes the package for the primary Android user without
touching the system partition. The system partition is read-only on many
builds; `--user 0` is the only path that reliably works.

Why not just `pm uninstall` (no user flag): This attempts a full system-level
removal, which fails on read-only partitions with a permission error.

Debug: `Success` = done. `Exception occurred while executing` = wrong package
name. Find exact names with:

```bash
pm list packages | grep microvirt
```

**Restore a removed package if needed**

```bash
adb shell cmd package install-existing com.microvirt.launcher2
```

This re-enables the package from the still-present system partition APK without
reinstalling MEmu.

---

### 1.4 Network Blocking

Goal: prevent MEmu from contacting ad servers, telemetry endpoints, and
auto-update infrastructure that can re-enable removed packages.

**Do this before debloating.** If the emulator has internet access while you
work, the background updater can re-register packages during removal.

**Option A — Block by executable path (recommended, more durable)**

Program-path rules survive IP rotation:

```batch
netsh advfirewall firewall add rule name="Block MEmu OUT" ^
    program="C:\Program Files\Microvirt\MEmu\MEmu.exe" ^
    dir=out action=block profile=any
netsh advfirewall firewall add rule name="Block MEmu Headless OUT" ^
    program="C:\Program Files\Microvirt\MEmuHyperv\MEmuHeadless.exe" ^
    dir=out action=block profile=any
```

Adjust paths to match your MEmu installation folder.

> **Note — Hyper-V vs VirtualBox backend:** `MEmuHyperv\MEmuHeadless.exe`
> only exists on MEmu's Hyper-V backend. The default MEmu installation uses
> VirtualBox and does not have this path. `netsh advfirewall` creates the rule
> without error for a non-existent executable, but the rule silently matches
> no traffic. If you are on a VirtualBox install, open Task Manager while MEmu
> is running to find the actual headless VM process name, then create the rule
> targeting that path instead.

**Option B — Block by IP list (from TameemS gist, current as of late 2025)**

```batch
@echo off
for /f "usebackq tokens=*" %%i in ("memu_block.txt") do (
    netsh advfirewall firewall add rule name="MEmu_BLOCK_IN_%%i" ^
        dir=in action=block remoteip=%%i
    netsh advfirewall firewall add rule name="MEmu_BLOCK_OUT_%%i" ^
        dir=out action=block remoteip=%%i
)
echo Done.
```

Known IPs to include in `memu_block.txt` (from TameemS MEmu gist):
```
118.31.236.63
114.215.159.204
221.194.169.66
103.215.142.16
```

Run as Administrator. Verify rules were created:
```cmd
netsh advfirewall firewall show rule name=all | findstr MEmu
```

Debug: No rules appear → script was not run as Administrator.

**Option C — Hosts file (domain-level, supplements firewall)**

```
127.0.0.1 www.microvirt.com
127.0.0.1 dl.memuplay.com
```

Add to `C:\Windows\System32\drivers\etc\hosts`.

Note: MEmu updates overwrite the hosts approach. Option A or B is more
persistent.

Coverage note: The above list covers only core Microvirt domains. The
1broccoli automation tool (see §5) ships a substantially larger blocklist
covering AppLovin SDK subdomains, Baishan CDN endpoints (`baishan-cloud.net`,
`bsclink.cn`), and MEmu-specific CloudFront distributions. If hosts-based
blocking is your primary strategy, that tool's `memu_block.example.txt` is
the best available source for the extended entry set. Do not run the
PowerShell script directly — see §5 for caveats.

---

### 1.5 Fixing Read-Only Partition Issues (If Still Needed)

If you specifically need to modify files in `/system` rather than using
`pm uninstall`:

- Set **MEmu Settings → Disk Sharing → Independent system disk**.
  Why: The shared-disk mode mounts the system partition read-only and can
  reset changes on reboot. Independent disk gives each instance a private VMDK
  where writes persist.
- Use **ZArchiver** or **Total Commander** (with root plugin) rather than
  generic file browsers. They surface root permission errors clearly instead of
  silently dropping writes.

---

### 1.6 Confidence Summary — MEmu

| Task | Method | Confidence | Caveat |
|------|--------|------------|--------|
| Package removal | `pm uninstall --user 0` via ADB | High | Do NOT remove `launcher2` on Android 12 |
| Block ads/telemetry | Executable-path firewall rules | High | Re-run after MEmu updates |
| Block by IP | `netsh` batch script | Medium | IPs may rotate; prefer executable-path rules |
| Manual file edits | ZArchiver + independent disk | Medium | Slower, riskier than `pm uninstall` |

---

## 2. LDPlayer

Applies to LDPlayer 9.x (VirtualBox backend, Android 9 base).
Verified by community, January 2026.

### 2.1 Critical Warning — Network Block Before First Run

> Block `dnplayer.exe` in Windows Firewall **before** running LDPlayer for the
> first time. Community reports show that allowing `dnplayer.exe` to connect to
> update endpoints can put LDPlayer into a broken state requiring full
> reinstall.

---

### 2.2 Package Removal via ADB

**Step 1 — Enable ADB**

Settings → Other → ADB Debugging → Open local connection.

Why: LDPlayer disables ADB by default. Without this, `adb connect` will
time out with no useful error.

**Step 2 — Connect**

```powershell
.\adb.exe connect 127.0.0.1:5555
```

Run from your LDPlayer installation folder (e.g., `C:\LDPlayer\LDPlayer9`).
The port shown in LDPlayer's ADB settings may differ per instance.

Debug: `cannot connect to 127.0.0.1:5555` → ADB debugging not enabled, or
wrong port. Check the port in LDPlayer settings.

**Step 3 — Discover exact package names**

```shell
.\adb.exe shell pm list packages | findstr ldmnq
.\adb.exe shell pm list packages | findstr "android.ld"
```

Why: LDPlayer package names vary by build. Common packages found in v9.x:

| Package | Description |
|---------|-------------|
| `com.ldmnq.launcher3` | LDPlayer's modified AOSP home launcher |
| `com.android.ld.appstore` | LDPlayer's built-in app store |

Note: Older guides list `com.ldmnq.appstore`. On 9.x builds this has moved to
`com.android.ld.appstore`. Always verify with `findstr`/`grep` before
uninstalling — do not rely on package names from guides.

Debug: `findstr ldmnq` returns nothing → try `findstr bignox`, `findstr nox`,
`findstr ldplayer`. The package namespace has shifted between minor versions.

**Step 4 — Uninstall**

```shell
.\adb.exe shell pm uninstall -k --user 0 com.ldmnq.launcher3
.\adb.exe shell pm uninstall -k --user 0 com.android.ld.appstore
```

Why `-k`: Keeps the package's data directory. On some LDPlayer builds the data
directory is shared with a service that Android tries to restart. Without `-k`,
removal can trigger a service restart loop and soft-freeze.

Why `--user 0`: Same as MEmu — targets the user profile without requiring
system partition write access.

Debug: `Success` = done. Package reappears after reboot → a watchdog service
survived. Find and uninstall it: `pm list packages | grep ld` again; it may
appear as a separate entry not present before the reboot.

**Optional: Full system-level removal (requires root + remount)**

Only attempt this if user-scope removal is insufficient:

```shell
adb root && adb remount
adb shell ls /system/priv-app/ | grep -i ld  # verify path exists first
adb shell rm -fr /system/priv-app/LDAppStore
```

Note: On LDPlayer 9.1.67.0+, `/system/priv-app/LDAppStore` may not exist.
Always check with `ls` before running `rm`.

**Optional: Suppress the startup splash ad image**

LDPlayer caches its startup advertisement image on the Windows host at:

```
%AppData%\XuanZhi9\cache\
```

Replacing the cached image files with blank/transparent equivalents prevents
the ad from rendering on launch without requiring ADB, firewall rules, or
root. This is cosmetic only — it does not stop telemetry or prevent the
update service from running.

Caveats: This path is LDPlayer-version-specific (`XuanZhi9` corresponds to
LDPlayer 9.x). It may change across major versions. LDPlayer may re-download
the ad image from its CDN if network access is not also blocked by Option A
or Option C in §2.3.

Source: Red0Hood/LDPlayer_Debloater community report.

---

### 2.3 Network Blocking

**The `dnplayer.exe` vs `Ld9BoxHeadless.exe` distinction is critical.**

| Process | Role | Block? |
|---------|------|--------|
| `dnplayer.exe` | Windows-side UI shell — ads, update checks, telemetry to `ldmnq.com` and CloudFront CDN | **Yes** |
| `Ld9BoxHeadless.exe` | VirtualBox headless VM — carries all Android app network traffic (your game) | **Do not block** |

Blocking `Ld9BoxHeadless.exe` kills all internet access inside Android.

**Option A — Block `dnplayer.exe` by executable path (recommended)**

```batch
netsh advfirewall firewall add rule name="Block dnplayer OUT" ^
    program="C:\LDPlayer\LDPlayer9\dnplayer.exe" ^
    dir=out action=block profile=any
netsh advfirewall firewall add rule name="Block dnplayer IN" ^
    program="C:\LDPlayer\LDPlayer9\dnplayer.exe" ^
    dir=in action=block profile=any
```

Adjust path to match your LDPlayer installation folder.

Why executable-path over IP: LDPlayer's ad CDN uses CloudFront IPs shared with
many other services. Blocking by IP risks collateral damage to unrelated
HTTPS traffic.

Debug: Games lose internet after applying rules → you accidentally blocked
`Ld9BoxHeadless.exe` (located at
`C:\Program Files\ldplayer9box\Ld9BoxHeadless.exe`). Remove that rule:

```batch
netsh advfirewall firewall delete rule name="<rule name>"
```

**Option B — Block by IP range (from TameemS LDPlayer gist)**

Known telemetry IP ranges:
```
79.133.177.0-79.133.177.255
163.181.56.0-163.181.56.255
163.181.92.0-163.181.92.255
47.74.196.235
139.224.223.140
106.14.57.193
```

Use the same `netsh advfirewall` batch pattern as §1.4 Option B.

**Option C — Hosts file (domain-level)**

```
# LDPlayer core ad/telemetry domains
0.0.0.0 apien.ldmnq.com
0.0.0.0 appstore.ldmnq.com
0.0.0.0 encdn.ldmnq.com
0.0.0.0 storeen.ldmnq.com
0.0.0.0 apiid.ldmnq.com
0.0.0.0 ldcdn.ldmnq.com
0.0.0.0 usersdk.ldmnq.com
0.0.0.0 adabdapi.ldmnq.com
0.0.0.0 middledata.ldmnq.com

# LDPlayer ad and telemetry endpoints on ldplayer.net
0.0.0.0 advertise.ldplayer.net
0.0.0.0 ad.ldplayer.net
0.0.0.0 middledata.ldplayer.net

# LDPlayer CloudFront CDN distributions (ad delivery)
0.0.0.0 dldgmpfyeblzc.cloudfront.net
0.0.0.0 dn2sifz9m7tkk.cloudfront.net
0.0.0.0 de2pmm85odupd.cloudfront.net
0.0.0.0 dkf29paj6y8sk.cloudfront.net
0.0.0.0 d19przo9d3f9zk.cloudfront.net
0.0.0.0 d330if318qxsm2.cloudfront.net
0.0.0.0 d3p6x1jquzbe0c.cloudfront.net

# Tencent Bugly crash-reporting SDK (embedded in LDPlayer binaries)
0.0.0.0 android.bugly.qq.com
```

Add to `C:\Windows\System32\drivers\etc\hosts`.

Domain source: entries above `encdn.ldmnq.com` (original four) are from the
TameemS gist. Additional entries sourced from Red0Hood/LDPlayer_Debloater host
list, verified as valid domain-format entries (malformed URL-format entries in
that list were discarded). CloudFront distributions were confirmed as
LDPlayer-specific by cross-referencing against known ad delivery patterns.

Note: `android.bugly.qq.com` is Tencent's crash-reporting SDK, which is
embedded in many Chinese-origin Android apps. Blocking it stops LDPlayer from
phoning home with crash telemetry, but does not affect game functionality.

---

### 2.4 Confidence Summary — LDPlayer

| Task | Method | Confidence | Caveat |
|------|--------|------------|--------|
| Package removal | `pm uninstall -k --user 0` via ADB | High | Verify package names with `pm list` first |
| Block desktop ads | Block `dnplayer.exe` by path | High | Do not block `Ld9BoxHeadless.exe` |
| Block by IP | IP range firewall rules | Medium | IPs may shift; prefer executable-path |
| Hosts file blocking | Domain entries | Medium | LDPlayer updates may override |

---

## 3. Verification Steps

After debloating either emulator, verify before declaring success:

```bash
# Confirm packages are gone
adb shell pm list packages | findstr microvirt   # MEmu
adb shell pm list packages | findstr ldmnq       # LDPlayer

# Reboot the emulator, then re-run the above
# If packages reappear: watchdog service is active; find and remove it

# Confirm game networking works
# Launch a game that requires internet and verify it connects
# If it doesn't: check firewall rules — you may have blocked the wrong process
```

---

## 4. Connection to This Project

This repository uses **MEmu** (`127.0.0.1:21503`) as the target emulator for
ALAS automation. Debloating reduces background CPU and network noise that
can interfere with pixel-matching accuracy and OCR reliability.

After debloating:

- Re-run baseline screenshot captures if you notice mask or OCR drift.
- Confirm `Alas.Emulator.Serial` still resolves after any MEmu settings change
  (the ADB port does not change with debloating, but verify after port-related
  settings edits).

Known-good serial for this setup: `127.0.0.1:21503` (see `CLAUDE.md`).

**Note on MEmu Android version:** Check your MEmu build's Android version
before removing `com.microvirt.launcher2`. ALAS has been verified against
MEmu Android 9; Android 12 builds have the boot freeze issue documented in
§1.1 and are not recommended for this project.

---

## 5. References and Tools

| Resource | Appraisal | What it covers |
|----------|-----------|---------------|
| [TameemS MEmu gist](https://gist.github.com/TameemS/603686cec857ff1f91e68607e374b0d8) | Authoritative | Canonical MEmu debloat reference; package list, IP list. This guide derives from it. |
| [TameemS LDPlayer gist](https://gist.github.com/TameemS/894cdb8adae1d6042a5f21c4e80bcd9e) | Authoritative | Canonical LDPlayer debloat reference. This guide derives from it. |
| [1broccoli/memu-debloat-automation](https://github.com/1broccoli/memu-debloat-automation) | **Reference — do not run unmodified** | Sophisticated PowerShell automation for MEmu. Dynamic path resolution, multi-instance support (`memuc listvms`), ADB health recovery, and a large hosts blocklist (~90 entries, covering AppLovin, Baishan CDN, CloudFront). **Do not run unmodified:** uses `pm disable-user` instead of the more durable `pm uninstall --user 0`; no Android 12 launcher guard; hosts file fallback silently schedules a forced Windows reboot with a 10-second countdown and no user confirmation. Useful as a reference for patterns (see §1.3 and §1.4 Option C) and for the extended blocklist in `memu_block.example.txt`. |
| [HideCM/Block-ads-for-LDplayer](https://github.com/HideCM/Block-ads-for-LDplayer) | **Broken — do not use** | Batch script that wraps a single `netsh` rule. The outbound firewall rule is commented out in the source, leaving only an inbound rule. Ads and telemetry travel outbound; this tool does not block them as claimed. Our §2.3 Option A is strictly superior. |
| [Red0Hood/LDPlayer_Debloater](https://github.com/Red0Hood/LDPlayer_Debloater) | **Domain list extracted — do not run binaries** | Not a script. Contains a hosts file list (valid portions incorporated into §2.3 Option C), a startup ad cache guide (`%AppData%\XuanZhi9\cache\`, incorporated into §2.2), and opaque unsigned binaries (`.exe`, `.7z`) that should not be run. The malformed URL-format hosts entries in the list have been discarded. |
| [CypherpunkSamurai AIO gist](https://gist.github.com/CypherpunkSamurai/8bd55be11cfc7db8ac968c8f5ca9f91b) | Reference | Root, Magisk, and debloat for LDPlayer. Not appraised in detail. |

**Quick references:**

- Audit MEmu firewall rules:
  `netsh advfirewall firewall show rule name=all | findstr MEmu`
- Package manager help: `adb shell pm --help`
- List all installed packages: `adb shell pm list packages -f` (includes APK paths)
- MEmu ADB port: MEmu Settings → Connection
- LDPlayer ADB port: Settings → Other → ADB Debugging
