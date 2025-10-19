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
# --- MÁRGENES POR SECCIÓN (sidebar) ---
with st.sidebar:
    st.header('Márgenes por sección')
    # Editor con otra clave para evitar conflictos
    cm = st.data_editor(
        cm,              # tu DataFrame de márgenes cargado
        num_rows='dynamic',
        use_container_width=True,
        key='cm_editor'
    )
    # Guardado inmediato en el CSV (sin session_state)
    cm.to_csv(
        os.path.join(DATA_DIR, 'category_margins.csv'),
        index=False, encoding='utf-8'
    )
    st.caption('✅ Márgenes guardados (auto).')

# --- INGREDIENTES (mermas) ---
# --- BOTÓN DE ACCESO RÁPIDO ---
st.markdown("""
<div style='position:fixed; bottom:20px; right:20px;'>
  <a href='#compras' style='text-decoration:none;'>
    <button style='background:#ff6b35;color:white;border:none;border-radius:50px;padding:12px 20px;font-weight:bold;box-shadow:0 3px 6px rgba(0,0,0,.2);'>
      📤 Subir factura
    </button>
  </a>
</div>
""", unsafe_allow_html=True)
st.markdown("<a id='compras'></a>", unsafe_allow_html=True)
# --- BOTÓN DORADO FLOTANTE "SUBIR FACTURA" ---
st.markdown("""
<style>
#subirfactura {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: linear-gradient(135deg, #d4af37, #f8e58c);
  color: #1b1b1b;
  border: none;
  border-radius: 40px;
  padding: 12px 22px;
  font-weight: 600;
  font-size: 15px;
  box-shadow: 0 4px 14px rgba(0,0,0,.3);
  cursor: pointer;
  transition: all .3s ease;
  z-index: 9999;
}
#subirfactura:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 18px rgba(212,175,55,.5);
  background: linear-gradient(135deg, #f9e79f, #d4af37);
}
</style>

<a href="#compras">
  <button id="subirfactura">📤 Subir factura</button>
</a>
""", unsafe_allow_html=True)

st.subheader("1) Compras (facturas)")
# ---- RECUADRO PRINCIPAL PARA SUBIR FACTURAS ----
st.markdown("""
<div style="border:1px dashed #2e3447; border-radius:12px; padding:14px; margin-bottom:12px;">
  📦 <b>Sube aquí tus facturas o tickets de compra</b><br>
  - Acepta: PDF, JPG o PNG.<br>
  - En iPhone: usa “Compartir → Imprimir → pellizca → Guardar en Archivos (PDF)”.<br>
  - También puedes tomar una foto directamente desde el móvil.
</div>
""", unsafe_allow_html=True)

# Cuadro de subida grande y visible
up = st.file_uploader(
    "📤 Sube facturas (PDF/JPG/PNG)",
    type=["pdf", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
    label_visibility="visible",
    key="facturas_uploader"
)

# Opción cámara (solo en móviles)
cam = st.camera_input("📸 O toma una foto de la factura", key="camara_factura")
if cam is not None:
    # Añadir la foto como un archivo más
    up = list(up) if up else []
    up.append(cam)

# Si hay archivos, los mostramos en lista
if up:
    st.markdown("### 🧾 Facturas subidas")
    for f in up:
        st.write(f"**{f.name}** listo para procesar.")
else:
    st.info("👉 Pulsa el cuadro azul para seleccionar o tomar una factura.")

ing = st.data_editor(
    ing,                 # tu DataFrame de ingredientes/mermas
    num_rows='dynamic',
    use_container_width=True,
    key='ing_editor'
)
ing.to_csv(
    os.path.join(DATA_DIR, 'ingredient_yields.csv'),
    index=False, encoding='utf-8'
)
st.caption('✅ Mermas guardadas.')

# --- CARTA ---
st.subheader('Carta')
st.dataframe(
    rec[["category","display_name","iva_rate"]]
      .rename(columns={"category":"Sección","display_name":"Producto","iva_rate":"IVA"}),
    use_container_width=True
)

# --- AVISO SI NO HAY COMPRAS ---
if pur.empty:
    st.info('Sube una factura PDF para calcular PVP (mejor PDF con texto).')

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
