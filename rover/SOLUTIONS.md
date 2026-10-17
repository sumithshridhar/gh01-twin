# R1: the three unsolved problems, solved

Video #25 ended with three open problems. Here are the fixes, with real parts and real numbers.
Video: Instagram @ghost.ops.ai.service (GH-01 #26).

## 1. "The AI doesn't know this farm yet" (cold start)

The problem: disease models trained on internet photos do badly on a new farm's real photos. Plantix reports ~74 % on field
photos against ~95 % on a curated test set, and PlantDoc's "in the wild" images exist because lab photos (PlantVillage) don't transfer.
Every farm also has its own varieties, light, mulch and camera angle.

The fix has three layers. None of them needs a big disease dataset on day one.

1. **Learn "healthy" first.**
   - An anomaly-detection model is trained only on normal images: the PatchCore and teacher-student families, for example anomalib's EfficientAD.
   - On day 1 the rover photographs every plant. Healthy photos are 99 % of what it sees, so there is plenty to learn "normal" on this farm.
   - Anything that looks different (spots, yellowing, mildew, insects, damage) gets flagged, with a heat map of *where* on the leaf. No disease labels are needed.
   - Edge versions exist: PatchCore-Lite cuts the memory bank by 79 % ([arXiv 2603.20288](https://arxiv.org/abs/2603.20288)).
2. **Ask, don't guess (active learning).**
   - Each evening the app shows the farmer the 10 photos the model is least sure about. One tap each: healthy · disease (which) · pest · don't know. That's about 2 minutes a day.
   - Those are the labels that teach the most. Random photos would mostly be easy healthy ones.
3. **Retrain weekly, update over the air.**
   - Every Sunday the week's labels go into retraining on a laptop GPU. An RTX 3050 is enough for a small detector, and the Hailo compiler needs an x86 Linux PC.
   - The new model is compiled for the AI HAT+ and copied to the rover at its dock.
   - The disease names come from the second-opinion service plus the farmer's taps. With consent, labels can be pooled across farms, so the next farm starts better.

How it's measured: the share of alerts the farmer marks as real (precision), tracked every week. The target is 8 out of 10.
These are targets, not results: nothing has been measured on a real farm yet.

## 2. "4G is weak inside a polyhouse"

1. **Nothing important needs the internet.**
   - Driving, photos, the anomaly check, the spray locks, the e-stop and the logs all run on the rover (Pi 5 + AI HAT+).
   - Store-and-forward: everything is queued on the rover and sent later.
2. **Send crops, not photos.**
   - A 12 MP Camera Module 3 JPEG is ~3–5 MB. A 512 × 512 crop of the flagged leaf is ~40–80 kB.
   - One house: 8 paths × 80 stops × 6 photos ≈ 3,800 photos, about 15 GB a day if all were sent.
   - Flagged crops at 1–2 % come to about 40–80 crops, roughly 2–5 MB a day. That fits even a weak connection.
3. **Upload where the signal is.**
   - The rover charges at a dock just inside the door.
   - A 4G router sits outside on a 3 m GI pole with an external antenna (for example TP-Link TL-MR100, ~₹2.7–7k, with 2 detachable LTE antennas). Its Wi-Fi reaches the dock.
   - The rover syncs while it charges.
4. **Climate boxes use LoRa, not 4G.**
   - LoRa runs in India's licence-exempt 865–867 MHz band (IN865), with km-scale range in open fields and no SIM.
   - One LoRa gateway at the pole collects every house's temperature, humidity and leaf-wetness readings.
   - Check the current DoT/WPC exemption limits before deploying: vendor guides disagree on power and duty cycle.
5. **Fallback:** a plain SMS for "spraying done" and for faults.

## 3. "Too many alerts get ignored" (alert fatigue)

When most alarms are false, people stop reacting. Hospitals know this well: one ICU study counted 64 % of 2,184 alarms as false.

1. **Bundle.** All flags go into one summary at 7 AM, with a map: each house, which bed, how many spots, today's risk. Not 40 separate messages.
2. **Only urgent alerts ring.**
   - priority = how sure × how bad × spreading (new since last week) × house risk (humidity hours).
   - Only alerts above a high bar interrupt in real time. Everything else waits for the summary.
3. **Learn from every "Not disease".**
   - Each "no" raises the bar for that kind of flag on that farm.
   - If precision drops below 8 in 10, it sends fewer alerts, not more.
4. **One tap, in Kannada, with the photo.** No reading needed. If an urgent alert is ignored for 2 h, it reminds once, then rings a second person.

## Smaller open points, also closed

- **Charging:** the rover drives onto the dock's spring contacts (24 V LiFePO4 charger), so no plugging in.
- **Remote driving:** only from the paired phone, with a PIN. The e-stop is hardware.
- **Repairs:**
  - Every part is a standard Indian-market part (hub motors, ZS-X11H, Camera Module 3, TeeJet tips).
  - The spare box holds a camera, a valve, a nozzle set and a fuse kit.
  - The tutorial shows every connection.

## Sources

- Plantix API toolkit (field vs test accuracy): https://plantix.net/en/plantix-intelligence/api-toolkit/
- PlantDoc, in-the-wild disease dataset (2,598 images, 13 species): https://arxiv.org/abs/1911.10317
- Edge anomaly detection, PatchCore-Lite: https://arxiv.org/abs/2603.20288
- LoRa in India, IN865 (865–867 MHz): https://thinkrobotics.com/blogs/learn/lorawan-gateway-setup-india-complete-deployment-guide-for-2025
- TP-Link TL-MR100 (Flipkart listing): https://flipkart.com/tp-link-tl-mr100-4g-router-2-4-ghz-300-mbps-wifi-speed-single-band-external-antenna-ethernet-cable-broadband/p/itm4895648c057cc
- ICU false alarms (64 %): https://pmc.ncbi.nlm.nih.gov/articles/PMC4756058/
