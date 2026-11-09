import importlib.util
import json
import pathlib
import tempfile
import unittest
import zipfile

HELPER = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'contractnli_inputs.py'
spec = importlib.util.spec_from_file_location('contractnli_inputs', HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ContractNLIPrepareTests(unittest.TestCase):
    def test_zip_nested_test_json(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            src=root/'contract-nli.zip'; out=root/'nested'/'test.json'
            sample={'documents':[{'id':1,'annotation_sets':[{'annotations':{}}], 'text':'Agreement'}], 'labels':{'nda-1':{'hypothesis':'H'}}}
            with zipfile.ZipFile(src,'w') as z:
                z.writestr('contract-nli/test.json',json.dumps(sample))
                z.writestr('contract-nli/other/unwanted.txt','do not extract')
            self.assertEqual(module.prepare(src,out),out)
            self.assertTrue(module.is_contractnli_json(out))
            self.assertFalse((root/'nested'/'other'/'unwanted.txt').exists())
    def test_invalid_json_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); src=root/'test.json'; src.write_text('{"a":1}')
            with self.assertRaises(ValueError): module.prepare(src,root/'out.json')
    def test_invalid_zip_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); src=root/'bad.zip'
            with zipfile.ZipFile(src,'w') as z:z.writestr('readme.txt','not a dataset')
            with self.assertRaises(ValueError): module.prepare(src,root/'out.json')
if __name__=='__main__':unittest.main()
