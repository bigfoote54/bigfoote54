#!/usr/bin/env python3
"""One-time opt-in public listing submission of the AIC discovery concierge.
No secrets, auth tokens, or user records. Checks registry before writing.
"""
import json,sys,time
from urllib import request,error
from urllib.parse import quote
REGISTRY='https://api.a2a-registry.org'
CARD='https://aaexihcarcpgietsnztv.supabase.co/functions/v1/ai-commons-gateway/.well-known/agent-card.json'

def call(method,url,payload=None):
    data=json.dumps(payload).encode() if payload else None
    headers={'User-Agent':'aic-agent-registry-submit/1.0','Accept':'application/json'}
    if data: headers['Content-Type']='application/json'
    req=request.Request(url,data=data,headers=headers,method=method)
    try:
        with request.urlopen(req,timeout=15) as res:
            return res.status,res.read(32000).decode('utf-8','replace')
    except error.HTTPError as exc:
        return exc.code,exc.read(4000).decode('utf-8','replace')
def listed(body):
    try:
        parsed=json.loads(body)
        # Only exact manifest URL is trustworthy enough to deduplicate.
        return CARD in json.dumps(parsed)
    except ValueError:return False
def main():
    result={'target_registry':REGISTRY,'manifest':CARD,'checked_at_unix':round(time.time())}
    search=REGISTRY+'/public/agents?q='+quote('AI Commons')
    try:
        pre,body=call('GET',search)
        result['before']={'status':pre,'exact_card_found':listed(body)}
        if pre!=200:
            result['outcome']='blocked_registry_search'
            print(json.dumps(result,indent=2));return 1
        if listed(body):
            result['outcome']='already_indexed'
            print(json.dumps(result,indent=2));return 0
        code,reply=call('POST',REGISTRY+'/public/ingest',{'manifestUrl':CARD})
        result['ingest']={'status':code,'response_snippet':reply[:350]}
        result['outcome']='submitted_pending_verification' if code in (200,201,202) else 'submission_rejected'
        post,body=call('GET',search)
        result['after']={'status':post,'exact_card_found':listed(body)}
        if result['after']['exact_card_found']:result['outcome']='listed_verified'
        print(json.dumps(result,indent=2))
        return 0 if code in (200,201,202) else 1
    except Exception as exc:
        result['outcome']='transport_failed'
        result['error_type']=type(exc).__name__
        result['error']=str(exc)[:160]
        print(json.dumps(result,indent=2))
        return 1
if __name__=='__main__':sys.exit(main())
