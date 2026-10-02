import json, subprocess, sys, time, pathlib, concurrent.futures as cf
FIX = pathlib.Path("/Users/minhtran/Documents/minhtran3124/developer/harness-skills/evals/skills/review-chain/fixtures")
OUT = pathlib.Path(sys.argv[1]); arm, model, effort = sys.argv[2:5]
NEUTRAL = sys.argv[5]
PROMPT = """You are a blind code reviewer running two oracles over one change.

1. CORRECTNESS: find runtime bugs (code that crashes or returns a wrong result). Each finding names a trigger and the wrong outcome.
2. INTENT: compare the diff to the user's request. Report gaps (asked, missing), drift (done differently) and excess (not asked for).

Ignore style. For every finding give: oracle (correctness|intent), class, file:line, one-line reason, and a self-reported confidence 0-100 that it is real. If you find nothing, say "no defects found" and list what you checked.

## User request (intent.md)
{intent}

## Diff (diff.patch)
{diff}
"""
def run(fx):
    p = PROMPT.format(intent=(fx/"intent.md").read_text(), diff=(fx/"diff.patch").read_text())
    t=time.monotonic()
    r = subprocess.run(["claude","-p",p,"--tools","","--model",model,"--effort",effort,"--output-format","json","--no-session-persistence"],cwd=NEUTRAL,capture_output=True,text=True)
    ev = json.loads(r.stdout) if r.stdout.strip() else []
    res = ev if isinstance(ev,dict) else next((e for e in reversed(ev) if e.get("type")=="result"),{})
    return fx.name, {"rc":r.returncode,"elapsed":round(time.monotonic()-t,1),"result":res.get("result",""),"usage":res.get("usage",{}),"model_usage":list((res.get("modelUsage") or {}).keys()),"stderr":r.stderr[-500:]}
fxs=sorted(p for p in FIX.iterdir() if (p/"diff.patch").exists())
with cf.ThreadPoolExecutor(7) as ex: out=dict(ex.map(run,fxs))
OUT.write_text(json.dumps({"arm":arm,"model":model,"effort":effort,"client":subprocess.check_output(["claude","--version"],text=True).strip(),"cases":out},indent=2))
print(OUT, {k:v["rc"] for k,v in out.items()})
