"""Method-matched external R 4.4.3/metafor 4.8-0 oracle for synthetic RMST pooling.

The shipped engine computes per-study restricted means from supplied KM steps
and uses inverse-variance REML with an ad-hoc HKSJ variance floor.  This runs
independently computed R KM areas and a live metafor fit for the SAME source
rows. Synthetic reported difference-SEs are inputs, not reconstructed from
censoring, so this is NOT end-to-end clinical/censoring-aware RMST validation.
"""
import csv
import hashlib
import io
import json
import math
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RSCRIPT = ROOT / "metafor-tests" / "oracle_rmst_pool_metafor.R"
COPIES = ("assets", "docs/assets", "template/assets")

# Clearly synthetic post-event KM knots, with one *reported* difference SE
# per independent trial. All three copies receive identical raw TSV bytes.
A = (("A",0,1,1,.3), ("A",3,.8,.6,.3), ("A",6,.7,.5,.3))
B = (("B",0,1,1,.4), ("B",3,.9,.7,.4), ("B",6,.8,.6,.4))
C = (("C",0,1,1,.25), ("C",3,.6,.9,.25), ("C",6,.5,.8,.25))
D = (("D",0,1,1,.45), ("D",3,.95,.7,.45), ("D",6,.9,.6,.45))
HOMOGENEOUS = A+B
HETEROGENEOUS = A+B+C+D

JS = r"""
const S=require('./'+process.argv[1]+'/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const raw=process.argv[2],tau=Number(process.argv[3]),trials=new Map();
const lines=raw.trim().split(/\r?\n/);
if(lines.shift()!=='trial\tt\tsurv_trt\tsurv_ctl\trmst_diff_se')
  throw Error('fixture header mismatch');
for (const line of lines) {
 const x=line.split('\t');
 if(x.length!==5)throw Error('malformed fixture row');
 const [id,t,st,sc,se]=x;
 if(!trials.has(id))
   trials.set(id,{nct:id,name:id,rmst_diff_se:Number(se),km_curve:[]});
 trials.get(id).km_curve.push({t_months:Number(t),
  surv_trt:Number(st),surv_ctl:Number(sc)});
}
console.log(JSON.stringify(S.poolRMSTDiff([...trials.values()],tau)));
"""

def make_tsv(rows):
    return "trial\tt\tsurv_trt\tsurv_ctl\trmst_diff_se\n" + "".join(
        "\t".join(str(v) for v in row)+"\n" for row in rows
    )

def run_js(copy, raw, tau):
    p = subprocess.run(["node","-e",JS,copy,raw,str(tau)],cwd=ROOT,
                       text=True,capture_output=True,timeout=30,check=False)
    if p.returncode:
        raise AssertionError("shipped JS runtime error: "+p.stderr)
    return json.loads(p.stdout)

def r_process(raw,tau):
    return subprocess.run(["Rscript","--vanilla",str(RSCRIPT),str(tau)],
                          cwd=ROOT,input=raw,text=True,capture_output=True,
                          timeout=120,check=False)

def run_r(raw,tau):
    p=r_process(raw,tau)
    if p.returncode:
        raise AssertionError("external fitted R/metafor failed: "+p.stderr)
    lines=list(csv.reader(io.StringIO(p.stdout),delimiter="\t"))
    if not lines or lines.pop(0)!=[
        "TYPE","ID_OR_K","RMST_T_OR_POOLED","RMST_C_OR_CI_LO",
        "DIFF_OR_CI_HI","SE_OR_TAU2"]:
        raise AssertionError("malformed external R header: "+p.stdout)
    studies={}
    pooled=None
    for line in lines:
        if len(line)!=6:
            raise AssertionError("malformed R output row")
        if line[0]=="STUDY":
            if not line[1] or line[1] in studies:
                raise AssertionError("R duplicate/missing trial ID")
            vals=[float(v) for v in line[2:]]
            if not all(math.isfinite(v) for v in vals):
                raise AssertionError("R nonfinite per-study output")
            studies[line[1]]=vals
        elif line[0]=="POOL":
            if pooled is not None:
                raise AssertionError("R pooled more than once")
            pooled=[float(v) for v in line[1:]]
            if not all(math.isfinite(v) for v in pooled):
                raise AssertionError("R nonfinite pooled output")
        else:
            raise AssertionError("unrecognised R output type")
    if pooled is None or len(studies)!=int(pooled[0]):
        raise AssertionError("R omitted study or pooled result")
    return studies,pooled

def near(got,expected,field,rtol=2e-3,atol=2e-3):
    if not isinstance(got,(int,float)) or not math.isfinite(got) or \
       not math.isclose(got,expected,rel_tol=rtol,abs_tol=atol):
        raise AssertionError(
            f"{field} mismatch: shipped JS={got!r}, external R={expected:.17g}"
        )

def compare(js, external):
    studies,pool=external
    if js.get("error") or js.get("k")!=len(studies) or \
       len(js.get("per_study",[]))!=len(studies):
        raise AssertionError("RMST study set mismatch or unexpected refusal")
    if set(x["studlab"] for x in js["per_study"]) != set(studies):
        raise AssertionError("RMST source identities changed")
    for s in js["per_study"]:
        rt,rc,diff,se=studies[s["studlab"]]
        for field,expect in (
            ("rmst_trt",rt),("rmst_ctl",rc),
            ("rmst_diff",diff),("se",se)
        ):
            near(s[field],expect,field,rtol=1e-12,atol=1e-12)
    for field,expect in (
        ("pooled_diff",pool[1]),("ci_lo",pool[2]),
        ("ci_hi",pool[3]),("tau2",pool[4])
    ):
        near(js[field],expect,field)

class NativeRMSTMetaforOracle(unittest.TestCase):
    def test_pooled_reml_adhoc_hksj_concordance_from_same_km_source(self):
        # Two-study Q<df tests HKSJ floor; four heterogeneous studies test
        # fitted positive heterogeneity. Horizons exercise different estimands.
        for label,rows in (
            ("two_study_homogeneous",HOMOGENEOUS),
            ("four_study_heterogeneous",HETEROGENEOUS)
        ):
            raw=make_tsv(rows)
            print("RMST synthetic raw TSV SHA-256",label,
                  hashlib.sha256(raw.encode("utf-8")).hexdigest())
            for tau in (4,6):
                reference=run_r(raw,tau)
                for copy in COPIES:
                    with self.subTest(source=label,horizon=tau,copy=copy):
                        compare(run_js(copy,raw,tau),reference)

    def test_negative_invalid_reported_se_and_km_refused_in_both(self):
        bad_se=tuple((id,t,st,sc,-0.3 if id=="A" else se)
                     for id,t,st,sc,se in HOMOGENEOUS)
        bad_km=tuple((id,t,1.2 if id=="B" and t==6 else st,sc,se)
                     for id,t,st,sc,se in HOMOGENEOUS)
        for label,rows,reason in (
            ("invalid_reported_se",bad_se,"standard error"),
            ("invalid_survival_probability",bad_km,"source table")
        ):
            raw=make_tsv(rows)
            for copy in COPIES:
                with self.subTest(case=label,copy=copy):
                    js=run_js(copy,raw,6)
                    self.assertEqual(js.get("k"),0)
                    self.assertTrue(js.get("error"))
                    self.assertEqual(js.get("per_study"),[])
            r=r_process(raw,6)
            self.assertNotEqual(r.returncode,0)
            self.assertIn(reason,r.stderr)

    def test_forged_pooled_effect_fails_live_r_comparison(self):
        raw=make_tsv(HETEROGENEOUS)
        external=run_r(raw,6)
        forged=run_js("assets",raw,6)
        self.assertEqual(forged.get("k"),4)
        forged["pooled_diff"] += 0.20
        with self.assertRaisesRegex(AssertionError,"pooled_diff mismatch"):
            compare(forged,external)
