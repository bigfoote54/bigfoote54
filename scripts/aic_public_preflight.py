#!/usr/bin/env python3
"""No-secret, no-model public AIC discovery and auth-denial preflight."""
import json, sys, time, uuid
from xml.etree import ElementTree
from urllib import request, error

BASE = 'https://aaexihcarcpgietsnztv.supabase.co/functions/v1/ai-commons-gateway'
TESTS = [
 ('agent_card','/.well-known/agent-card.json','json'),
 ('catalog','/.well-known/ai-catalog.json','json'),
 ('contract','/.well-known/agent.json','json'),
 ('llms','/llms.txt','text'), ('guide','/join','text'),
 ('workflow','/arrival.yml','text'), ('robots','/robots.txt','text'),
 ('sitemap','/sitemap.xml','xml'), ('health','/healthz','json'),
]
def fetch(method,path,payload=None):
    headers={'User-Agent':'aic-public-preflight/1.0'}
    if payload is not None: headers['Content-Type']='application/json'
    req=request.Request(BASE+path, data=json.dumps(payload).encode() if payload is not None else None, method=method, headers=headers)
    try:
        with request.urlopen(req,timeout=15) as res:
            return res.status,res.headers.get('Content-Type',''),res.read(1048576).decode('utf-8','replace')
    except error.HTTPError as exc:
        return exc.code,exc.headers.get('Content-Type',''),exc.read(4096).decode('utf-8','replace')
def obj(raw):
    try:return json.loads(raw)
    except (ValueError,TypeError):return None
def valid_sitemap(body):
    try:
        return ElementTree.fromstring(body).tag.endswith('urlset')
    except ElementTree.ParseError:
        return False
def main():
    results={}; records={}; failures=[]
    for key,path,kind in TESTS:
        try:
            status,ctype,body=fetch('GET',path)
            parsed=obj(body) if kind=='json' else body
            valid=status==200 and (('application/json' in ctype and isinstance(parsed,dict)) if kind=='json'
                    else ('text/' in ctype and len(body)>40) if kind=='text'
                    else valid_sitemap(body))
            results[key]={'pass':valid,'status':status,'type':ctype.split(';')[0], 'mime_warning': (kind=='xml' and 'xml' not in ctype)}
            records[key]=parsed
            if not valid:failures.append(key)
        except Exception as exc:
            results[key]={'pass':False,'error_type':type(exc).__name__,'detail':str(exc)[:160]}
            failures.append(key)
    card=records.get('agent_card') or {}; catalog=records.get('catalog') or {}; contract=records.get('contract') or {}
    checks={
      'card_a2a':isinstance(card.get('supportedInterfaces'),list) and any(x.get('url')==BASE+'/a2a' for x in card['supportedInterfaces']),
      'card_guide':card.get('documentationUrl')==BASE+'/join',
      'contract_application':contract.get('endpoints',{}).get('application')==BASE+'/v1/applications',
      'contract_open':contract.get('applications')=='open',
      'catalog_links_card':any(x.get('url')==BASE+'/.well-known/agent-card.json' for x in catalog.get('entries',[])),
      'join_has_oidc':'OIDC' in str(records.get('guide','')),
      'join_has_workflow':BASE+'/arrival.yml' in str(records.get('guide','')),
      'llms_has_card':BASE+'/.well-known/agent-card.json' in str(records.get('llms','')),
      'workflow_has_dispatch':'workflow_dispatch' in str(records.get('workflow','')),
    }
    results['cross_links']=checks
    failures.extend(k for k,v in checks.items() if not v)
    req={'jsonrpc':'2.0','id':'public-preflight','method':'message/send','params':{'message':{
      'messageId':str(uuid.uuid4()),'role':'ROLE_USER','parts':[{'text':'How can my agent join AI Commons?'}]}}}
    try:
        status,ctype,body=fetch('POST','/a2a',req)
        reply=obj(body); ok=status==200 and isinstance(reply,dict) and reply.get('jsonrpc')=='2.0' and reply.get('id')=='public-preflight' and isinstance(reply.get('result'),dict)
        results['a2a']={'pass':ok,'status':status,'type':ctype.split(';')[0]}
        if not ok:failures.append('a2a')
    except Exception as exc:
        results['a2a']={'pass':False,'error_type':type(exc).__name__,'detail':str(exc)[:160]}
        failures.append('a2a')
    # No token provided. Access must fail closed, without application creation.
    try:
        status,ctype,body=fetch('POST','/v1/applications',{'action':'getApplication'})
        ok=status in (401,403)
        results['unauthenticated_denial']={'pass':ok,'status':status}
        if not ok:failures.append('unauthenticated_denial')
    except Exception as exc:
        results['unauthenticated_denial']={'pass':False,'error_type':type(exc).__name__,'detail':str(exc)[:160]}
        failures.append('unauthenticated_denial')
    print(json.dumps({'checked_at_unix':round(time.time()),'base':BASE,'results':results,'passed':not failures,'failures':failures},indent=2))
    return 1 if failures else 0
if __name__=='__main__':sys.exit(main())
