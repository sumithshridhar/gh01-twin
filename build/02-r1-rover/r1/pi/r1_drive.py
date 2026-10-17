"""Drive the R1 rover from a phone: a joystick page served by the rover itself (no internet needed). Starter code,
untested on hardware: first run it with the wheels off the ground.

  python3 r1_drive.py                      then open http://<rover-ip>:8080 on a phone on the same Wi-Fi, type the PIN
  python3 r1_drive.py --house 1 --bed 3    same, and take 6 photos every 25 cm while you drive (r1_capture.py)

The phone sends the stick position ~10 times a second. If it stops (phone locked, Wi-Fi drop), the rover stops after
0.5 s here, and the Mega stops after 0.3 s on its own anyway.
"""
import argparse
import hmac
import secrets
import threading
import time

from flask import Flask, jsonify, request, session

from r1_link import Link, load_config

ap = argparse.ArgumentParser()
ap.add_argument("--house", type=int, help="with --bed: take photos while you drive this bed's path")
ap.add_argument("--bed", type=int)
args = ap.parse_args()
cfg = load_config()
link = Link(cfg)
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
last_stick = [0.0]

PAGE = """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<title>R1</title><style>body{margin:0;background:#0b1016;color:#fff;font:600 18px system-ui;text-align:center;touch-action:none}
#pad{width:80vw;height:80vw;max-width:420px;max-height:420px;margin:20px auto;border-radius:50%;background:#17212b;position:relative}
#knob{width:30%;height:30%;border-radius:50%;background:#3ddc84;position:absolute;left:35%;top:35%}
#st{font:700 22px monospace;margin:12px} input,button{font:700 22px system-ui;padding:10px;border-radius:12px}</style>
<div id=login><p>PIN</p><input id=pin type=password inputmode=numeric><button onclick=go()>Drive</button></div>
<div id=drive style=display:none><div id=st>...</div><div id=pad><div id=knob></div></div>
<p>Gentle first. Let go = stop.</p></div>
<script>
let x=0,y=0;
async function go(){const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:pin.value})});
 if(r.ok){login.style.display='none';drive.style.display='block';loop()}else alert('Wrong PIN')}
const pad=document.getElementById('pad'),knob=document.getElementById('knob');
function move(e){const b=pad.getBoundingClientRect(),t=e.touches?e.touches[0]:e;
 x=Math.max(-1,Math.min(1,((t.clientX-b.left)/b.width-0.5)*2));y=Math.max(-1,Math.min(1,-((t.clientY-b.top)/b.height-0.5)*2));
 knob.style.left=(35+x*35)+'%';knob.style.top=(35-y*35)+'%';e.preventDefault()}
function end(){x=0;y=0;knob.style.left='35%';knob.style.top='35%'}
pad.addEventListener('touchmove',move);pad.addEventListener('touchend',end);pad.addEventListener('mousemove',e=>{if(e.buttons)move(e)});pad.addEventListener('mouseup',end);
async function loop(){try{const r=await fetch('/stick',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({x,y})});
 const s=await r.json();st.textContent=s.estop_ok?('OK  '+s.distance_m.toFixed(2)+' m'):'E-STOP';st.style.color=s.estop_ok?'#3ddc84':'#ff5a3c'}catch(e){}
 setTimeout(loop,100)}
</script>"""


@app.get("/")
def index():
    return PAGE


@app.post("/login")
def login():
    pin = str((request.get_json(silent=True) or {}).get("pin", ""))
    if hmac.compare_digest(pin, str(cfg["pin"])):
        session["ok"] = True
        return jsonify(ok=True)
    return jsonify(ok=False), 403


@app.post("/stick")
def stick():
    if not session.get("ok"):
        return jsonify(error="login"), 403
    d = request.get_json(silent=True) or {}
    x, y = float(d.get("x", 0)), float(d.get("y", 0))
    speed = 40.0                                   # % of max while learning; raise it in small steps
    left, right = (y + x) * speed, (y - x) * speed  # skid steer: turning = one side slower / backwards
    link.set_drive(left, right)
    last_stick[0] = time.time()
    return jsonify(estop_ok=link.estop_ok, distance_m=link.distance_m(), tank_ok=link.tank_ok)


def deadman():
    while True:                                    # no stick for 0.5 s -> stop
        if time.time() - last_stick[0] > 0.5:
            link.set_drive(0, 0)
        time.sleep(0.1)


if __name__ == "__main__":
    link.send("E 1")                               # close the drive-enable relay (the e-stop chain still rules)
    link.send("L g")
    threading.Thread(target=deadman, daemon=True).start()
    cap = None
    if args.house and args.bed:
        from r1_capture import Capturer
        cap = Capturer(link, cfg, args.house, args.bed)
        threading.Thread(target=cap.run, daemon=True).start()
    try:
        app.run(host="0.0.0.0", port=cfg["web_port"])
    finally:
        if cap:
            cap.stop = True
        link.close()
