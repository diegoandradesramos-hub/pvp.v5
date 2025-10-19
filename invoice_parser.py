import re, io, pdfplumber, pandas as pd
UNIT_MAP={'ud':'unit','uds':'unit','unidad':'unit','unidades':'unit','u':'unit','unit':'unit','kg':'kg','kgr':'kg','kgs':'kg','g':'g','gr':'g','grs':'g','l':'L','lt':'L','lts':'L','ml':'ml'}

def _to_float(x):
 x=str(x).strip().replace('€','').replace('EUR',''); x=x.replace('.','').replace(',','.') if x.count(',')==1 and x.count('.')>1 else x.replace(',','.')
 try: return float(x)
 except: return None

def _norm_unit(u):
 u=str(u).strip().lower().replace('.',''); return UNIT_MAP.get(u,u)

def _to_base(q,u):
 return (q/1000.0,'kg') if u=='g' else ((q/1000.0,'L') if u=='ml' else (q,u))

def extract_lines(text):
 rows=[]
 for raw in text.splitlines():
  line=raw.strip(); 
  if not line or len(line)<5: continue
  m=re.search(r'(?P<desc>[^0-9]{3,}?)\s+(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>(?:kg|kgr|kgs|g|gr|grs|l|lt|lts|ml|ud|uds|u|unidad|unidades|unit))\b.*?(?P<total>\d+(?:[.,]\d+)?)\s*€?', line, re.I)
  if not m:
   m=re.search(r'(?P<desc>[^0-9]{3,}?)\s+(?P<total>\d+(?:[.,]\d+)?)\s*€?\s+.*?(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>(?:kg|kgr|kgs|g|gr|grs|l|lt|lts|ml|ud|uds|u|unidad|unidades|unit))\b', line, re.I)
  if not m: continue
  desc=re.sub(r'\s+',' ',m.group('desc')).strip(' .:-'); qty=_to_float(m.group('qty')); unit=_norm_unit(m.group('unit')); total=_to_float(m.group('total'))
  if qty is None or total is None: continue
  qty,unit=_to_base(qty,unit); rows.append({'ingredient':desc,'qty':qty,'unit':unit,'total_cost_gross':total})
 df=pd.DataFrame(rows); 
 if df.empty: return []
 df=df.groupby(['ingredient','unit'],as_index=False).agg({'qty':'sum','total_cost_gross':'sum'})
 return df.to_dict(orient='records')

def parse_invoice_bytes(pdf_bytes):
 with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
  text='\n'.join(page.extract_text() or '' for page in pdf.pages)
 rows=extract_lines(text); return pd.DataFrame(rows, columns=['ingredient','qty','unit','total_cost_gross'])
