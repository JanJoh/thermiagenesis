# What this version fixes, in detail

The reasoning behind each change relative to the original integration and
library. The short list is in the
[README](https://github.com/JanJoh/thermiagenesis#what-it-does-differently); the
power, energy and smart grid sensors have
[their own page](power-and-energy.md).

## Device classes and state classes

**Proper `device_class` and `state_class`** on registers (upstream
[PR #318](https://github.com/CJNE/thermiagenesis/pull/318)), and sensor
attributes corrected against the official Thermia Modbus specification.

## Firmware version

**Fixed the reported firmware version.** Two separate faults. First, every
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

## Unknown entities after a reload

**No more `unknown` entities for 30 seconds after every reload.** Setup called
`coordinator.async_refresh()` _before_ forwarding the platform setups — at
which point no entity had registered anything, so the coordinator asked for
zero registers and stored an empty dict. Entities are then added with
`async_add_entities(..., False)`, so every one read `None` until the next
scheduled poll. Setup now refreshes again once the platforms have registered
what they want.

## Pool temperature scaling

**Corrected pool temperature scaling.** `input 119` (pool supply line) and
`input 120` (pool return line) are °C registers at scale `100`, as the Thermia
spec gives every other °C register in the map. The `thermia-genesis-modbus`
register table now declares them so, rather than the scale `1` that reported
them a hundred times too high.

## Mega discrete-input ranges

**Widened mega discrete-input register ranges.** Four dinput registers are
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
absent. Confirmed against the spec (see [Reference](reference.md)): the discrete input
table runs 0–4 for alarm classes A–E, jumps to 9 (so 5–8 is a genuine hole),
and the 81–87 block ends at `87`, tap water top sensor alarm. The
`thermia-genesis-modbus` table now declares the correct ranges
(`[[0, 4], [9, 87], [199, 247]]`).

## Demand sensors

**Demand sensors are enum sensors.** _First/Second/Third Prioritised Demand_
and the five _Queued Demand_ sensors hold text ("Heat", "Hot water",
"Anti legionella", …), but every sensor without an explicit `state_class`
defaulted to `measurement`. For those the history view draws a statistics
graph, which stays empty for text, so their history looked missing. Registers
decoded as `TYPE_STATUS` are now `device_class: enum` with the library's
status strings as `options` and no `state_class`, and show as a state
timeline.

## Gear limits

**Gear limits follow the compressor.** The _Minimum/Maximum Allowed Gear In …_
numbers (heating, tap water, pool, cooling) had a static maximum of 9, so a
10-gear compressor (Diplomat Inverter Duo, Calibra) could never be set back to
its own top gear once lowered. The maximum now follows
`input_compressor_available_gears` when the pump reports it, and falls back to
the static limit otherwise.

## Heating season stop

**Heating season stop limited to 5–25 °C.** The number used the generic
−40–100 °C range, so a slip of the slider could set it to 40 °C. That keeps
the heating season active all year; it happened on a real pump and went
unnoticed for a month.

## Gear shift delays

**Gear shift delays take seconds.** _Gear Shift Delay Heating/Pool/Cooling_
had no range of their own and fell back to the 0–100 meant for percentages —
below the pump's own 300 s default, so the control could not even hold the
current value. They now accept 0–1800 s
([#14](https://github.com/JanJoh/thermiagenesis/issues/14)).

## Model field

**The pump's model is yours to set.** Every device used to report the model
_Diplomat Inverter Duo_, whatever the pump was. Setup now has an optional
**Model** field, and **Configure** on an existing installation changes it
later; left empty, no model is claimed. Only the model field of the device
changes — its name, its identifier and every entity ID stay as they were, so
history and statistics carry on
([#14](https://github.com/JanJoh/thermiagenesis/issues/14)).

## Gears as whole numbers

**Gears are whole numbers.** _Compressor Available Gears_ and _Compressor
Current Gear_ showed `10.0`, because the register scales them by 100. They
now show `10`.

## Internal immersion heater on mega

**Internal immersion heater on `mega`.** `input 67` (internal additional
heater, current step) and `dinput 222` (internal additional heater active)
answer on a Calibra configured as `mega`; the `thermia-genesis-modbus` table
enables them for the mega map, and the entities are on by default.

## Room temperature without a sensor

**Room temperature reports unavailable without a sensor.** When no room sensor
is wired, `input 121` returns a ~200 °C placeholder. The room-temperature
sensor now goes `unavailable`, and the heat climate entity reports no current
temperature, instead of passing the placeholder through as 200 °C
([#3](https://github.com/JanJoh/thermiagenesis/issues/3)).
