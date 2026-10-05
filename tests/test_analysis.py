import gzip
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path

spec=importlib.util.spec_from_file_location('analysis',Path(__file__).resolve().parents[1]/'native/analyze-results.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class AnalysisTests(unittest.TestCase):
    def test_percentile_linear_interpolation(self):self.assertEqual(95,a.quantile([0,100]))

    def test_verification_mode_never_becomes_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'smoke-summary.json').write_text(json.dumps({'verificationOnly':True}))
            self.assertEqual('verification_only',a.analyze(p,'smoke')['status'])

    def fixture(self,p,errors=0,observed=10):
        (p/'load-summary.json').write_text(json.dumps({'verificationOnly':False,'phases':[{'seconds':30}],'summary':{'state':{'testRunDurationMs':30000}}}))
        points=[]
        for n in range(30):
            time=datetime.fromtimestamp(1700000000+n,tz=timezone.utc).isoformat()
            tags={'measured':'true','phase':'peak','target_vus':'10'}
            for metric,value in [('http_req_duration',100),('http_req_failed',int(n<errors)),('vus',observed)]:
                points.append({'type':'Point','metric':metric,'data':{'time':time,'value':value,'tags':tags}})
        with gzip.open(p/'load-metrics.json.gz','wt') as f:
            f.write('\n'.join(json.dumps(point) for point in points))

    def test_largest_level_requires_good_latency_and_error_rate(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);self.fixture(p)
            self.assertEqual(10,a.analyze(p,'load')['largest_tested_vus_within_slo'])
            self.fixture(p,errors=3)
            self.assertIsNone(a.analyze(p,'load')['largest_tested_vus_within_slo'])

    def test_configured_vus_are_not_claimed_as_achieved(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);self.fixture(p,observed=5)
            self.assertIsNone(a.analyze(p,'load')['largest_tested_vus_within_slo'])

if __name__=='__main__':unittest.main()
