# Thermia Genesis

Home Assistant integration for **Thermia Genesis-platform** heat pumps — the Mega
and Inverter register maps, including the Calibra — read over **local Modbus TCP**.

It began as a fork of [CJNE/thermiagenesis](https://github.com/CJNE/thermiagenesis)
and is now maintained independently, as upstream is no longer active. The Modbus
register layer lives in the companion library
[`thermia-genesis-modbus`](https://pypi.org/project/thermia-genesis-modbus/); this
repository is the Home Assistant integration built on top of it.

## Installation

Thermia Genesis is in the default [HACS](https://hacs.xyz/) catalog.

1. In HACS, search for **Thermia Genesis** and download it — or
   [open it in HACS directly](https://my.home-assistant.io/redirect/hacs_repository/?owner=JanJoh&repository=thermiagenesis&category=integration).
2. Restart Home Assistant.
3. **Settings → Devices & Services → + Add Integration → Thermia Genesis**, and
   enter the pump's Modbus host, port (`502`), and register map — `inverter` or
   `mega` (a Calibra uses `mega`). **Model** is optional: whatever you type
   (say _Calibra Eco 8_ or _Sigrin 13 Duo_) is shown as the device's model, and you
   can change it later under **Configure**.

Requires Home Assistant **2024.1.0** or newer.

**Not showing up in the search?** Add it as a custom repository instead: HACS →
⋮ → **Custom repositories** → `JanJoh/thermiagenesis`, category **Integration**,
then download it from there. The result is the same.

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

Switch to the catalog entry:

1. HACS → **Thermia Genesis** → ⋮ → **Remove** (this removes the HACS _download_
   only — not your devices or entities).
2. HACS → ⋮ → **Custom repositories** → remove `JanJoh/thermiagenesis` if it's
   still listed. You don't need to add it again: the integration is in the
   default HACS catalog now.
3. Search HACS for **Thermia Genesis**, download it (now 1.0.0+) and **restart**
   Home Assistant.

**Do not** delete the integration from _Settings → Devices & Services_ — that
removes the config entry and erases your entity renames, areas, and anything
referencing those entities. The steps above touch only the HACS download, so
your devices, entities, history and automations are preserved.

## What it does differently

Compared with the original integration and library. The reasoning behind each
item is in [docs/changes.md](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md).

**Stays up**

- One register outside its declared range no longer fails the whole refresh and
  takes every entity down
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#mega-discrete-input-ranges)).
- No `unknown` entities for 30 seconds after every reload
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#unknown-entities-after-a-reload)).
- The reported firmware version is right
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#firmware-version)).
- A sensor your pump does not have no longer disturbs the others.

**Shows the right thing**

- Device and state classes on registers, checked against Thermia's Modbus
  specification
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#device-classes-and-state-classes)).
- Pool supply and return temperatures are no longer a hundred times too high
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#pool-temperature-scaling)).
- Demand sensors show their text as a state timeline
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#demand-sensors)).
- Gear sensors show `10`, not `10.0`
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#gears-as-whole-numbers)).
- Room temperature is unavailable, not 200 °C, when no room sensor is wired
  ([#3](https://github.com/JanJoh/thermiagenesis/issues/3),
  [detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#room-temperature-without-a-sensor)).

**Safer controls**

- Gear limits follow the compressor's own number of gears
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#gear-limits)).
- Heating season stop is limited to 5–25 °C
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#heating-season-stop)).
- Gear shift delays take seconds, 0–1800
  ([#14](https://github.com/JanJoh/thermiagenesis/issues/14),
  [detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#gear-shift-delays)).

**New**

- An optional **Model** field, at setup and under **Configure**
  ([#14](https://github.com/JanJoh/thermiagenesis/issues/14),
  [detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#model-field)).
- Heat demand, power, energy and smart grid sensors
  ([#13](https://github.com/JanJoh/thermiagenesis/issues/13)), all disabled by
  default. They need no electric meter module: the values are the controller's
  own estimate. Against a real meter the power estimate runs about 2 % low, and
  the energy figures are a rolling 24 hours of heating only, not a calendar day
  ([docs/power-and-energy.md](https://github.com/JanJoh/thermiagenesis/blob/master/docs/power-and-energy.md)).
- The internal immersion heater's step and state on the `mega` map
  ([detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md#internal-immersion-heater-on-mega)).

## Good to know

- **The device is named _Diplomat Inverter Duo_ whatever your pump is**, and on
  many installs the entity IDs carry that name. That is deliberate: the name is
  also the device identifier, so changing it would orphan every entity. Set the
  **Model** field for the real model, and rename the device in Home Assistant if
  you want another display name.
- **`inverter` / `mega` selects a register map, not your hardware.** A Calibra
  is neither; `mega` is the closer fit.
- **A register that answers is not proof the feature exists.** The controller
  answers its whole address map whether or not the optional hardware is fitted.

More on all three in
[docs/known-rough-edges.md](https://github.com/JanJoh/thermiagenesis/blob/master/docs/known-rough-edges.md) and
[docs/reference.md](https://github.com/JanJoh/thermiagenesis/blob/master/docs/reference.md).

## Documentation

- [What this version fixes, in detail](https://github.com/JanJoh/thermiagenesis/blob/master/docs/changes.md)
- [Heat demand, power, energy and smart grid sensors](https://github.com/JanJoh/thermiagenesis/blob/master/docs/power-and-energy.md)
- [Reference](https://github.com/JanJoh/thermiagenesis/blob/master/docs/reference.md): Thermia's Modbus document and how to read
  its register tables
- [Known rough edges](https://github.com/JanJoh/thermiagenesis/blob/master/docs/known-rough-edges.md)

## Credits

Based on the original [thermiagenesis](https://github.com/CJNE/thermiagenesis)
integration and `pythermiagenesis` library by
[@CJNE](https://github.com/CJNE) and contributors, used under the MIT license.
