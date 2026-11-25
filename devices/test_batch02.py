import json, pathlib, unittest
root=pathlib.Path(__file__).resolve().parent
stage=root/'catalog_stage_v2'
base=root/'published_baseline'
class Batch02Tests(unittest.TestCase):
 def test_index(self):
  d=json.loads((stage/'index.json').read_text()); self.assertEqual((d['device_count'],d['field_count']),(4,29))
 def test_identical_poco(self):
  p='devices/poco-f5-a5138b96.json'; self.assertEqual((stage/p).read_bytes(),(base/p).read_bytes())
 def test_three_ram_variants(self):
  for id_, options in [('xiaomi-13t-d2f97199','8,12'),('xiaomi-13t-pro-e1b24b9b','12,16'),('xiaomi-14t-pro-23c6ee21','12')]:
   d=json.loads((stage/'devices'/f'{id_}.json').read_text())
   f=d['fields']['ram_options_gb']; self.assertEqual(f['value'],options); self.assertEqual(f['scope'],'model_wide')
 def test_no_sensitive_fields_added(self):
  for id_ in ['xiaomi-13t-d2f97199','xiaomi-13t-pro-e1b24b9b','xiaomi-14t-pro-23c6ee21']:
   a=json.loads((base/'devices'/f'{id_}.json').read_text())['fields']
   b=json.loads((stage/'devices'/f'{id_}.json').read_text())['fields']
   self.assertEqual(set(b)-set(a),{'ram_options_gb'})
if __name__=='__main__':unittest.main()
