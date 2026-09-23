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
  absent. Reported upstream as
  [pythermiagenesis#7](https://github.com/CJNE/pythermiagenesis/issues/7), with
  [pythermiagenesis#8](https://github.com/CJNE/pythermiagenesis/issues/8) asking
  that `_get_data` warn and skip rather than raise, so this class of mismatch
  can never again be fatal.

## Known rough edges

- `ATTR_MODEL` in `sensor.py` is the hardcoded string `"Diplomat Inverter Duo"`,
  so the device and its entity IDs carry that name whatever your pump actually
  is. Cosmetic, but it means entity names are not evidence of the configured
  platform — the configured `kind` is `entry.data[CONF_TYPE]`.
- `climate.py` is the one platform that does not gate entity creation on the
  configured model. Currently harmless, since `CLIMATE_TYPES` contains no
  model-specific registers.

## Staying in sync with upstream

    git fetch upstream
    git merge upstream/master
    git push origin master

## Credits

Original project by [@CJNE](https://github.com/CJNE). All rights belong to the original authors and contributors.
See the upstream repo for full documentation, installation instructions, and contribution guidelines.
