#!/usr/bin/env python3
"""Ankara median fuel prices from the publisher's open CSV (EPDK-derived)."""
import csv, io, json, re, urllib.request, unicodedata
from datetime import datetime, timezone
from pathlib import Path

URL = 'https://guncelakaryakitfiyatlari.com/veri/iller.csv'

def norm(x):
    x = unicodedata.normalize('NFKD', str(x).strip().casefold())
    return ''.join(c for c in x if not unicodedata.combining(c)).replace('ı','i')

def number(v):
    v=str(v).strip().replace('₺','').replace('TL','').strip()
    if ',' in v and '.' not in v: v=v.replace(',','.')
    return float(v)

def main():
    req=urllib.request.Request(URL,headers={'User-Agent':'AKRLojistikSite/1.0 (+https://akrlojistik.com)'})
    with urllib.request.urlopen(req,timeout=30) as resp: raw=resp.read().decode('utf-8-sig')
    dialect=csv.Sniffer().sniff(raw[:4096],delimiters=',;\t')
    rows=list(csv.reader(io.StringIO(raw),dialect))
    if not rows:raise ValueError('CSV empty')
    headers=[norm(h) for h in rows[0]]
    def column(keys):
        for i,h in enumerate(headers):
            if h in keys:return i
        for i,h in enumerate(headers):
            if any(k in h for k in keys):return i
        return None
    city=column(['il','sehir','bolge','city','province'])
    fields={'benzin':column(['benzin','gasoline','kursunsuz']), 'motorin':column(['motorin','diesel','mazot']), 'lpg':column(['lpg','otogaz','autogas'])}
    date_col=column(['tarih','date','gecerlilik','yururluk'])
    if city is None or any(v is None for v in fields.values()):
        raise ValueError('CSV column format changed: '+repr(headers))
    candidates=[r for r in rows[1:] if len(r)>max([city,*fields.values()]) and norm(r[city])=='ankara']
    if len(candidates)!=1:raise ValueError('Expected exactly one Ankara row; got '+str(len(candidates)))
    row=candidates[0]
    prices={k:number(row[i]) for k,i in fields.items()}
    if not (10<prices['benzin']<300 and 10<prices['motorin']<300 and 5<prices['lpg']<200):raise ValueError('Out-of-range prices: '+repr(prices))
    now=datetime.now(timezone.utc)
    raw_date=row[date_col].strip() if date_col is not None and date_col<len(row) else ''
    valid_date=''
    if raw_date:
        for pattern in ('%Y-%m-%d','%d.%m.%Y','%d/%m/%Y'):
            try:valid_date=datetime.strptime(raw_date,pattern).date().isoformat();break
            except ValueError:pass
    if not valid_date:valid_date=now.date().isoformat() # collection date, not source-effective date
    output={'city':'Ankara','prices':prices,'valid_date':valid_date,'updated_at':now.isoformat(),'source':URL,'price_type':'EPDK dağıtıcı bildirimleri il ortancası'}
    dest=Path('data/ankara-yakit.json');dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(output)

if __name__=='__main__':main()
