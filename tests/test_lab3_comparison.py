import copy,importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'container/compare-results.py'
spec=importlib.util.spec_from_file_location('comparison',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ComparisonTests(unittest.TestCase):
    def sample(self):
        return {'test':'load','status':'measured','overall':{'avg_ms':10,'p95_ms':20,'error_rate':0},'summary':{'phases':[{'seconds':270,'target':100}], 'thinkSeconds':.5,'baseUrl':'http://localhost:4567','verificationOnly':False}}
    def test_no_docker_no_fabricated_delta(self):
        row=m.compare([self.sample()],[],{},{},{})['rows'][1]
        self.assertEqual(row['comparison_status'],'awaiting_docker');self.assertEqual(row['delta'],{})
    def test_valid_latency_delta(self):
        b=self.sample();d=copy.deepcopy(b);d['overall']['p95_ms']=30
        row=m.compare([b],[d],{},{},{})['rows'][1]
        self.assertEqual(row['comparison_status'],'ready');self.assertEqual(row['delta']['p95_ms_percent'],50)
    def test_different_profile_blocks_comparison(self):
        b=self.sample();d=copy.deepcopy(b);d['summary']['phases'][0]['seconds']=5
        row=m.compare([b],[d],{},{},{})['rows'][1]
        self.assertEqual(row['comparison_status'],'different_conditions');self.assertEqual(row['delta'],{})
    def test_changed_api_blocks_comparison(self):
        row=m.compare([self.sample()],[self.sample()],{},{'api_sha256':'new'},{'api_sha256':'old'})['rows'][1]
        self.assertEqual(row['comparison_status'],'different_conditions')
    def test_verification_is_not_a_baseline(self):
        b=self.sample();d=copy.deepcopy(b);d['status']='verification_only'
        self.assertEqual(m.compare([b],[d],{},{},{})['rows'][1]['delta'],{})
    def test_zero_baseline_has_no_infinite_percentage(self):self.assertIsNone(m.percentage_change(0,5))
    def test_error_change_uses_percentage_points(self):
        b=self.sample();d=copy.deepcopy(b);d['overall']['error_rate']=.03
        row=m.compare([b],[d],{},{},{})['rows'][1];self.assertEqual(row['delta']['errors_percentage_points'],3)
    def test_changed_postgresql_version_is_detected(self):
        row=m.compare([self.sample()],[self.sample()],{'postgresql_version':'PostgreSQL 18.4 on Windows'},{'postgresql_version':'PostgreSQL 18.6 on Linux'},{})['rows'][1]
        self.assertEqual(row['comparison_status'],'different_conditions')
if __name__=='__main__':unittest.main()
