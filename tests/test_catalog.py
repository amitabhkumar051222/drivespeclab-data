import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
catalog=load('generate_database_catalog')
watch=load('watch_official_sources')

class CatalogTests(unittest.TestCase):
    def test_unknown_powertrain_not_gas(self):
        self.assertEqual(catalog.fuel_types(''),[])
    def test_mixed_hybrid(self):
        self.assertEqual(catalog.fuel_types('Gas / Hybrid / Plug-in Hybrid'),['Plug-in Hybrid','Hybrid','Gas'])
    def test_display_name_preserves_routing(self):
        row=catalog.make_row('Ram',{'name':'Ram 1500','year':'2026'}, {}, {})
        self.assertEqual(row['display_name'],'Ram 1500')
        self.assertEqual(row['model'],'Ram 1500')
    def test_transmission_available_to_finder(self):
        row=catalog.make_row('Honda',{'name':'CR-V'}, {'transmission':'CVT'}, {})
        self.assertEqual(row['transmission'],'CVT')

class MonitorTests(unittest.TestCase):
    def test_failure_preserves_baseline_and_unreviewed_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'state.json'; pending=Path(tmp)/'pending.json'
            state.write_text(json.dumps({'sources':{'https://example.com':{'fingerprint':'old','status':200}}}))
            pending.write_text(json.dumps({'changes':[{'url':'https://other.com','new_fingerprint':'pending'}]}))
            with patch.object(watch,'STATE',state),patch.object(watch,'PENDING',pending),patch.object(watch,'collect_urls',return_value={'https://example.com':{}}):
                with patch.object(watch,'fetch',return_value=(0,'')):watch.main()
                self.assertEqual(json.loads(state.read_text())['sources']['https://example.com']['fingerprint'],'old')
                self.assertEqual(len(json.loads(pending.read_text())['changes']),1)
                with patch.object(watch,'fetch',return_value=(200,'new')):watch.main()
                self.assertEqual(len(json.loads(pending.read_text())['changes']),2)
                with patch.object(watch,'fetch',return_value=(200,'new')):watch.main()
                self.assertEqual(len(json.loads(pending.read_text())['changes']),2)

if __name__=='__main__':unittest.main()
