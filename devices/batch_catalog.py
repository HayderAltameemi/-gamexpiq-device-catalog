#!/usr/bin/env python3
"""Safe, offline batch builder for GamExpIQ static GitHub Pages JSON catalog.

Review-gated: this utility does NOT research specs, claim licensing permissions,
change the Flutter database, connect to GitHub, or publish automatically.
"""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit

CORE = {'soc','gpu','ram_gb','display_width_px','display_height_px','screen_inches',
        'display_ppi','max_refresh_hz','battery_mah','touch_sampling_hz','model_code'}
EXTRA = {'gyro_sensor_present','ram_options_gb'}
ALLOWED = CORE | EXTRA
LICENSES = {'OEM-PUBLIC-REFERENCE','CC0-1.0','COMMERCIAL-LICENSED'}
NUMERIC = {'ram_gb':(1,128),'screen_inches':(3,20),'display_width_px':(320,10000),
           'display_height_px':(320,10000),'display_ppi':(50,1500),
           'max_refresh_hz':(30,360),'battery_mah':(500,30000),
           'touch_sampling_hz':(30,5000)}
INTS = {'display_width_px','display_height_px','display_ppi','max_refresh_hz','battery_mah','touch_sampling_hz'}
COLUMNS = ['device_id','field_name','value','source_url','license','reviewed','model_code','review_note']
SKU = {'soc','gpu','ram_gb'}

def canonical(key, value):
    value = str(value).strip()
    if key in NUMERIC:
        try: n = float(value)
        except ValueError: raise ValueError('not numeric')
        lo,hi = NUMERIC[key]
        if not lo <= n <= hi: raise ValueError('numeric value outside permitted range')
        if key in INTS and not n.is_integer(): raise ValueError('expected integer')
        return str(int(n)) if n.is_integer() else str(n)
    if key == 'gyro_sensor_present':
        if value.lower() not in {'true','false'}: raise ValueError('gyro must be true or false')
        return value.lower()
    if key == 'ram_options_gb':
        try: vals=[int(x.strip()) for x in value.split(',')]
        except ValueError: raise ValueError('RAM choices must be comma-separated integers')
        if not vals or len(vals)>8 or any(n<1 or n>128 for n in vals) or len(set(vals)) != len(vals):
            raise ValueError('invalid/duplicate RAM choices')
        return ','.join(map(str,sorted(vals)))
    if not 2 <= len(value) <= 100 or not re.fullmatch(r'[A-Za-z0-9 +._/()\-]{2,100}',value):
        raise ValueError('invalid text or model code')
    return value

def valid_url(url):
    u=urlsplit(url)
    return (u.scheme=='https' and bool(u.hostname) and not u.username and not u.password
            and not u.fragment and len(url)<=2048)

def load_seed(path):
    uri=path.resolve().as_uri()+'?mode=ro'
    with sqlite3.connect(uri,uri=True) as con:
        con.row_factory=sqlite3.Row
        rows=con.execute('SELECT * FROM devices').fetchall()
    return {r['id']:dict(r) for r in rows}

def load_existing(path, seed):
    output={}
    if not path.exists(): return output
    folder=path/'devices'
    for file in sorted(folder.glob('*.json')):
        data=json.loads(file.read_text(encoding='utf-8'))
        did=data.get('device_id')
        if did != file.stem or did not in seed or data.get('schema_version') != 1:
            raise ValueError(f'Invalid existing catalog identity: {file.name}')
        s=seed[did]
        if data.get('brand')!=s['brand'] or data.get('model')!=s['model']:
            raise ValueError(f'Existing brand/model mismatch: {file.name}')
        if not isinstance(data.get('fields'),dict): raise ValueError(f'Existing fields invalid: {file.name}')
        for field, details in data['fields'].items():
            if field not in ALLOWED or not isinstance(details,dict):
                raise ValueError(f'Unsupported existing field {did}.{field}')
            if details.get('license') not in LICENSES or not valid_url(details.get('source_url','')):
                raise ValueError(f'Invalid existing provenance: {did}.{field}')
            canonical(field,details.get('value',''))
        output[did]=data
    return output

def run(args):
    seed=load_seed(Path(args.seed))
    records=load_existing(Path(args.base),seed)
    rejects=[]; additions=[]; unchanged=[]; seen=set()
    with open(args.csv,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=COLUMNS:
            raise ValueError('CSV columns must be exactly: '+','.join(COLUMNS))
        for line,row in enumerate(reader,2):
            did=row['device_id'].strip(); field=row['field_name'].strip()
            label=f'line {line}: {did}.{field}'
            try:
                if did not in seed: raise ValueError('device ID not in seed SQLite')
                if field not in ALLOWED: raise ValueError('unsupported field')
                if row['reviewed'].strip().lower()!='yes': raise ValueError('not manually reviewed')
                if row['license'].strip() not in LICENSES: raise ValueError('license not approved for this workflow')
                if not valid_url(row['source_url'].strip()): raise ValueError('invalid HTTPS source URL')
                if not row['review_note'].strip(): raise ValueError('review_note required')
                value=canonical(field,row['value'])
                code=row['model_code'].strip()
                if code and not re.fullmatch(r'[A-Za-z0-9._\-]{3,80}',code):
                    raise ValueError('invalid variant code')
                s=seed[did]
                if field in SKU:
                    # Existing app accepts online SKU-sensitive fields only when
                    # a concrete SKU matches; no guessing across regional variants.
                    if not code or not s['model_code'] or code.casefold()!=s['model_code'].casefold():
                        raise ValueError('SKU-sensitive field lacks matching model_code; cannot safely publish')
                elif code:
                    raise ValueError('model-wide field should not specify a SKU')
                seed_value=s.get(field)
                if seed_value is not None and field in CORE and canonical(field,seed_value).casefold()!=value.casefold():
                    raise ValueError('conflicts with immutable seed value')
                key=(did,field)
                if key in seen: raise ValueError('duplicate field in batch')
                seen.add(key)
                if did not in records:
                    records[did]={'schema_version':1,'device_id':did,'brand':s['brand'],
                                  'model':s['model'],'fields':{}}
                details={'value':value,'source_url':row['source_url'].strip(),'license':row['license'].strip()}
                if field in EXTRA: details['scope']='model_wide'
                old=records[did]['fields'].get(field)
                if old is not None:
                    if canonical(field,old['value']).casefold()!=value.casefold():
                        raise ValueError('conflicts with existing published catalog; manual resolution needed')
                    unchanged.append(label)
                    continue
                records[did]['fields'][field]=details
                additions.append({'device_id':did,'field':field,'value':value,'note':row['review_note'].strip(),
                                  'app_consumes_field':field in CORE})
            except (ValueError,TypeError,KeyError) as exc: rejects.append(f'{label}: {exc}')
    stats={'status':'REJECTED' if rejects else 'PASS_REVIEW_GATE',
           'existing_devices':len(load_existing(Path(args.base),seed)),
           'output_devices':len(records),'new_fields':len(additions),
           'unchanged_rows':len(unchanged),'rejected_rows':len(rejects),
           'fields_total':sum(len(x['fields']) for x in records.values()),
           'limitations':['Source contents and redistribution rights require human verification',
                          'GPU/SOC/RAM fields require exact seed SKU matches',
                          'gyro_sensor_present and ram_options_gb are supplemental, not 8-core fields',
                          'This does not verify PUBG FPS or upload files to GitHub']}
    print(json.dumps(stats,ensure_ascii=False,indent=2))
    for problem in rejects: print('REJECT:',problem,file=sys.stderr)
    if rejects: return 2
    if not args.publish_ready:
        print('DRY RUN ONLY. Add --publish-ready to create a local staging folder. No network uploads.')
        return 0
    out=Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output directory must be new or empty; refuses overwrites')
    (out/'devices').mkdir(parents=True,exist_ok=True)
    for did,data in sorted(records.items()):
        (out/'devices'/f'{did}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    index={'schema_version':1,'device_count':len(records),
           'field_count':sum(len(x['fields']) for x in records.values()),
           'notice':'Reviewed candidate fields with provenance. Does not establish PUBG FPS support.'}
    (out/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    hashes={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(out.rglob('*.json'))}
    report={'summary':stats,'additions':additions,'unchanged':unchanged,
            'sha256':hashes,'review_required_before_upload':True}
    (out.parent/(out.name+'_AUDIT_REPORT.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('STAGED (not uploaded):',out)
    return 0

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed',required=True,help='Original Flutter assets/db/pubg_devices.sqlite')
    p.add_argument('--base',required=True,help='Current published catalog root with devices/ JSON')
    p.add_argument('--csv',required=True,help='New manually reviewed field rows')
    p.add_argument('--out',default='catalog_staged')
    p.add_argument('--publish-ready',action='store_true',help='Generate staging files for separate human publication (does NOT upload)')
    try: return run(p.parse_args())
    except (OSError,ValueError,sqlite3.Error,json.JSONDecodeError) as e:
        print('FAILED:',e,file=sys.stderr);return 2

if __name__=='__main__': sys.exit(main())
