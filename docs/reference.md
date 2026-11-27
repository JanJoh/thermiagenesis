# Reference

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
Eco 8 returned data for every one, with no Modbus exceptions. **That is not
evidence a feature exists** — the Genesis controller answers its whole address
map whether or not the optional hardware is fitted. On a pump without the
electric meter, for instance, `input 69`–`84` all read `0`, including the three
line-to-neutral voltages. Those voltages are the practical availability probe:
a fitted meter always sees mains voltage, so `input 72 == 0` means no meter,
whereas zero current or zero power is ambiguous.
