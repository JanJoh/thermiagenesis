# Known rough edges

- The device is still _named_ `Diplomat Inverter Duo` by the integration, and on
  many installs the entity IDs carry that name
  (`sensor.diplomat_inverter_duo_…`) whatever your pump actually is — so entity
  names are not evidence of the configured platform; the configured `kind` is
  `entry.data[CONF_TYPE]`. The name is deliberately left alone: the same string
  is the device identifier (`identifiers: {(DOMAIN, "Diplomat Inverter Duo")}`),
  so changing it would register a new device and orphan every existing entity.
  Set the **Model** field for the real model, and rename the device in Home
  Assistant if you want another display name (answer _No_ when asked whether to
  rename the entity IDs too).
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
