"""Time Tier 2's LLM call (the exact command SubprocessLlmBackend builds) on the
real demo prompt, per setup: wall time, llama.cpp's own phase timings, CPU time
and peak RSS of each llama-completion process (os.wait4 per-child rusage)."""
import json, os, re, subprocess, sys, time
from pathlib import Path
from fleet_telemetry_model import EnrichmentCard, from_json
from talk3_pulsar_speaks_english.synthesizer import decide_scope, decide_reroute
from talk3_pulsar_speaks_english.prompting import render_synthesis_prompt
from llm_inference.structured import extract_json_object

cards=[from_json(EnrichmentCard,l) for l in open('deploy/talk3-demo-cards.jsonl') if l.strip()]
scope=decide_scope(cards); rr,det=decide_reroute(cards,scope)
prompt=render_synthesis_prompt(corridor=cards[0].corridor,scope=scope,reroute_recommended=rr,reroute_detail=det,cards=cards)
model=os.path.expanduser('~/tools/models/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf')
SETUPS={
 'default_t4': ['-t','4'],                              # what the Function runs today on a Mac: Metal GPU
 'cpu_t4':     ['-t','4','-dev','none','-ngl','0'],
 'cpu_t1':     ['-t','1','-dev','none','-ngl','0'],
}
N=int(sys.argv[1]) if len(sys.argv)>1 else 10
out=Path(sys.argv[2]); out.parent.mkdir(parents=True,exist_ok=True)
pat={k:re.compile(rf'(?<!prompt ){k} time =\s+([\d.]+) ms(?: /\s+(\d+))?') for k in ('load','prompt eval','eval','total')}
with out.open('w') as f:
    for name,flags in SETUPS.items():
        for i in range(N+1):
            # flags first, then -no-cnv: SubprocessLlmBackend's order is -m -p -n -t --temp, then extra_args
            cmd=['/usr/bin/time','-l','llama-completion','-m',model,'-p',prompt,'-n','256',*flags[:2],'--temp','0.7','-no-cnv',*flags[2:]]
            t0=time.monotonic()
            pr=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            so,se=pr.communicate()  # reaps via waitpid; get rusage separately below
            wall=time.monotonic()-t0
            rec={'setup':name,'run':i,'warmup':i==0,'wall_s':round(wall,3),'rc':pr.returncode}
            for k,r in pat.items():
                m=r.search(se)
                if m: rec[k.replace(' ','_')+'_ms']=float(m.group(1)); rec[k.replace(' ','_')+'_n']=int(m.group(2)) if m.group(2) else None
            m=re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys',se)
            if m: rec['cpu_s']=round(float(m.group(2))+float(m.group(3)),2)
            m=re.search(r'(\d+)\s+maximum resident set size',se)
            if m: rec['peak_rss_mb']=round(int(m.group(1))/2**20)
            m=re.search(r'(\d+)\s+peak memory footprint',se)
            if m: rec['peak_footprint_mb']=round(int(m.group(1))/2**20)
            try: rec['warning']=extract_json_object(so).get('spoken_warning')
            except Exception: rec['warning']=None; rec['raw']=so[-300:]
            f.write(json.dumps(rec)+'\n'); f.flush()
            print(name,i,rec['wall_s'],flush=True)
