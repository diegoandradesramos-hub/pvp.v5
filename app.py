APP_VERSION="5.1"
import streamlit as st, pandas as pd, numpy as np, os, yaml, re
from invoice_parser import parse_invoice_bytes
st.set_page_config(page_title="PVP V5",page_icon="💶",layout="wide")
DATA_DIR=os.path.join(os.path.dirname(__file__),'data')
@st.cache_data
def load_csv(n):
 p=os.path.join(DATA_DIR,n); return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()
@st.cache_data
def load_settings():
 import yaml; return yaml.safe_load(open(os.path.join(DATA_DIR,'settings.yaml'),encoding='utf-8'))
SET=load_settings(); currency=SET.get('currency_symbol','€')
ing=load_csv('ingredient_yields.csv'); cm=load_csv('category_margins.csv'); rec=load_csv('recipes.csv'); rlines=load_csv('recipe_lines.csv'); pur=load_csv('purchases.csv')
st.title('PVP La Terraza V5 (Completa)')
with st.sidebar:
 st.header('Márgenes por sección'); cm=st.data_editor(cm, num_rows='dynamic', use_container_width=True, key='cm'); st.session_state['cm']=cm
st.subheader('Ingredientes (mermas)'); ing=st.data_editor(ing, num_rows='dynamic', use_container_width=True); ing.to_csv(os.path.join(DATA_DIR,'ingredient_yields.csv'),index=False)
st.subheader('Carta'); st.dataframe(rec[["category","display_name","iva_rate"]].rename(columns={"category":"Sección","display_name":"Producto","iva_rate":"IVA"}),use_container_width=True)
# helper
if pur.empty:
 st.info('Sube una factura PDF con la versión con estilo (parche).');
else:
 pur['unit_cost_net']=pur['total_cost_gross']/(1.0+pur['iva_rate'].fillna(0.10))/pur['qty'].replace(0,np.nan)
 pur['_k_ing']=pur['ingredient'].str.strip().str.lower().str.replace(r'\s+',' ',regex=True); pur['_k_unit']=pur['unit'].str.strip().str.lower()
 y=ing.copy(); y['_k_ing']=y['ingredient'].str.strip().str.lower().str.replace(r'\s+',' ',regex=True); y['_k_unit']=y['unit'].str.strip().str.lower()
 last=pur.groupby(['_k_ing','_k_unit']).last(numeric_only=True).reset_index()
 r=last.merge(y[['_k_ing','_k_unit','usable_yield']],on=['_k_ing','_k_unit'],how='left')
 r['usable_yield']=r['usable_yield'].fillna(1.0); r['effective_cost']=r['unit_cost_net']/r['usable_yield'].replace(0,np.nan)
 cost_map={(row['ingredient'],row['unit']):row['effective_cost'] for _,row in r.assign(ingredient=lambda d:d['_k_ing'],unit=lambda d:d['_k_unit']).iterrows()}
 cm_map={str(x['category']):float(x['target_margin']) for _,x in cm.iterrows() if pd.notna(x['target_margin'])}
 rows=[]
 for _, rr in rec.iterrows():
  item_lines=rlines[rlines['item_key']==rr['item_key']]; cost=0.0; missing=False
  for _,ln in item_lines.iterrows():
   k=(str(ln['ingredient']).strip().lower(), str(ln['unit']).strip().lower()); c=cost_map.get(k, np.nan)
   if pd.isna(c): missing=True; continue
   cost+=c*float(ln['qty_per_portion'])
  margin=cm_map.get(rr['category'],0.70); iva=float(rr.get('iva_rate',0.10))
  price=None; pvp=None
  if cost>0:
   price=cost/(1.0-margin); pvp=price*(1.0+iva)
  rows.append({'Sección':rr['category'],'Producto':rr['display_name'],'Margen':f"{margin*100:.0f}%",'IVA':f"{iva*100:.0f}%",'Coste ingredientes':cost,'PVP':pvp,'Faltan costes':'Sí' if missing else ''})
 df=pd.DataFrame(rows); 
 for c in ['Coste ingredientes','PVP']:
  df[c]=df[c].map(lambda x: f"{x:.2f}{currency}" if pd.notna(x) else '')
 st.subheader('PVP'); st.dataframe(df.sort_values(['Sección','Producto']), use_container_width=True)
