# Thermia Genesis

Home Assistant integration for **Thermia Genesis-platform** heat pumps — the Mega
and Inverter register maps, including the Calibra — read over **local Modbus TCP**.

It began as a fork of [CJNE/thermiagenesis](https://github.com/CJNE/thermiagenesis)
and is now maintained independently, as upstream is no longer active. The Modbus
register layer lives in the companion library
[`thermia-genesis-modbus`](https://pypi.org/project/thermia-genesis-modbus/); this
repository is the Home Assistant integration built on top of it.

## Installation

1. In HACS, add this repository as a **custom repository**
   (`JanJoh/thermiagenesis`, category **Integration**) and install it.
2. Restart Home Assistant.
3. **Settings → Devices & Services → + Add Integration → Thermia Genesis**, and
   enter the pump's Modbus host, port (`502`), and register map — `inverter` or
   `mega` (a Calibra uses `mega`).

Requires Home Assistant **2024.1.0** or newer.

### Coming from CJNE's original integration?

**Uninstall it first.** Recent Home Assistant/HACS won't overwrite a
`custom_components/thermiagenesis` folder that's owned by a _different_ source,
so installing this on top of [CJNE's](https://github.com/CJNE/thermiagenesis)
can fail to copy the files. Remove CJNE's version in HACS (or delete its
`custom_components/thermiagenesis` folder), restart Home Assistant, then install
this one. Your config entry, entities, history and automations are keyed by
domain and entity ID, so they carry over unchanged — this only swaps which
source provides the code.

## Updating from a pre-1.0.0 install (HACS)

**If you added this integration as a HACS custom repository before 2026-11-20,
HACS may not offer the 1.0.0 update** (it errors with something like _"unknown
repository ID"_). The project was re-created as a standalone, non-fork
repository, which changed its GitHub repository ID — and HACS keys custom
repositories by that ID.

Re-point HACS at it:

1. HACS → **Thermia Genesis** → ⋮ → **Remove** (this removes the HACS _download_
   only — not your devices or entities).
2. HACS → ⋮ → **Custom repositories** → remove `JanJoh/thermiagenesis` if it's
   still listed, then **add** it again (category _Integration_).
3. Reinstall **Thermia Genesis** (now 1.0.0+) and **restart** Home Assistant.

**Do not** delete the integration from _Settings → Devices & Services_ — that
removes the config entry and erases your entity renames, areas, and anything
referencing those entities. The steps above touch only the HACS download, so
your devices, entities, history and automations are preserved.

## What it fixes

Relative to the original integration and library, this version carries:

- **Proper `device_class` and `state_class`** on registers (upstream
  [PR #318](https://github.com/CJNE/thermiagenesis/pull/318)), and sensor
  attributes corrected against the official Thermia Modbus specification.

- **Fixed the reported firmware version.** Two separate faults. First, every
  `device_info` used `coordinator.data.get("firmware")`, but `coordinator.data`
  is keyed by _register name_ and no register is called `firmware` — so the
  lookup returned `None` unconditionally.

  Second, `ThermiaGenesis.firmware` cannot be used either: the library sets it
  from `self.data` _before_ overwriting `self.data` with the freshly read
  values, so it always lags one refresh behind. On the first refresh `self.data`
  is still empty, the resulting `KeyError` is swallowed by the library's own
  `except KeyError`, and the attribute stays `None` — and `device_info` is built
  between the two refreshes, so it would never see a value.

  The coordinator therefore computes the version itself from its own current
  data, and setup requests the three `input_software_version_*` registers before
  the first refresh so the value exists when the platforms build their device
  info.

- **No more `unknown` entities for 30 seconds after every reload.** Setup called
  `coordinator.async_refresh()` _before_ forwarding the platform setups — at
  which point no entity had registered anything, so the coordinator asked for
  zero registers and stored an empty dict. Entities are then added with
  `async_add_entities(..., False)`, so every one read `None` until the next
  scheduled poll. Setup now refreshes again once the platforms have registered
  what they want.

- **Corrected pool temperature scaling.** `input 119` (pool supply line) and
  `input 120` (pool return line) are °C registers at scale `100`, as the Thermia
  spec gives every other °C register in the map. The `thermia-genesis-modbus`
  register table now declares them so, rather than the scale `1` that reported
  them a hundred times too high.

- **Widened mega discrete-input register ranges.** Four dinput registers are
  flagged `mega: True` in the register table — so the per-model gate in the
  platform setups quite correctly creates entities for them — yet they fell
  outside the declared mega dinput ranges `[[0, 3], [9, 83], [199, 247]]`:

  | addr | register                                 |
  | ---- | ---------------------------------------- |
  | 4    | `dinput_alarm_active_class_e`            |
  | 84   | `dinput_primary_unit_conflict_alarm`     |
  | 85   | `dinput_primary_unit_no_secondary_alarm` |
  | 86   | `dinput_oil_boost_in_progress`           |

  Enabling any of them left `_get_data()` unable to place the address in a
  block, and the unguarded `in_range[0]` raised `IndexError`. Because that
  happens inside the coordinator's `_async_update_data`, a single such register
  failed the whole refresh and **every** entity the integration owns went
  unavailable. Observed: enabling _Alarm Active Class E_ on a Calibra produced
  1581 consecutive failures and took ~400 entities down for six hours.

  All four sit directly against registers already in range — 0–3 are alarm
  classes A–D and this is class E; 83 is the secondary unit alarm and 84–86
  follow on — so the range table was short rather than the registers being
  absent. Confirmed against the spec (see Reference below): the discrete input
  table runs 0–4 for alarm classes A–E, jumps to 9 (so 5–8 is a genuine hole),
  and the 81–87 block ends at `87`, tap water top sensor alarm. The
  `thermia-genesis-modbus` table now declares the correct ranges
  (`[[0, 4], [9, 87], [199, 247]]`).

- **Demand sensors are enum sensors.** _First/Second/Third Prioritised Demand_
  and the five _Queued Demand_ sensors hold text ("Heat", "Hot water",
  "Anti legionella", …), but every sensor without an explicit `state_class`
  defaulted to `measurement`. For those the history view draws a statistics
  graph, which stays empty for text, so their history looked missing. Registers
  decoded as `TYPE_STATUS` are now `device_class: enum` with the library's
  status strings as `options` and no `state_class`, and show as a state
  timeline.

- **Gear limits follow the compressor.** The _Minimum/Maximum Allowed Gear In …_
  numbers (heating, tap water, pool, cooling) had a static maximum of 9, so a
  10-gear compressor (Diplomat Inverter Duo, Calibra) could never be set back to
  its own top gear once lowered. The maximum now follows
  `input_compressor_available_gears` when the pump reports it, and falls back to
  the static limit otherwise.

- **Heating season stop limited to 5–25 °C.** The number used the generic
  −40–100 °C range, so a slip of the slider could set it to 40 °C. That keeps
  the heating season active all year; it happened on a real pump and went
  unnoticed for a month.

- **Internal immersion heater on `mega`.** `input 67` (internal additional
  heater, current step) and `dinput 222` (internal additional heater active)
  answer on a Calibra configured as `mega`; the `thermia-genesis-modbus` table
  enables them for the mega map, and the entities are on by default.

- **Room temperature reports unavailable without a sensor.** When no room sensor
  is wired, `input 121` returns a ~200 °C placeholder. The room-temperature
  sensor now goes `unavailable`, and the heat climate entity reports no current
  temperature, instead of passing the placeholder through as 200 °C
  ([#3](https://github.com/JanJoh/thermiagenesis/issues/3)).

## Reference

Register numbers, units, scales and descriptions here are checked against
Thermia's own document, **Modbus protocol for Mega & Mega E, Genesis platform,
version 17.00.007**
([copy](https://www.geotherma.be/wp-content/uploads/2026/02/Modbus-protocol-for-Genesis-platform-17.1-MEGA.pdf)).

Two things from it worth knowing when reading the register tables:

- The **Reference to** column is a subsystem tag, not a footnote:
  `1` heating system, `2` hot water, `3` TWC, `4` WCS, `5` cooling, `6` pool,
  `7` distribution circuit, `8` buffer tank, `9` electric meter,
  `10` internal heat pump, `11` RSM (Mega E only).
- **(EM)** marks a register requiring an expansion module; **(EM3 only)** a
  specific card.

A read-only sweep of all 434 registers in the library's table against a Calibra
8E returned data for every one, with no Modbus exceptions. **That is not
evidence a feature exists** — the Genesis controller answers its whole address
map whether or not the optional hardware is fitted. On a pump without the
electric meter, for instance, `input 69`–`84` all read `0`, including the three
line-to-neutral voltages. Those voltages are the practical availability probe:
a fitted meter always sees mains voltage, so `input 72 == 0` means no meter,
whereas zero current or zero power is ambiguous.

## Known rough edges

- `ATTR_MODEL` in each platform is the hardcoded string
  `"Diplomat Inverter Duo"`, so the device and its entity IDs carry that name
  whatever your pump actually is. It means entity names are not evidence of the
  configured platform — the configured `kind` is `entry.data[CONF_TYPE]`. Note
  this is **not safely fixable**: `ATTR_MODEL` is also the device identifier
  (`identifiers: {(DOMAIN, ATTR_MODEL)}`), so changing it would register a new
  device and orphan every existing entity. The library already exposes a correct
  `thermia.model`, but adopting it needs a migration rather than an edit.
- `climate.py` is the one platform that does not gate entity creation on the
  configured model. Currently harmless, since `CLIMATE_TYPES` contains no
  model-specific registers.
- `kind` (`inverter` / `mega`) selects a **register map**, not a description of
  the hardware: the library models only the Diplomat Inverter and the Mega. A
  Calibra is neither, and `mega` is the closer fit — coil 59, condenser pump
  continuous operation, is inside the mega ranges and outside the inverter
  ones. But a Calibra also answers registers outside _both_ maps, so the tables
  are incomplete for it either way.
- The library's per-model flags conflate **model capability** with **fitted
  hardware**. Sixteen registers documented in the Mega spec — the electric
  meter block `input 69`–`83`, plus coil 26 — are flagged `MODEL_MEGA: False`
  and so produce no entities at all; correcting the flag would instead produce
  sixteen entities reading zero on any pump without the meter. The real fix is
  gating per subsystem rather than per model, which is a larger design change
  and deliberately not attempted here.

## Credits

Based on the original [thermiagenesis](https://github.com/CJNE/thermiagenesis)
integration and `pythermiagenesis` library by
[@CJNE](https://github.com/CJNE) and contributors, used under the MIT license.
