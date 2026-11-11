# Build GH-01 · Part 4: the heat-and-dew alarm

A small box that hangs inside a polyhouse, reads the air once a minute, and messages the grower when the crop is in
danger. **It only warns. A person opens the vents or switches on the foggers.**

**Status (Nov 2026): the decisions are written and tested on a laptop. The box is not built yet, and there is no
sketch for the board yet.** Planned parts: an ESP32, an SHT30 temperature and humidity probe in a white radiation
shield (a sensor in the sun reads wrong), about ₹2,100 in all.

## What it warns about

| Warning | When | What the grower does |
| --- | --- | --- |
| Dew is about to form | the air is within 2 °C of its dew point for 10 minutes | open the side vents or run the fans for 30 minutes |
| Too hot | 35 °C or more for 10 minutes | shade net or foggers on |
| Sensor fault | an impossible reading, or exactly the same reading for an hour | check the probe and its cable |

Why the dew point and not plain humidity: inside a polyhouse the humidity reads 95-99 % almost every night, so a
"humidity is high" alarm would ring every night and be ignored. Fungus needs water on the leaf, and that forms when
the air cools to its dew point.

## What keeps it useful

- A warning has to last 10 minutes before it is sent. A short damp spell is ignored.
- The same warning repeats at most every 3 hours.
- A warning ends only when the reading is clearly back to normal (3 °C gap, 33 °C), so it doesn't flip on and off.
- While the sensor is faulty, no dew or heat warning is trusted.

The limits are starting points. They need tuning on a real crop.

## Test it on a laptop

```bash
pip install ziglang
bash build/04-heat-dew-alarm/tests/run_test.sh
```

16 checks: a dry day, a damp night, a short damp spell, hovering at the limit, a hot afternoon, an unplugged sensor,
impossible numbers, a stuck sensor, and recovery after a fault.
