"""Genuine R 4.4.3 vs shipped JS synthetic Kaplan-Meier step-area parity.

This is ONLY deterministic restricted-mean step integral arithmetic.
No censoring-aware variance, pooled REML/HKSJ R comparison, or independently
sourced clinical effects are tested. R must execute; no stored R snapshots.
"""
import csv
import io
import json
import math
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RSCRIPT=ROOT/"oracle-tests"/"oracle_rmst_km_step.R"
ROWS=(
 ("A",0,1,1),("A",3,.8,.6),("A",6,.7,.5),
 ("B",0,1,1),("B",3,.9,.7),("B",6,.8,.6),
)
JS=r"""
const S=require('./'+process.argv[1]+'/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const rows=JSON.parse(process.argv[2]),tau=Number(process.argv[3]),d=new Map();
for(const [id,t,st,sc] of rows){
 if(!d.has(id))d.set(id,{name:id,rmst_diff_se:id==='A'?.3:.4,km_curve:[]});
 d.get(id).km_curve.push({t_months:t,surv_trt:st,surv_ctl:sc});
}
console.log(JSON.stringify(S.poolRMSTDiff([...d.values()],tau)));
"""

def run_js(copy,tau):
    cp=subprocess.run(["node","-e",JS,copy,json.dumps(ROWS),str(tau)],
         cwd=ROOT,text=True,capture_output=True,timeout=30,check=True)
    out=json.loads(cp.stdout)
    if out.get("error") or out.get("k")!=2:
        raise AssertionError("shipped JS refused the eligible synthetic curves")
    return out

def r_process(rows,tau):
    tsv="trial\tt\tsurv_trt\tsurv_ctl\n"+"".join(
        "%s\t%s\t%s\t%s\n"%row for row in rows)
    return subprocess.run(["Rscript","--vanilla",str(RSCRIPT),str(tau)],
        input=tsv,cwd=ROOT,text=True,capture_output=True,timeout=60,check=False)

def run_r(rows,tau):
    cp=r_process(rows,tau)
    if cp.returncode:
        raise AssertionError("real R oracle error (not skipped): "+cp.stderr)
    reader=csv.DictReader(io.StringIO(cp.stdout),delimiter="\t")
    if reader.fieldnames!=["trial","rmst_trt","rmst_ctl","rmst_diff"]:
        raise AssertionError("incorrect independent R columns: "+cp.stdout)
    out={}
    for record in reader:
        id=record.pop("trial")
        if id in out or not id:
            raise AssertionError("duplicate or missing R trial ID")
        values={k:float(v) for k,v in record.items()}
        if not all(math.isfinite(v) for v in values.values()):
            raise AssertionError("nonfinite R area result")
        out[id]=values
    if set(out)!={"A","B"}:
        raise AssertionError("R omitted one or more source study")
    return out

def compare_per_study(js,ref):
    for row in js["per_study"]:
        expected=ref[row["studlab"]]
        for field in ("rmst_trt","rmst_ctl","rmst_diff"):
            observed,wanted=row[field],expected[field]
            if not math.isclose(observed,wanted,rel_tol=1e-12,abs_tol=1e-12):
                raise AssertionError(
                    "%s: JS %.17g vs R %.17g"%(field,observed,wanted))

class NativeRKMOracle(unittest.TestCase):
    def test_synthetic_step_area_at_two_horizons_in_three_shipped_copies(self):
        for tau in (4,6):
            reference=run_r(ROWS,tau)
            for copy in ("assets","template/assets","docs/assets"):
                with self.subTest(tau=tau,copy=copy):
                    compare_per_study(run_js(copy,tau),reference)
        # No pooled CI/se comparison; the input SEs are synthetic.

    def test_negative_original_trapezoid_area_is_not_accepted(self):
        reference=run_r(ROWS,6)
        shipped=run_js("assets",6)
        forged=json.loads(json.dumps(shipped))
        forged["per_study"][0]["rmst_diff"]=0.9
        with self.assertRaisesRegex(AssertionError,"rmst_diff"):
            compare_per_study(forged,reference)

    def test_r_oracle_refuses_invalid_survival_and_truncated_support(self):
        bad=tuple((id,t,st,1.1 if id=="A" and t==3 else sc)
                  for id,t,st,sc in ROWS)
        cp=r_process(bad,6)
        self.assertNotEqual(cp.returncode,0)
        self.assertIn("invalid KM source table",cp.stderr)
        cp=r_process(ROWS,7)
        self.assertNotEqual(cp.returncode,0)
        self.assertIn("support",cp.stderr)
