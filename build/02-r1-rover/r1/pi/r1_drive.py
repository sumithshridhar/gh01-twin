"""Drive the R1 rover from a phone: a joystick page served by the rover itself (no internet needed). Starter code,
untested on hardware: first run it with the wheels off the ground.

  python3 r1_drive.py                      then open http://<rover-ip>:8080 on a phone on the same Wi-Fi, type the PIN
  python3 r1_drive.py --house 1 --bed 3    same, and take photos every 25 cm while you drive (r1_capture.py)

The phone sends the stick position ~10 times a second. If it stops (phone locked, Wi-Fi drop), the rover stops after
0.5 s here, and the Mega stops after 0.3 s on its own anyway.

13 Nov 2026 (ISSUES.md E10, securing the remote drive):
  - the PIN must be at least 6 digits and not the example one; the script refuses to start otherwise
    (v1 shipped a 4-digit example PIN and allowed unlimited guesses: 10,000 tries take minutes);
  - 5 wrong PINs lock the page for 5 minutes;
  - one driver at a time: a second phone can't take over while the first is still driving;
  - after a bumper or e-stop trip the page says so, and Resume works only after someone pressed RESET on the rover.
Also give the rover its own Wi-Fi network with its own password, so only the workers' phones can reach the page.
"""
import hmac
import secrets
import threading
import time

from flask import Flask, jsonify, request, session

WEAK_PINS = {"482600", "123456", "000000", "111111", "123123", "654321", "CHANGE-ME"}
MAX_FAILS, LOCK_S, DRIVER_IDLE_S = 5, 300, 5.0

PAGE = """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<title>R1</title><style>body{margin:0;background:#0b1016;color:#fff;font:600 18px system-ui;text-align:center;touch-action:none}
#pad{width:80vw;height:80vw;max-width:420px;max-height:420px;margin:20px auto;border-radius:50%;background:#17212b;position:relative}
#knob{width:30%;height:30%;border-radius:50%;background:#3ddc84;position:absolute;left:35%;top:35%}
#st{font:700 20px monospace;margin:12px} input,button{font:700 22px system-ui;padding:10px;border-radius:12px}</style>
<div id=login><p>PIN</p><input id=pin type=password inputmode=numeric><button onclick=go()>Drive</button></div>
<div id=drive style=display:none><div id=st>...</div><button id=res style=display:none onclick=resume()>Resume</button>
<div id=pad><div id=knob></div></div><p>Gentle first. Let go = stop.</p></div>
<script>
let x=0,y=0;
async function go(){const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:pin.value})});
 const j=await r.json();if(r.ok){login.style.display='none';drive.style.display='block';loop()}else alert(j.error)}
async function resume(){const r=await fetch('/resume',{method:'POST'});const j=await r.json();if(!r.ok)alert(j.error)}
const pad=document.getElementById('pad'),knob=document.getElementById('knob');
function move(e){const b=pad.getBoundingClientRect(),t=e.touches?e.touches[0]:e;
 x=Math.max(-1,Math.min(1,((t.clientX-b.left)/b.width-0.5)*2));y=Math.max(-1,Math.min(1,-((t.clientY-b.top)/b.height-0.5)*2));
 knob.style.left=(35+x*35)+'%';knob.style.top=(35-y*35)+'%';e.preventDefault()}
function end(){x=0;y=0;knob.style.left='35%';knob.style.top='35%'}
pad.addEventListener('touchmove',move);pad.addEventListener('touchend',end);pad.addEventListener('mousemove',e=>{if(e.buttons)move(e)});pad.addEventListener('mouseup',end);
async function loop(){try{const r=await fetch('/stick',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({x,y})});
 const s=await r.json();st.textContent=s.msg;st.style.color=s.ok?'#3ddc84':'#ff5a3c';res.style.display=s.tripped?'inline-block':'none'}catch(e){}
 setTimeout(loop,100)}
</script>"""


def pin_problem(pin):
    """Why this PIN may not be used, or None."""
    p = str(pin)
    if not (p.isdigit() and len(p) >= 6):
        return "the PIN in config.yaml must be at least 6 digits"
    if p in WEAK_PINS or len(set(p)) == 1:
        return "the PIN in config.yaml is the example or too easy to guess: change it"
    return None


def status_msg(link):
    if link.tripped:
        return "TRIPPED: check the rover, press the green RESET on it, then Resume"
    if link.batt_flat:
        return "BATTERY FLAT"
    if not link.estop_ok:
        return "E-STOP"
    v = f"{link.battery_v:.1f} V" if link.battery_v else ""
    return f"OK  {link.distance_m():.2f} m  {v}" + ("  battery low" if link.batt_low else "")


def create_app(link, cfg, clock=time.time):
    why = pin_problem(cfg.get("pin", ""))
    if why:
        raise SystemExit(f"Not starting: {why}")
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(16)
    st = {"fails": 0, "locked_until": 0.0, "driver": None, "driver_seen": 0.0, "last_stick": 0.0}
    app.config["R1_STATE"] = st

    @app.get("/")
    def index():
        return PAGE

    @app.post("/login")
    def login():
        now = clock()
        if now < st["locked_until"]:
            return jsonify(error=f"Locked after {MAX_FAILS} wrong PINs. Try again in {int(st['locked_until'] - now)} s"), 429
        pin = str((request.get_json(silent=True) or {}).get("pin", ""))
        if not hmac.compare_digest(pin, str(cfg["pin"])):
            st["fails"] += 1
            if st["fails"] >= MAX_FAILS:
                st["fails"], st["locked_until"] = 0, now + LOCK_S
            return jsonify(error="Wrong PIN"), 403
        st["fails"] = 0
        if st["driver"] and now - st["driver_seen"] < DRIVER_IDLE_S:
            return jsonify(error="Someone else is driving R1 right now"), 409
        st["driver"], st["driver_seen"] = secrets.token_hex(8), now
        session["driver"] = st["driver"]
        return jsonify(ok=True)

    def is_driver():
        return st["driver"] is not None and session.get("driver") == st["driver"]

    @app.post("/stick")
    def stick():
        if not is_driver():
            return jsonify(error="login"), 403
        now = clock()
        st["driver_seen"] = now
        d = request.get_json(silent=True) or {}
        x = max(-1.0, min(1.0, float(d.get("x", 0))))
        y = max(-1.0, min(1.0, float(d.get("y", 0))))
        speed = float(cfg.get("drive_speed_pct", 40))     # % of max while learning; raise it in small steps
        if link.tripped:
            link.set_drive(0, 0)
        else:
            link.set_drive((y + x) * speed, (y - x) * speed)   # skid steer: turning = one side slower / backwards
        st["last_stick"] = now
        ok = link.estop_ok and not link.tripped and not link.batt_flat
        return jsonify(ok=ok, tripped=link.tripped, msg=status_msg(link), distance_m=link.distance_m(),
                       battery_v=link.battery_v, tank_ok=link.tank_ok)

    @app.post("/resume")
    def resume():
        if not is_driver():
            return jsonify(error="login"), 403
        if not link.estop_ok:
            return jsonify(error="The e-stop or a bumper is still pressed"), 409
        if link.tripped and not link.latch:
            return jsonify(error="Press the green RESET on the rover first"), 409
        link.resume()
        return jsonify(ok=True)

    return app


def deadman(link, st, clock=time.time):
    while True:                                    # no stick for 0.5 s -> stop
        if clock() - st["last_stick"] > 0.5:
            link.set_drive(0, 0)
        time.sleep(0.1)


def main():
    import argparse
    from r1_link import Link, load_config
    ap = argparse.ArgumentParser()
    ap.add_argument("--house", type=int, help="with --bed: take photos while you drive this bed's path")
    ap.add_argument("--bed", type=int)
    args = ap.parse_args()
    cfg = load_config()
    why = pin_problem(cfg.get("pin", ""))
    if why:
        raise SystemExit(f"Not starting: {why}")
    link = Link(cfg)
    app = create_app(link, cfg)
    link.send("E 1")                               # close the drive-enable relay (the e-stop chain still rules)
    link.send("L g")
    threading.Thread(target=deadman, args=(link, app.config["R1_STATE"]), daemon=True).start()
    if args.house and args.bed:
        from r1_capture import Capturer
        from r1_mission import CROPS
        house = next(h for h in cfg["houses"] if h["id"] == args.house)
        prof = CROPS[house["crop"]]
        cap = Capturer(cfg, args.house, args.bed, prof["cameras"], heights=prof.get("heights"))
        link.send("F 1")                           # rings on for the whole path

        def shoot_every_25cm():
            nxt = 0.0
            while True:
                m = link.distance_m()              # wheel distance: fine for slow manual driving on firm ground
                if m >= nxt:
                    link.set_drive(0, 0)           # stop for the photos
                    cap.shoot(m)
                    nxt = m + cfg.get("photo_every_m", 0.25)
                time.sleep(0.05)
        threading.Thread(target=shoot_every_25cm, daemon=True).start()
    try:
        app.run(host="0.0.0.0", port=cfg["web_port"])
    finally:
        link.send("F 0")
        link.close()


if __name__ == "__main__":
    main()
