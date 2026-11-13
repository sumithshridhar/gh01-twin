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

Every R1 problem raised so far, with the fix, the laptop evidence and the bench test still to do:
[build/02-r1-rover/ISSUES.md](build/02-r1-rover/ISSUES.md) (13 Nov). Nothing below has run on a real rover yet.

| What goes wrong | Status |
| --- | --- |
| A hose, a crate, mud or a fallen stake on the path | **Guarded in code and the simulator, not on hardware.** It stops before anything standing in the path and waits; it crosses up to 20 mm and asks for a ramp over higher ones; it notices mud before digging in; otherwise it asks a person, with the place, and carries on from the same metre. 200 simulated paths: 0 hits |
| Driving between houses breaks on any surprise | **Changed:** a worker drives it between houses; it starts by itself only from a checked bed tag and path width |
| A released bumper or e-stop let the wheels start again by themselves | **Fixed in firmware and wiring (RESET latch), tested on a fake Arduino.** Bench test B1 |
| Plants grow into the aisle and differently on every farm | **Guarded:** the lidar follows the soil walls under the leaves, and it stops rather than brush plants. It needs paths of about 46 cm: measure them first |
| The cameras miss leaves hidden behind other leaves | **Reduced, not solved.** Portrait cameras see 99 % of the canopy band (v1: 63 %), a second angle in risky houses, a check-by-hand list for what it missed. Hidden leaves stay hidden |
| Telling disease from a photo | **Not claimed.** R1 only flags "different from healthy"; a person names it; every spray needs a person's name |
| About ₹2 lakh in parts; pays back in about 3.5 years on one acre at best | **Still open: engineering can't fix it.** One parts list now: full ₹2.00–2.18 lakh, Scout ₹1.25–1.38 lakh, trolley ₹0.58–0.63 lakh. None pays back on labour + spray on small houses; only measured crop savings could (bench test B15) |
| The electronics box in a polyhouse at noon (~83 °C) | **Changed:** converters out, white sun shield, morning and late-afternoon patrols; about 44 °C. Bench test B10 |

## Dropped

- **Rail robot and the row change between houses.** Local polyhouses have no rails, rails cost about ₹17.7 lakh an
  acre, and any obstacle on the handover breaks it. The old idea can still be seen with `?rails`.

## How a line gets added

Run it for real, even on one pot. When something breaks: what happened, what it cost, what was changed, and the test
that now covers it.
