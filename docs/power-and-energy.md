# Heat demand, power, energy and smart grid sensors

Added in 1.1.0 for
[#13](https://github.com/JanJoh/thermiagenesis/issues/13). All of these are
disabled by default; enable the ones your pump answers on the device page.

| Register    | Sensor                                     |
| ----------- | ------------------------------------------ |
| input 30    | Calculated Heat Demand                     |
| input 157   | Heat Output Power (kW)                     |
| input 158   | Consumed Electrical Power (kW)             |
| input 331   | Consumed Electrical Energy (kWh)           |
| input 332   | Delivered Heat Energy (kWh)                |
| input 333   | Reported COP                               |
| input 334   | Energy From Natural Source (kWh)           |
| holding 124 | Power Consumption Control Mode (read-only) |
| holding 125 | Input Power Limit (kW, read-only)          |

A sensor your pump does not have does not disturb the others: the register block
it sits in is skipped and the rest are read as usual.

## What the energy figures are

Inputs 331–334 are in no Thermia document. On a Calibra they hold about a day's
worth, and 333 is 332 divided by 331. They are plain measurements, not running
totals, and do not belong in the Energy dashboard.

## No electric meter module needed

The power and energy values are the controller's own estimate, not a
measurement. A pump without the electric meter module reports them all the same.

## How close the estimates are

Checked on a Calibra Eco 8 without the module, against a separate meter on the
pump's electrical supply, over 24 hours in late November 2026.

**Power (input 158).** Hour by hour the estimate ran 1.7 % under the meter on
average, between 2.5 % under and 0.7 % over, at loads from 1.0 to 2.4 kW. At low
load the gap is a steady 25 W or so.

**Energy (input 331).** Three things about it:

- It is a rolling 24 hours, not a calendar day. It did not reset at midnight.
- It is a whole number of kWh and changes on the hour.
- It counts heating only. Energy used while the pump makes hot water is left
  out.

The last point was tested against the meter. For each of 25 hours, take what the
meter counted over the preceding 24 hours, subtract what it counted while the
diverting valve pointed at hot water, and take off 1.5 % for the estimate's
bias:

| Assumption   | Hours matching the pump's figure exactly | Average miss |
| ------------ | ---------------------------------------- | ------------ |
| All energy   | 0 of 25                                  | 2.6 kWh      |
| Heating only | 23 of 25                                 | 0.1 kWh      |

The two misses were 1 kWh each. With hot water included the figure the meter
predicts is 2–5 kWh too high in every hour.

This rests on one day with three hot water runs, so read it as very likely
rather than settled. If 331 is heating only, 332–334 probably are too, which
would make _Reported COP_ a heating COP. That has not been checked.

An earlier spot check agrees with it: on a day in early November the pump
reported 16 kWh when the meter had counted 16.4 kWh over the preceding 24 hours.

## Smart grid registers

_Power Consumption Control Mode_ is left a number, because its meaning depends
on how the pump is set up: in SG-Ready mode 0 normal, 1 load-up, 2 EVU, 3 boost;
in PL/LU mode 0 normal, 1 power limit, 2 load-up, 3 power limit. Nothing is
written to either smart grid register.

_Comfort Mode_ (input 82), which used to show a bare number, shows its name:
EVU, Normal, Comfort or Boost.
