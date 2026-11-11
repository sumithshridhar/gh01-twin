# What a real farm would break (the failure list)

GH-01 is a design. Reality is not predictable from a desk, so this file lists, part by part, what is known to break it,
what the code already guards against, and what is still open. Every real test adds lines here. Each line is a fix to
make, and an honest story to tell.

**What is being built first:** the watering box and the heat-and-dew alarm. They are cheap, useful alone, and when they
fail the farm is no worse than a normal day. The R1 rover is a concept. The rail robot is dropped.

## Watering box (Part 3)

| What goes wrong | Status |
| --- | --- |
| Sensor cable falls out or the sensor shorts | Guarded and tested: an impossible reading never opens the valve |
| One wrong reading from a knocked wire | Guarded and tested: needs three dry readings in a row |
| Power flickers, or comes only a few hours a day | Guarded and tested: no watering for 30 minutes after power-up; the daily limit is remembered across power cuts |
| Tank empty, line blocked, or the sensor is out of the soil | Guarded and tested: after two waterings with no effect it stops and warns; it restarts when the soil reads wet |
| The program hangs with the valve open | Guarded in the sketch (watchdog restart shuts the valve); not tested on hardware |
| The valve sticks open mechanically | **Open.** Code can't close a stuck valve. Today: the hand tap. Later: a flow meter that notices water still running |
| The sensor drifts or corrodes over months | **Open.** Needs a real season of readings |
| One sensor speaks for a whole bed (wet spot, dry spot) | **Open.** Placement rule to be learned on a real bed |
| Calibration differs by soil and by sensor | **Open.** Each box is calibrated by hand today |
| The sketch has never run on a real ESP32 | **Open.** First job when the box is wired |

## Heat-and-dew alarm (Part 4)

| What goes wrong | Status |
| --- | --- |
| Humidity reads 95-99 % every night, so a humidity alarm rings every night | Guarded and tested: it uses the gap to the dew point |
| Too many messages get ignored | Guarded and tested: 10-minute hold, at most one repeat every 3 hours, clear end levels |
| Sensor unplugged, impossible numbers, or stuck on one value | Guarded and tested: reported as a sensor fault, and no other warning is trusted |
| The limits (2 °C gap, 35 °C) are wrong for a given crop | **Open.** Starting points only; tune on a real crop |
| Sun on the probe reads hot | **Open.** Needs the radiation shield, tested outdoors |
| No internet at the farm, so no message arrives | **Open.** Wi-Fi only today; SMS or a local siren later |
| The box is not built and has no board sketch | **Open.** |

## R1 rover (concept)

| What goes wrong | Status |
| --- | --- |
| A hose, a crate, mud or a fallen stake on the path | **Open.** One small obstacle stops it. Not solved |
| Plants grow into the aisle and differently on every farm | **Open.** |
| The cameras miss leaves hidden behind other leaves | **Open.** |
| Telling disease from a photo | **Open, and not claimed.** Field photo apps are right about three times in four at best |
| About ₹2 lakh in parts; pays back in about 3.5 years on one acre at best | **Open.** Too costly for a small house |

## Dropped

- **Rail robot and the row change between houses.** Local polyhouses have no rails, rails cost about ₹17.7 lakh an
  acre, and any obstacle on the handover breaks it. The old idea can still be seen with `?rails`.

## How a line gets added

Run it for real, even on one pot. When something breaks: what happened, what it cost, what was changed, and the test
that now covers it.
