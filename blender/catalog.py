"""The component catalog: one entry per clickable component type, grouped by system.
Used by build_library.py (grid .blend) and render_catalog.py (renders + labels JSON)."""

CATALOG = [
    ("Plants", [
        ("components.plant", "plant_seedling"),
        ("components.plant", "plant_young"),
        ("components.plant", "plant_flowering"),
        ("components.plant", "plant_fruiting"),
    ]),
    ("Irrigation", [
        ("components.irrigation", "irrigation_pump"),
        ("components.irrigation", "disc_filter"),
        ("components.irrigation", "flow_meter"),
        ("components.irrigation", "pressure_transmitter"),
        ("components.irrigation", "pressure_gauge"),
        ("components.irrigation", "solenoid_valve"),
        ("components.irrigation", "dripper"),
    ]),
    ("Fertigation", [
        ("components.fertigation", "water_tank"),
        ("components.fertigation", "mix_tank"),
        ("components.fertigation", "stock_tank"),
        ("components.fertigation", "dosing_pump"),
        ("components.fertigation", "ph_probe"),
        ("components.fertigation", "ec_probe"),
        ("components.fertigation", "flow_cell"),
        ("components.fertigation", "drain_meter"),
        ("components.fertigation", "slab_scale"),
    ]),
    ("Climate", [
        ("components.climate", "exhaust_fan"),
        ("components.climate", "cooling_pad"),
        ("components.climate", "haf_fan"),
        ("components.climate", "vent_drive"),
        ("components.climate", "fog_pump"),
        ("components.climate", "fog_nozzle"),
        ("components.lights", "led_toplight_on"),
    ]),
    ("Sensors & cameras", [
        ("components.sensors", "climate_box"),
        ("components.sensors", "par_sensor"),
        ("components.sensors", "substrate_sensor"),
        ("components.sensors", "level_sensor"),
        ("components.sensors", "weather_station"),
        ("components.sensors", "sticky_trap_cam"),
        ("components.sensors", "canopy_camera"),
    ]),
    ("Control & interface", [
        ("components.control", "control_cabinet"),
        ("components.control", "esp32_node"),
        ("components.control", "hmi_tablet"),
    ]),
    ("Robot", [
        ("components.robot", "scout_robot"),
        ("components.robot", "charging_dock"),
    ]),
]
