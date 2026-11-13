# How R1 gets a disease name (13 Nov 2026)

**Status: a method and laptop-tested code. Not checked by an agronomist, not tried on a farm.**

## Why the old idea failed

"The camera sees a spot, the AI names the disease" doesn't work in a field. The best photo apps are right about 3 times
in 4 on real field photos. Many problems look the same in a photo (early blight, bacterial spot, septoria), and the
tell-tale sign is often under the leaf, or only shows when you rub it or hold it to the light.

A plant clinic doesn't name a disease from a photo either. It uses the crop, the signs a person checks at the plant,
and the weather. So R1 does the same, in four steps.

## The four steps

| Step | Who | What | Cost |
|---|---|---|---|
| 1. Flag | rover (or a phone) | "this leaf looks different from healthy" + the photo and the exact place | automatic |
| 2. Five taps at the plant | the grower or worker | first "what do you see most?", then up to 4 yes / no questions such as "white powder underneath that rubs off?" ([`r1_diagnose.py`](r1/pi/r1_diagnose.py)) | under a minute |
| 3. Climate | the heat-and-dew alarm | wet-leaf hours and temperature in that house shift the odds (cool + wet: late blight; hot + dry: mites) | automatic |
| 4. Settle the doubtful ones | a lab or an agronomist | when the key says "not sure", and always for a virus or bacteria | per sample |

The answer is either **"likely X"** (with how to confirm it and what to do today that needs no chemical) or
**"not sure"** with the 2–3 candidates. It never names a chemical: products come from the label and a person.

## What the code guarantees (laptop tests)

- 20 problems in the key: 8 for strawberry, 13 for tomato (spider mites are in both). Three are not diseases at
  all (iron shortage, magnesium shortage, blossom end rot), because those get sprayed by mistake.
- A photo alone never gets a name.
- Every problem can be named in 5 taps or fewer.
- 378 simulated cases (every problem × every first answer × 3 climates, answered truthfully): **0 wrong names**,
  99 of 105 named when the first answer was sensible, the rest "not sure".
- It won't name the leader until the runner-up's tell-tale sign has been checked. (The first version said
  "whitefly" on a plant with the virus that whiteflies carry. That is now a test.)
- Two problems on one plant gives "not sure", not one name.
- Problems that spread by touch (mosaic / brown rugose virus, bacterial spots) warn at once: visit that house last,
  wash before the next. Fast ones (late blight, grey mould) say "tell someone today, don't wait for the lab".
- Every case is saved as one line (place, answers, climate, guess). When a lab or agronomist confirms the name it
  becomes a label, and `key_accuracy()` reports how often "likely" was right. That file is the farm's own dataset.

"0 wrong names" means the key is consistent with itself. It does **not** mean it is right on a farm: real plants
show mixed and early signs, and people answer wrongly.

## What still has to be done by people

1. **An agronomist reviews the key** (one sitting): the signs, the climate ranges, anything missing for Karnataka
   polyhouses. Ask the nearest Krishi Vigyan Kendra, a horticulture university, or ICAR-IIHR at Hesaraghatta near
   Bengaluru whether they take samples and what a test costs. (I have not checked their current services.)
2. **Measure it:** for 4 weeks, every flagged plant gets the 5 taps and the grower's own name for it; doubtful and
   important ones go to a lab. Pass = "likely" is right at least 8 times in 10.
3. **Only then think about a photo model.** With a few hundred confirmed cases from this farm, a photo model can be
   tested as a *second opinion* against those labels. Until it beats the 5-tap key on them, it stays out.

## What this does not solve

- Problems not in the key, and crops other than strawberry and tomato: the answer is "send it to a person".
- Disease before any sign shows. That is the climate warning's job (the heat-and-dew alarm), not the camera's.
- Leaves the camera never saw. Those are on the check-by-hand list.
