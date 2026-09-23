# thermiagenesis (personal fork)

> This is a personal convenience fork. All credit belongs to [@CJNE](https://github.com/CJNE) and contributors.
> Please star, file issues, and contribute upstream: [CJNE/thermiagenesis](https://github.com/CJNE/thermiagenesis).

## Why this fork exists

To install via HACS, and to carry fixes that aren't in upstream yet — unmerged
upstream PRs, plus the occasional small patch of my own. Nothing here is meant
to live in this fork permanently; it is all intended to end up upstream, and
this file is the record of what is still outstanding.

Currently carries:

- **[PR #318](https://github.com/CJNE/thermiagenesis/pull/318)**, merged into master — registers get a proper
  `device_class` and `state_class` in Home Assistant.

- **Sensor attributes corrected** against the official Thermia Modbus
  specification.

- **Fixed the reported firmware version.** Two separate faults. First, every
  `device_info` used `coordinator.data.get("firmware")`, but `coordinator.data`
  is keyed by *register name* and no register is called `firmware` — so the
  lookup returned `None` unconditionally.

  Second, `ThermiaGenesis.firmware` cannot be used either: the library sets it
  from `self.data` *before* overwriting `self.data` with the freshly read
  values, so it always lags one refresh behind. On the first refresh `self.data`
  is still empty, the resulting `KeyError` is swallowed by the library's own
  `except KeyError`, and the attribute stays `None` — and `device_info` is built
  between the two refreshes, so it would never see a value.

  The coordinator therefore computes the version itself from its own current
  data, and setup requests the three `input_software_version_*` registers before
  the first refresh so the value exists when the platforms build their device
  info.

- **No more `unknown` entities for 30 seconds after every reload.** Setup called
  `coordinator.async_refresh()` *before* forwarding the platform setups — at
  which point no entity had registered anything, so the coordinator asked for
  zero registers and stored an empty dict. Entities are then added with
  `async_add_entities(..., False)`, so every one read `None` until the next
  scheduled poll. Setup now refreshes again once the platforms have registered
  what they want.

- **Corrected pool temperature scaling.** `input 119` (pool supply line) and
  `input 120` (pool return line) are declared scale `1` in
  `pythermiagenesis`, but the Thermia spec gives both as scale `100`, as it
  does for every other °C register in the map. Uncorrected they report a
  hundred times too high.

- **Widened mega discrete-input register ranges.** On the `mega` platform, four
  dinput registers are flagged `mega: True` in `pythermiagenesis`' register
  table — so the per-model gate in our platform setups quite correctly creates
  entities for them — yet they fall outside the declared mega dinput ranges
  `[[0, 3], [9, 83], [199, 247]]`:

  | addr | register |
  |---|---|
  | 4 | `dinput_alarm_active_class_e` |
  | 84 | `dinput_primary_unit_conflict_alarm` |
  | 85 | `dinput_primary_unit_no_secondary_alarm` |
  | 86 | `dinput_oil_boost_in_progress` |

  Enabling any of them leaves `_get_data()` unable to place the address in a
  block, and the unguarded `in_range[0]` raises `IndexError`. Because that
  happens inside the coordinator's `_async_update_data`, a single such register
  fails the whole refresh and **every** entity the integration owns goes
  unavailable. Observed: enabling *Alarm Active Class E* on a Calibra produced
  1581 consecutive failures and took ~400 entities down for six hours.

  All four sit directly against registers already in range — 0–3 are alarm
  classes A–D and this is class E; 83 is the secondary unit alarm and 84–86
  follow on — so the range table is short rather than the registers being
  absent. Confirmed against the spec (see Reference below): the discrete input
  table runs 0–4 for alarm classes A–E, jumps to 9 (so 5–8 is a genuine hole),
  and the 81–87 block ends at `87`, tap water top sensor alarm, which the
  library's table does not carry at all. Reported upstream as
  [pythermiagenesis#7](https://github.com/CJNE/pythermiagenesis/issues/7), with
  [pythermiagenesis#8](https://github.com/CJNE/pythermiagenesis/issues/8) asking
  that `_get_data` warn and skip rather than raise, so this class of mismatch
  can never again be fatal.

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
  ones. But a Calibra also answers registers outside *both* maps, so the tables
  are incomplete for it either way.
- The library's per-model flags conflate **model capability** with **fitted
  hardware**. Sixteen registers documented in the Mega spec — the electric
  meter block `input 69`–`83`, plus coil 26 — are flagged `MODEL_MEGA: False`
  and so produce no entities at all; correcting the flag would instead produce
  sixteen entities reading zero on any pump without the meter. The real fix is
  gating per subsystem rather than per model, which is a larger design change
  and deliberately not attempted here.

## Staying in sync with upstream

    git fetch upstream
    git merge upstream/master
    git push origin master

## Credits

Original project by [@CJNE](https://github.com/CJNE). All rights belong to the original authors and contributors.
See the upstream repo for full documentation, installation instructions, and contribution guidelines.
