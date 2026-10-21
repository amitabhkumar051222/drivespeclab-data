#!/usr/bin/env python3
"""Rebuild verified inputs in isolation; publish only a fully validated result.

Manufacturer changes are detected by watch_official_sources.py. This command
consumes reviewed sidecars/enrichment; it does not invent API prices or refresh
source-verification dates just because a build ran.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from validate_catalog import validate

ROOT = Path(__file__).resolve().parents[1]
STEPS = ['apply_v6_overlay.py', 'apply_verified_enrichment.py',
         'generate_database_catalog.py', 'postprocess_catalog.py', 'sync_catalog_manifest.py']
OUTPUTS = ['data/catalog/cars.json','data/catalog/upcoming.json',
           'data/catalog/change-log.json','data/catalog/catalog-manifest-live.json','data/compare/cars.json']

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check',action='store_true',help='Build and validate without writing outputs')
    args=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='dsl-build-') as temp:
        work=Path(temp)
        shutil.copytree(ROOT/'scripts',work/'scripts')
        shutil.copytree(ROOT/'data',work/'data')
        for step in STEPS:
            subprocess.run([sys.executable,str(work/'scripts'/step)],check=True,cwd=work)
        validate(work)
        old=json.loads((ROOT/OUTPUTS[0]).read_text())['cars']
        new=json.loads((work/OUTPUTS[0]).read_text())['cars']
        if len(new)<len(old)*0.8:
            raise ValueError('Catalog lost over 20% of models; review inputs before publication')
        changed=[]
        for rel in OUTPUTS:
            source,target=work/rel,ROOT/rel
            new_obj=json.loads(source.read_text());old_obj=json.loads(target.read_text()) if target.exists() else {}
            # Build timestamps are not evidence of freshly verified vehicle data.
            if {k:v for k,v in new_obj.items() if k!='generated'}=={k:v for k,v in old_obj.items() if k!='generated'}:
                continue
            changed.append(rel)
            if not args.check:
                target.parent.mkdir(parents=True,exist_ok=True)
                tmp=target.with_suffix(target.suffix+'.tmp')
                tmp.write_text(json.dumps(new_obj,ensure_ascii=False,indent=2)+'\n')
                os.replace(tmp,target)
        print(('Would update' if args.check else 'Updated'),len(changed),'outputs:',', '.join(changed))

if __name__=='__main__':main()
