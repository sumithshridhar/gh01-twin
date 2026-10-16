"""GH-01 real-product catalog: one entry per line of the bill of materials.

Every part in the twin maps to a product you can buy (mostly in India), with the price we found online on
29 Sep 2026 and the page it came from. `unit` is our landed estimate in INR *including* 18 % GST
(IndiaMART B2B listings are usually quoted ex-GST, so those were multiplied by 1.18). `est=True` marks a
price we could not find listed in India (import or quote needed), so treat it as a guess.

Fields
  key      short id            comps  twin component ids it covers      sys  system group
  qty      count in the 45 m² prototype                                  unit INR each (incl. GST)
  product  brand + model we model in Blender                              spec key specs (plain words)
  dims     sizes used for the 3D model (mm)                               src  where the price came from
  alt      cheaper option: (product, unit INR, src)                      life years before replacement
  maint    yearly upkeep INR for the whole line (consumables, calibration, spares)           note anything the buyer must know
  opt      True = optional, not in the base total
"""

G = 1.18  # GST

P = [
    # ───────────────────────── structure & growing ─────────────────────────
    dict(key="structure", sys="Structure", comps=["greenhouse_structure"], qty=1, unit=130000, est=True,
         product="45 m² fan-pad polyhouse (GI tube frame, 200 µm UV film, 40-mesh insect net)",
         spec="Vendor-built. Govt norm for fan-pad houses is ₹1,400/m² (NHB); small houses cost 1.5–2× per m².",
         src="https://nhb.gov.in/pdf/Cost%20Norms.pdf", life=15, maint=4000,
         note="Film is replaced every 3–4 years (~₹60/m² of film + labour). The current 3D model uses twin-wall "
              "polycarbonate; real Indian polyhouses use UV film, so the model switches to film."),
    dict(key="vent_drive", sys="Structure", comps=["vent_drive"], qty=1, unit=32000, est=True,
         product="MAXPOWER MP-series 370 W greenhouse gearmotor + 1\" torque tube + 5 rack-and-pinion sets",
         spec="230 V, 2.6 rpm output, built-in limit switches. Opens the ridge vent.",
         src="https://www.alibaba.com/product-introduction/Gear-motor-for-greenhouse-rack-pinion_1600974221413.html",
         alt=("Manual crank winch", 3000, "local"), life=10, maint=500,
         note="Import from China (US$150–300 + freight + duty). Price is a landed estimate."),
    dict(key="rows", sys="Structure", comps=["row_1", "row_2", "row_3"], qty=3, unit=5400,
         product="Galvanised hanging gutter 6.3 m + 6 coco slabs 100×20×10 cm + hooks & twine",
         spec="Coco slabs from Pollachi (TN), ₹60 each; UV-stable bags last 1–2 crops.",
         dims=dict(slab=(1000, 200, 100)),
         src="https://www.indiamart.com/proddetail/coco-peat-grow-bag-20614323730.html", life=10, maint=700),
    dict(key="pipe_rails", sys="Structure", comps=["pipe_rails"], qty=1, unit=10500,
         product="51 mm GI pipe rails (Tata/Apollo, ~30 m) on 10 cm supports",
         spec="Same heating-pipe rail used by Dutch greenhouse trolleys; 0.55 m gauge.",
         src="local steel dealer", life=20, maint=0),
    dict(key="mains", sys="Structure", comps=["irrigation_mains"], qty=1, unit=6500,
         product="32 mm PVC-U PN10 mains (Supreme/Finolex) + fittings",
         spec="", src="local dealer", life=10, maint=300),

    # ───────────────────────── irrigation ─────────────────────────
    dict(key="pump", sys="Irrigation", comps=["irrigation_pump"], qty=1, unit=36000,
         product="Grundfos CM 3-4 horizontal multistage pump (0.5 kW, 230 V)",
         spec="Stainless steel, ~4 bar. Also feeds the fog line (the PLC never runs fog and a watering shot at once).",
         dims=dict(length=430, height=250, width=180, inlet="1\"", outlet="1\""),
         src="https://www.indiamart.com/proddetail/grundfos-pressure-pump-cm-3-4-17599176297.html",
         alt=("Kirloskar Chhotu 0.5 HP monoblock", 4200,
              "https://www.moglix.com/kirloskar-chhotu-05hp-domestic-monoblock-water-pump/mp/msn2w6byxave3f"),
         life=10, maint=1500, note="IndiaMART ₹34,402 (Pune); Bengaluru dealer ₹38,800 with a 24 L tank."),
    dict(key="disc_filter", sys="Irrigation", comps=["disc_filter"], qty=1, unit=1800, est=True,
         product="Azud Modular 100 1\" disc filter, 120 mesh (130 µm)",
         spec="Red discs stop sand and algae before the drippers.",
         src="Azud India dealer",
         alt=("Rainflow 1\" disc filter 120 mesh", 392, "https://www.amazon.in/Rainflow-Disc-irrigation-Apartment-Warranty/dp/B09Z68XGML"),
         life=8, maint=300),
    dict(key="flow_meter", sys="Irrigation", comps=["flow_meter"], qty=1, unit=1650,
         product="FEDREL 25 mm multi-jet water meter with reed pulse output",
         spec="Brass body, 1 pulse per litre → PLC counts every litre. Proves a valve really opened.",
         src="https://www.indiamart.com/proddetail/pulse-output-multi-jet-water-meter-18149404088.html",
         life=8, maint=0),
    dict(key="pressure_tx", sys="Irrigation", comps=["pressure_tx"], qty=1, unit=4500,
         product="Danfoss MBS 3000 060G1125 (0–10 bar, 4–20 mA, G¼)",
         spec="Stainless, IP65. Confirms the pump is really pushing water and the filter isn't blocked.",
         src="https://www.indiamart.com/proddetail/danfoss-pressure-transmitter-mbs-3000-060g1125-0-10-bar-22679576791.html",
         life=10, maint=0),
    dict(key="pressure_gauge", sys="Irrigation", comps=["pressure_gauge"], qty=1, unit=600,
         product="H. Guru 63 mm glycerine-filled gauge 0–10 bar, ¼\" bottom entry",
         spec="Manual check for the farmer; no electronics.", src="local dealer", life=8, maint=0),
    dict(key="zone_valve", sys="Irrigation", comps=["zone_valve_1", "zone_valve_2", "zone_valve_3"], qty=3, unit=3000,
         est=True, product="Rain Bird 100-HV 1\" solenoid valve, 24 V AC, flow control",
         spec="One per crop row. Normally closed.",
         src="https://www.amazon.in/RainBird-Solenoid-Valve-flow-control/dp/B078X9PJT7", life=8, maint=0),
    dict(key="drippers", sys="Irrigation", comps=["dripper"], qty=54, unit=18,
         product="Netafim PCJ-CNL 2 L/h pressure-compensating dripper + 4 mm arrow + 60 cm micro-tube",
         spec="Anti-drain valve, same flow at every plant.",
         src="https://www.flipkart.com/netafim-2-plh-pc-dripper-irrigation-vertical-garden-green-house-red-colour-pack-od-500-nos-drip-kit/p/itm49deabc77db8c",
         life=3, maint=0),

    # ───────────────────────── fertigation ─────────────────────────
    dict(key="water_tank", sys="Fertigation", comps=["water_tank"], qty=1, unit=6000,
         product="Sintex 500 L vertical tank (3-layer LLDPE) + brass float valve",
         spec="", dims=dict(dia=900, height=970),
         src="https://www.rocareindia.com/product/sintex-500-ltr-loft-water-tank/1390", life=10, maint=0),
    dict(key="mix_tank", sys="Fertigation", comps=["mix_tank"], qty=1, unit=4500,
         product="200 L open-top blue HDPE drum with clamp ring + 24 V brushless circulation pump",
         spec="Nutrient solution is mixed here before each watering.", dims=dict(dia=580, height=935),
         src="local drum dealer", life=8, maint=0),
    dict(key="stock_tanks", sys="Fertigation", comps=["stock_A", "stock_B", "stock_acid"], qty=3, unit=900,
         product="60 L HDPE drum with lid + suction lance and foot filter", spec="", src="local drum dealer",
         life=8, maint=0),
    dict(key="dosing", sys="Fertigation", comps=["dosing_pump_A", "dosing_pump_B", "dosing_pump_acid"], qty=3,
         unit=3459, product="Kamoer KCS Plus peristaltic pump (24 V stepper, 4 rollers, BPT tube, ~80 mL/min)",
         spec="Only the tube touches the liquid; dose = counted steps.",
         src="https://robu.in/product/kamoer-kcs-plus-4-rotor-24v-b10-sl-peristaltic-pump/", life=5, maint=1500,
         note="Tube wears out: replace yearly (~₹500 each)."),
    dict(key="ph", sys="Fertigation", comps=["ph_probe"], qty=1, unit=18000,
         product="Atlas Scientific pH kit (lab-grade probe + EZO-pH circuit + isolator + calibration fluids)",
         spec="", src="https://www.indiamart.com/proddetail/atlas-scientific-ph-kit-18327785162.html", life=1.5,
         maint=9000, note="pH probes age: expect a new probe every 12–18 months (~₹7–9k) + ₹2k of calibration fluid."),
    dict(key="ec", sys="Fertigation", comps=["ec_probe"], qty=1, unit=24000, est=True,
         product="Atlas Scientific conductivity kit K 1.0 (probe + EZO-EC + isolator)",
         spec="", src="https://atlas-scientific.com/kits/", life=5, maint=1500),
    dict(key="flow_cell", sys="Fertigation", comps=["sensor_flow_cell"], qty=1, unit=6000, est=True,
         product="Acrylic 3-port flow cell for pH + EC probes (Atlas-style)", spec="", src="estimate", life=8,
         maint=0),
    dict(key="drain_meter", sys="Fertigation", comps=["drain_meter"], qty=1, unit=6000, est=True,
         product="Tipping-bucket drain gauge (Misol WH-SP-RG-type) + drain EC cup", spec="Counts drain water from one slab.",
         src="estimate", life=6, maint=0),
    dict(key="slab_scale", sys="Fertigation", comps=["slab_scale"], qty=1, unit=10000,
         product="2 × Zemic H3G-C3-50 kg S-type load cells + weight transmitter + stainless gutter segment",
         spec="Weighs one slab + 3 plants all day: the most reliable water signal.",
         src="https://www.indiamart.com/proddetail/s-type-loadcell-24917952497.html", life=10, maint=0),
    dict(key="skid", sys="Fertigation", comps=["fertigation_skid"], qty=1, unit=8000,
         product="Galvanised skid frame + PVC mounting board + drip tray", spec="Holds pump, filter, meters, dosing and probes.",
         src="local fabricator", est=True, life=12, maint=0),
    dict(key="level", sys="Fertigation", comps=["level_water_tank", "level_mix_tank", "level_pond"], qty=3, unit=1721,
         product="DFRobot A02YYUW waterproof ultrasonic distance sensor (IP67, 3–450 cm)",
         spec="", src="https://robu.in/product/dfrobot-a02yyuw-waterproof-ultrasonic-sensor/", life=5, maint=0),
    dict(key="float", sys="Fertigation", comps=["float_switch"], qty=3, unit=450,
         product="Vertical reed float switch (PP, NO/NC)",
         spec="One is wired straight into the pump contactor coil: hardware dry-run cut-off.",
         src="https://dir.indiamart.com/impcat/magnetic-float-switch.html", life=5, maint=0),

    # ───────────────────────── climate ─────────────────────────
    dict(key="exhaust_fan", sys="Climate", comps=["exhaust_fan_1", "exhaust_fan_2"], qty=2, unit=32000, est=True,
         product="Vostermans Multifan 4E50 wall fan (50 cm, 420 W) + gravity shutter",
         spec="~7,000 m³/h each at 50 Hz. Two fans ≈ 12,000 m³/h at 30 Pa: right-sized for 45 m², and one fan "
              "still cools if the other fails.",
         dims=dict(panel=647.5, mount=600, opening=540, motor_depth=192, E=84),
         src="https://cdn11.bigcommerce.com/s-44t8fz8vq4/content/pdf/Multifan%20Dimensional%20Diagram.pdf",
         alt=("Indian 36\" poultry box fan (one fan, oversized)", 17000,
              "https://www.indiamart.com/proddetail/36-inch-poultry-exhaust-fans-2856403308773.html"),
         life=12, maint=600, note="No Indian price listed: import quote needed. Old model said 2 × 30\" fans at "
                                  "4,500 m³/h; a real 30\" box fan (Munters EM30) moves ~14,000 m³/h, so that was 3× too much air."),
    dict(key="pad", sys="Climate", comps=["cooling_pad"], qty=1, unit=17000,
         product="Munters CELdek 7090-15 pad 2.4 × 0.9 m + aluminium frame/gutter + Kirloskar Chhotu 0.5 HP pad pump",
         spec="150 mm cellulose honeycomb; air enters here and cools by evaporation.",
         dims=dict(width=2400, height=900, depth=150),
         src="https://www.indiamart.com/proddetail/poly-house-cooling-pads-16123553091.html", life=5, maint=1200,
         note="Pads last 3–5 years (₹140–150 per sq ft). Pump ₹4.2k (Moglix)."),
    dict(key="haf", sys="Climate", comps=["haf_fan_1", "haf_fan_2"], qty=2, unit=18000, est=True,
         product="Vostermans Multifan greenhouse circulation fan (45 cm, ~5,000 m³/h)",
         spec="Keeps air moving so leaves stay dry and temperature is even.",
         src="https://www.vostermans.com/hubfs/Brochures/Fans/Horizontal%20Circulation%20Fans/Greenhouse/Multifan%20Greenhouse%20Circulation%20fan%20EN.pdf",
         alt=("Indian polyhouse circulation fan 80 W", 9700,
              "https://www.tradeindia.com/products/air-circulation-fan-c8811476.html"),
         life=10, maint=0),
    dict(key="fog", sys="Climate", comps=["fog_nozzle", "fog_line"], qty=6, unit=350,
         product="Netafim CoolNet Pro 4-way fogger + anti-leak valve + 30 cm hanger & weight",
         spec="65 µm droplets at 4 bar, 30 L/h each (4 nozzles × 7.5 L/h); one fogger per ~8 m².",
         src="https://www.amazon.in/AQUA-AGRO-FOGGER-Assembly-polyhouse-Poultry/dp/B0CJFFZF93", life=4, maint=300),
    dict(key="fog_station", sys="Climate", comps=["fog_pump"], qty=1, unit=8500, est=True,
         product="Fog valve station: Rain Bird 100-HV valve + Azud ¾\" disc filter + Senninger PRLG-60 (4.1 bar) "
                 "regulator + gauge + 16 mm PE fog line",
         spec="Fed by the main pump; replaces the old 70-bar fog pump (₹35–60k).", src="estimate", life=8, maint=300),
    dict(key="led", sys="Climate", comps=["led_toplight"] + [f"led_r{r}_{k}" for r in (1, 2, 3) for k in (1, 2)],
         qty=6, unit=70000, est=True, opt=True,
         product="Philips GreenPower LED toplighting (600 W class)",
         spec="NOT needed in Karnataka sun for tomato. Removed from the 3D model on 6 Oct 2026 (Sumith's call); "
              "kept here only as a nursery option.",
         src="estimate", life=12, maint=0),

    # ───────────────────────── sensors & cameras ─────────────────────────
    dict(key="climate_box", sys="Sensors", comps=["climate_box_1", "climate_box_2"], qty=2, unit=12000,
         product="7Semi RS485 SHT45 probe + DFRobot RS485 NDIR CO₂ sensor in a fan-aspirated shield",
         spec="Air temp ±0.1 °C, RH ±1 %, CO₂ 400–5000 ppm. Two boxes = cross-check for the PLC.",
         src="https://robu.in/product/dfrobot-industrial-rs485-infrared-co2-sensor/", life=6, maint=500),
    dict(key="par", sys="Sensors", comps=["par_sensor"], qty=1, unit=7300,
         product="Renke RS-GH-N01-AL PAR sensor (RS485, 0–2500 µmol/m²/s)",
         spec="Measures the light plants use; drives watering and shade.",
         src="https://robu.in/product/photosynthetically-active-radiation-par-sensor-type-rs485/", life=6, maint=0),
    dict(key="substrate", sys="Sensors", comps=["substrate_sensor"], qty=1, unit=7000,
         product="Renke RS485 3-in-1 substrate sensor (moisture, temperature, EC)",
         spec="", src="https://www.indiamart.com/proddetail/soil-temperature-humidity-moisture-sensor-with-rs485-modbus-output-23833702130.html",
         alt=("METER TEROS 12 (research grade)", 30000, "estimate"), life=5, maint=0),
    dict(key="weather", sys="Sensors", comps=["weather_station"], qty=1, unit=35000, est=True,
         product="Renke RS485 mast: cup anemometer + wind vane + tipping rain gauge + louvered T/RH + pyranometer",
         spec="Outside conditions: wind closes vents, rain closes vents, sunlight plans watering.",
         src="https://www.indiamart.com/embsys/weather-sensor.html",
         alt=("Misol WH-SP-WS01 + WH-SP-RG hobby set", 8000, "estimate"), life=8, maint=500),
    dict(key="sticky_cam", sys="Sensors", comps=["sticky_trap_1", "sticky_trap_2", "sticky_trap_3"], qty=3, unit=7000,
         product="Raspberry Pi Zero 2 W + Camera Module 3 + Adafruit TPL5110 timer + MT3608 boost + 18650 cell + "
                 "5 V LED ring (IRLZ44N switch) + IP65 box with acrylic window + yellow sticky card",
         spec="Wakes every hour (TPL5110), photographs the card at 20 cm, uploads it, powers off: ~1 % awake, "
              "~3 weeks per 18650 charge. The farm's Pi 5 + AI HAT+ counts the new catches.",
         src="https://www.thingbits.in/products/raspberry-pi-camera-module-3", life=5, maint=1400,
         note="Pi Zero 2 W ₹1,770, Camera Module 3 ₹3,158 (Thingbits). TPL5110 ~₹750 (import), MT3608 ₹50, 18650 + holder "
              "₹300, LED ring ₹150, MOSFET/resistors/board ₹120, box + window ₹350, microSD ₹350 (estimates). "
              "14 Oct 2026: battery + timer replaced the solar idea (tutorial 1, tutorials/01-pest-camera). Cards ~₹25."),
    dict(key="canopy_cam", sys="Sensors", comps=["canopy_camera_1", "canopy_camera_2"], qty=2, unit=3000,
         product="Hikvision DS-2CD1023G2-LIU 2 MP PoE bullet camera",
         spec="Growth time-lapse and canopy cover. Powered over the network cable.",
         src="https://www.flipkart.com/hikvision-2mp-outdoor-bullet-ip-ds-2cd1023g2-liu-color-vision-motion-detection-mic-security-camera/p/itm81845f4409a2d",
         life=6, maint=0),

    # ───────────────────────── control ─────────────────────────
    dict(key="cabinet", sys="Control", comps=["control_cabinet"], qty=1, unit=113000,
         product="EC Box 800×1000×300 IP65 steel cabinet: Arduino Opta RS485 PLC, Raspberry Pi 5 8 GB + AI HAT+ 26 TOPS, "
                 "Schneider TeSys contactors & MPCBs, RCCB, E-stop, 35 °C hard-wired fan thermostat, 4G router, DC UPS",
         spec="The AI runs on the Pi and only suggests; the Opta PLC owns every relay; the thermostat, float switch and "
              "E-stop work even if both are off.",
         dims=dict(width=600, height=800, depth=250),
         src="https://robocraze.com/products/official-arduino-opta-rs485", life=10, maint=2000,
         note="Opta ₹18,060 · Pi 5 8 GB ₹19,999 (2026 RAM-shortage price) · AI HAT+ ₹14,769 · cabinet ≈₹16k · "
              "6 × LC1D09 ₹4.5k · 3 × GV2ME ₹5.3k · rest ₹34k."),
    dict(key="esp32", sys="Control", comps=["esp32_node_fert", "esp32_node_crop"], qty=2, unit=2800,
         product="Waveshare ESP32-S3-RS485-CAN (DIN-rail case) in an IP65 box",
         spec="Field node: reads RS485 sensors, talks MQTT over Wi-Fi.",
         src="https://www.waveshare.com/esp32-s3-rs485-can.htm", life=6, maint=0),
    dict(key="tablet", sys="Control", comps=["farmer_tablet"], qty=1, unit=49999, opt=True,
         product="Samsung Galaxy Tab Active5 (8\", IP68, rugged) on a wall bracket",
         spec="Optional: the farmer's own phone runs the same app.",
         src="https://news.samsung.com/in/samsung-launches-galaxy-tab-active5-in-india-rugged-5g-enabled-tablet-built-for-enterprise-workforce",
         life=5, maint=0),
    dict(key="poe", sys="Control", comps=[], qty=1, unit=3000, product="TP-Link TL-SG1005P PoE switch",
         spec="Powers the 2 canopy cameras.", src="amazon.in", life=6, maint=0),

    # ───────────────────────── robot ─────────────────────────
    dict(key="robot", sys="Robot", comps=["scout_robot"], qty=1, unit=182000,
         product="GH-01 scout (our build): NVIDIA Jetson Orin Nano Super, 2 × Luxonis OAK-D Lite, "
                 "2 × Robokits RMCS-2071 24 V BLDC gearmotors (rails), 4 × 127 mm mecanum wheels + 24 V encoder "
                 "gearmotors (path), 24 V 50 Ah LiFePO4, NEMA 23 belt lift, 40×40 aluminium frame, 12 V air pump for pollination",
         spec="Rides the pipe rails, changes rows on its own on the concrete path, photographs every plant, pulses air at open flowers.",
         src="https://www.indiamart.com/proddetail/nvidia-jetson-orin-nano-super-developer-kit-2859303114497.html",
         life=6, maint=6000,
         note="Jetson ₹38k · 2 × OAK-D Lite ₹56k · rail motors + drivers ₹18.5k · battery ₹18k · lift ₹8k · frame ₹12k · "
              "grooved rail wheels ₹4k · mecanum path drive ₹16k (4 wheels + 4 encoder gearmotors + 2 drivers, estimate) · "
              "air pump ₹2k · IO, bumpers, E-stop, DC-DC ₹9k. 14 Oct 2026: the 2 rubber hub wheels (₹2k of the old ₹6k "
              "wheels line) were replaced by the mecanum drive: they could not hold the robot up on the path or move it "
              "between aisles."),
    dict(key="dock", sys="Robot", comps=["robot_dock"], qty=1, unit=12000,
         product="24 V 10 A LiFePO4 charger + spring copper contacts on a GI post",
         spec="", src="estimate", life=8, maint=0),

    # ───────────────────────── farm site (added 6 Oct 2026) ─────────────────────────
    dict(key="solar_pv", sys="Power", comps=["solar_array"], qty=6, unit=14580,
         product="Waaree 540 W mono-PERC half-cut module (144 half cells)",
         spec="3.24 kWp on the packhouse roof, south at 13°: ~14 kWh on a clear Kolar day, enough for a hot day's fans + pad.",
         dims=dict(length=2279, width=1134, depth=35),
         src="https://m.indiamart.com/stellar-power/solar-panel.html", life=25, maint=1000,
         note="Listings run ₹12,000–16,000 per 540 W panel. Why solar: Karnataka gives farm pump-set feeders 7 h of "
              "three-phase power a day (cut to 3 h or less in droughts), but the fans are needed all afternoon "
              "(https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fnow-erratic-power-supply-hits-drought-stricken-farmers-in-karnataka-2726364)."),
    dict(key="solar_mount", sys="Power", comps=[], qty=1, unit=15000, est=True,
         product="Aluminium rails, L-feet, clamps, 4 mm² DC cable, MC4 connectors, earthing",
         spec="", src="estimate", life=25, maint=0),
    dict(key="inverter", sys="Power", comps=["hybrid_inverter"], qty=1, unit=34399,
         product="MuscleGrid Focus Series 3.6 kW 48 V hybrid solar inverter",
         spec="MPPT charger + pure-sine inverter + grid charger; switches to battery in a power cut.",
         src="https://pricehistory.app/p/focus-series-hybrid-solar-inverter-3-6-a2Fw5ISj", life=10, maint=0,
         note="Amazon price ₹34,399 (Jun 2026)."),
    dict(key="battery", sys="Power", comps=["battery_bank"], qty=1, unit=73750,
         product="Hykon HiLIFE 48 V 100 Ah LiFePO4 battery (5.12 kWh)",
         spec="~3–4 h of full cooling (2 fans + pad pump + controller) through a power cut. 5-year warranty.",
         src="https://www.hykonindia.com/product/hykon-hilife-48v-100ah-lifepo4-battery",
         alt=("Aqueouss 48 V 100 Ah LiFePO4", 57000, "https://m.indiamart.com/aqueouss"), life=10, maint=0),
    dict(key="power_panel", sys="Power", comps=["power_panel"], qty=1, unit=12000, est=True,
         product="IP65 AC + DC distribution boxes (MCBs, type-2 surge arresters) + earthing pit",
         spec="", src="estimate", life=15, maint=0),
    dict(key="farm_wiring", sys="Power", comps=[], qty=1, unit=15000, est=True,
         product="~20 m armoured cable packhouse → greenhouse cabinet, in a trench",
         spec="", src="estimate", life=20, maint=0),
    dict(key="farm_pond", sys="Water", comps=["farm_pond"], qty=1, unit=30000, est=True,
         product="8 × 8 × 3 m dug farm pond + 500 µm HDPE geomembrane (~125 m²) + stone inlet apron",
         spec="≈85 m³ full. Liner ₹99–132 per m² (IndiaMART) ≈ ₹16k incl. GST; digging ≈ 10 JCB hours ≈ ₹12k.",
         src="https://m.indiamart.com/proddetail/hdpe-geomembrane-farm-pond-liner-sheet-26795318291.html",
         life=8, maint=1000,
         note="Karnataka's Krishi Bhagya scheme pays 80 % (90 % for SC/ST) of a 12 × 12 × 3 m farm pond and supports "
              "the liner (https://schemesinindia.in/schemes/karnataka/krishi-bhagya-yojana-karnataka)."),
    dict(key="pond_fence", sys="Water", comps=["pond_fence"], qty=1, unit=56000, est=True,
         product="1.8 m GI chain-link on cement posts round the pond (~47 m) + lockable gate",
         spec="A farm pond is a drowning risk: fence it. ~155 running ft × ₹360/ft incl. cement poles.",
         src="https://m.indiamart.com/tools-hardware/chain-link-fencing.html",
         alt=("Barbed wire on cement poles", 20000, "estimate"), life=15, maint=500),
    dict(key="pond_pump", sys="Water", comps=["pond_pump"], qty=1, unit=9000, est=True,
         product="Kirloskar Chhotu 0.5 HP + foot valve + 32 mm PVC (~25 m) + screen filter",
         spec="Pond → 500 L tank, only while the pond is above 20 %.",
         src="https://www.moglix.com/kirloskar-chhotu-05hp-domestic-monoblock-water-pump/mp/msn2w6byxave3f", life=8, maint=300),
    dict(key="rain", sys="Water", comps=["rain_harvest"], qty=1, unit=9000, est=True,
         product="2 × 110 mm PVC downpipes + ~20 m 110 mm PVC to the pond + first-flush chamber (90 mm)",
         spec="~50 m² of roof × ~750 mm of rain a year ≈ 30–35 m³ a year from the roof alone.",
         src="https://m.indiamart.com/catalyst-solutions-chennai", life=15, maint=200,
         note="First Flush Carrot 90 mm ₹934; downpipe diverter kit ₹1,579 (IndiaMART)."),
    dict(key="source_valves", sys="Water", comps=["source_valves"], qty=2, unit=2500, est=True,
         product="1-inch 24 V motorised ball valve (pond line / borewell line)", spec="", src="estimate", life=8, maint=0),
    dict(key="entry_room", sys="Structure", comps=["entry_room"], qty=1, unit=35000, est=True,
         product="Double-door entry room 2 × 1.9 m: GI frame, 40-mesh net, film apron, spring outer door, footbath tray, "
                 "2 door contacts",
         spec="Government polyhouse tenders specify an 'anteroom with disinfection pond and double door entry'.",
         src="https://accer.kau.in/sites/default/files/tenders/poly_house_tender_notice-2.pdf", life=10, maint=2400,
         note="Footbath disinfectant ≈ ₹200 a month."),
    dict(key="shade_net", sys="Climate", comps=["shade_net"], qty=1, unit=52000, est=True,
         product="Retractable external aluminet 50 % shade screen (~60 m²) on stainless wires + GI posts + 370 W gearmotor drive",
         spec="Reflects about half the sun before it reaches the roof: fans and pad work less (power + water).",
         src="https://m.indiamart.com/apexgreen/shade-net.html", life=6, maint=1500,
         note="Aluminet ₹110/m² ≈ ₹7.8k incl. GST; posts + wires ≈ ₹12k; gearmotor ≈ ₹32k (same import as the vent drive)."),
    dict(key="packhouse", sys="Farm", comps=["packhouse"], qty=1, unit=90000, est=True,
         product="6 × 4 m GI-frame packhouse: corrugated GI roof (carries the solar), brick half-walls + mesh, "
                 "plastered north wall, rolling shutter, 15 cm plinth",
         spec="Shade for harvest, sorting and the cool chamber; houses the inverter and battery.",
         src="https://dirhorti.assam.gov.in/sites/default/files/swf_utility_folder/departments/horticulture_medhassu_in_oid_5/menu/information_and_services/Post%20Harvest%20Management_0.pdf",
         life=20, maint=2000,
         note="MIDH pack-house norm: 9 × 6 m, ₹4 L per unit, 50 % assistance (the subsidised size is bigger than ours)."),
    dict(key="cool_chamber", sys="Farm", comps=["cool_chamber"], qty=1, unit=7115,
         product="IARI zero-energy cool chamber (double brick wall, wet river sand, bamboo + khus lid)",
         spec="No power. Tomatoes kept 14–15 days instead of 7 in a room (ICAR study).",
         src="https://epubs.icar.org.in/index.php/AAZ/article/view/139887", life=5, maint=1000),
    dict(key="pack_station", sys="Farm", comps=["pack_station"], qty=1, unit=19500, est=True,
         product="SS sorting table 2.0 × 0.9 m + Phoenix NEP-100 100 kg platform scale + 12 ventilated crates",
         spec="Scale ₹5,920 (GeM); table ≈ ₹8k; crates ≈ ₹450 each.",
         src="https://org.gem.gov.in/cart/cart_global/directBuy/95895", life=8, maint=500),

    # ───────────────────────── farm v4 (11 Oct 2026) ─────────────────────────
    dict(key="drain_recycle", sys="Fertigation", comps=["drain_recycle"], qty=1, unit=38000, est=True,
         product="Drain recycling skid: 200 L HDPE sump + float, 0.5 HP transfer pump, 120-mesh screen filter, "
                 "55 W UV-C steriliser (SS 304, ~2,000 L/h), in-line drain EC/pH probe, 32 mm header + 25 mm return line, canopy",
         spec="Recycles ~35 L a day of drain water (≈25 % drain) into the mix tank, capped at 30 % of each batch. Tomato "
              "growers dose ~250 mJ/cm² of UV-C on drain water (ToBRFV and other pathogens).",
         src="https://www.greentech.nl/news/circular-horticulture/disinfecting-drain-water-which-method-to-use", life=8, maint=2500,
         note="UV unit ≈ ₹15k (IndiaMART SS chamber ₹20k; 55 W 2,725 L/h units sell for ~AU$48 abroad); pump ≈ ₹6k; filter "
              "≈ ₹2k; probe ≈ ₹6k; sump + pipes + canopy ≈ ₹9k. UV lamp replaced yearly (≈ ₹2k)."),
    dict(key="windbreak", sys="Farm", comps=["windbreak"], qty=1, unit=6000, est=True,
         product="2-row casuarina shelterbelt, 3 m apart, on the west + north-west sides (44 seedlings + pits + drip line)",
         spec="Strong winds come from the W/SW (pre-monsoon) and NW (winter) in Karnataka; a 40–60 % porous belt "
              "shelters ~10× its height downwind.",
         src="https://www.organicmandya.com/farming/methods/wind-damage-prevention-farm/", life=25, maint=1000,
         note="Casuarina seedling ≈ ₹4 (FCRI/TNAU price list); most of the cost is digging and the drip line."),
    dict(key="comms_mast", sys="Control", comps=["comms_mast"], qty=1, unit=38000, est=True,
         product="6 m GI mast + guy wires, Teltonika RUT241 4G router in an IP65 box, 8 dBi outdoor omni antenna, "
                 "copper lightning rod + down-conductor + earth pit, backup 2G SMS modem (2nd operator SIM), 12 V beacon + siren",
         spec="Every farmer alert leaves over 4G; the rod protects the solar array and the house.",
         src="https://bechtle.com/be/shop/teltonika-rut241-industrial-4g-router--4831521--p", life=10, maint=2400,
         note="RUT241 ≈ €148 ex-VAT in Europe (≈ ₹14k in India via distributors); data SIM ≈ ₹200 a month."),
    dict(key="vermicompost", sys="Farm", comps=["vermicompost"], qty=1, unit=12000, est=True,
         product="2 × 12 × 4 × 2 ft HDPE vermibeds (450 GSM) + GI posts + 50 % shade-net roof + earthworms",
         spec="Crop residue → vermicompost for the farm's field crops; diseased leaves are bagged and removed instead.",
         src="https://m.indiamart.com/impcat/vermi-beds.html", life=5, maint=500,
         note="Vermibeds ₹1,030–1,500 each on IndiaMART; TNAU costs a full 25 t/yr unit at ₹60k with 50 % subsidy."),

    # ───────────────────────── install ─────────────────────────
    dict(key="install", sys="Install", comps=[], qty=1, unit=45000, est=True,
         product="Wiring & conduit, plumbing labour, transport",
         spec="Our own time for software and commissioning is not counted.", src="estimate", life=15, maint=0),
]

CONTINGENCY = 0.10  # prices move; small orders pay freight


def line_total(p):
    return p["qty"] * p["unit"]


def totals(include_optional=False):
    by_sys = {}
    for p in P:
        if p.get("opt") and not include_optional:
            continue
        by_sys[p["sys"]] = by_sys.get(p["sys"], 0) + line_total(p)
    sub = sum(by_sys.values())
    return by_sys, sub, round(sub * CONTINGENCY), round(sub * (1 + CONTINGENCY))


if __name__ == "__main__":
    by_sys, sub, cont, tot = totals()
    for k, v in by_sys.items():
        print(f"{k:12s} ₹{v:>10,}")
    print(f"{'subtotal':12s} ₹{sub:>10,}\n{'+10 % cont.':12s} ₹{cont:>10,}\n{'TOTAL':12s} ₹{tot:>10,}")
    no_robot = sub - by_sys["Robot"]
    print(f"without robot: ₹{round(no_robot * 1.1):,}")
    print("optional:", sum(line_total(p) for p in P if p.get("opt")))
    base = [p for p in P if not p.get("opt")]
    print("yearly upkeep (consumables, calibration):", sum(p["maint"] for p in base))
    print("yearly wear-out (price / life):", round(sum(line_total(p) / p["life"] for p in base)))
