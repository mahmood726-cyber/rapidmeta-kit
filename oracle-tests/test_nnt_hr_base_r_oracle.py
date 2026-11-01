"""True version-pinned base-R vs shipped JavaScript HR-to-NNT arithmetic parity.

The input risks are synthetic fixed-time baseline risks; they are NOT
inferred clinical Kaplan-Meier probabilities. R executes at test time.
Altman & Andersen, BMJ 1999;319:1492 (doi:10.1136/bmj.319.7223.1492).
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
RSCRIPT = ROOT / "oracle-tests" / "oracle_nnt_hr_base_r.R"
CASES = (
    ("benefit", .75, .1),
    ("harm", 1.5, .1),
    ("near_benefit", 1-1e-10, .25),
    ("near_harm", 1+1e-10, .25),
    ("tiny_baseline", 1-1e-10, 1e-8),
    ("exact_null", 1., .25),
)
COPIES = ("assets", "docs/assets", "template/assets")
JS = r"""
const S = require('./'+process.argv[1]+'/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const rows = JSON.parse(process.argv[2]);
console.log(JSON.stringify(rows.map(([id,h,r])=>({case:id,...S.nntForHR(h,r)}))));
"""

def raw_tsv(rows=CASES):
    return "case\thr\tcontrol_risk\n"+"".join(
        "{}\t{:.17g}\t{:.17g}\n".format(key,h,r) for key,h,r in rows
    )

def run_r(raw):
    return subprocess.run(["Rscript","--vanilla",str(RSCRIPT)],
                          input=raw,cwd=ROOT,text=True,capture_output=True,
                          timeout=60,check=False)

def comparator():
    raw = raw_tsv()
    # Immutable synthetic byte manifest, not a hash of a clinical extraction.
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    cp = run_r(raw)
    if cp.returncode:
        raise AssertionError("Real R oracle did not run successfully: "+cp.stderr)
    reader = csv.DictReader(io.StringIO(cp.stdout),delimiter="\t")
    if reader.fieldnames != ["case","nnt","arr","tx_risk","direction"]:
        raise AssertionError("Unexpected R columns: "+cp.stdout)
    out = {}
    for row in reader:
        key = row.pop("case")
        if key in out or not key:
            raise AssertionError("Duplicate/absent R case")
        out[key] = {
            "nnt": None if row["nnt"]=="NA" else float(row["nnt"]),
            "arr": float(row["arr"]), "tx_risk": float(row["tx_risk"]),
            "direction": None if row["direction"]=="null" else row["direction"]
        }
    if set(out)!={x[0] for x in CASES}:
        raise AssertionError("R silently omitted synthetic cases")
    return out,digest

def run_js(copy):
    cp = subprocess.run(["node","-e",JS,copy,json.dumps(CASES)],
                        cwd=ROOT,text=True,capture_output=True,timeout=30,
                        check=False)
    if cp.returncode:
        raise AssertionError("Actual shipped JS failed: "+cp.stderr)
    rows=json.loads(cp.stdout)
    return {row.pop("case"):row for row in rows}

def compare(actual,expected):
    if actual.keys()!=expected.keys():
        raise AssertionError("Missing or extra source cases")
    for key in expected:
        a,b=actual[key],expected[key]
        if a["direction"]!=b["direction"]:
            raise AssertionError(key+" direction disagreement")
        for field in ("arr","tx_risk","nnt"):
            av,bv=a[field],b[field]
            if (av is None)!=(bv is None):
                raise AssertionError(key+" "+field+" finite/null mismatch")
            if av is None:
                continue
            if not (math.isfinite(av) and math.isfinite(bv) and
                    math.isclose(av,bv,rel_tol=1e-10,abs_tol=1e-24)):
                raise AssertionError("{} {} JS {:.17g} vs R {:.17g}".format(
                    key,field,av,bv))

class NativeRHRNNTOracle(unittest.TestCase):
    def test_version_pinned_numerical_parity_three_shipped_copies(self):
        reference,digest=comparator()
        self.assertEqual(digest, "a2e6481d09d385f0b0356e383c89873f02a5501069cf130661a48e63db7cc236")
        for copy in COPIES:
            with self.subTest(copy=copy):
                compare(run_js(copy),reference)
        self.assertGreater(reference["near_benefit"]["nnt"],1e10)
        self.assertGreater(reference["near_harm"]["nnt"],1e10)
        self.assertIsNone(reference["exact_null"]["nnt"])

    def test_tampered_nnt_rejected_by_independent_comparator(self):
        reference,_=comparator()
        forged=run_js("assets")
        forged["benefit"]["nnt"]=5.0
        with self.assertRaisesRegex(AssertionError,"benefit nnt"):
            compare(forged,reference)

    def test_external_r_refuses_invalid_baseline_and_effect(self):
        for rows in (
            (("bad_hr",0.,.25),),
            (("bad_risk",.75,1.0),),
            (("negative_risk",.75,-.01),),
        ):
            with self.subTest(rows=rows):
                cp=run_r(raw_tsv(rows))
                self.assertNotEqual(cp.returncode,0)
                self.assertIn("invalid NNT source values",cp.stderr)
