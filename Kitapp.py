
import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# Page configuration
st.set_page_config(
    page_title="KELP Kit Builder",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1F4E78;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4472C4;
        margin-bottom: 2rem;
    }
    .cost-summary {
        background-color: #D9E1F2;
        padding: 1.5rem;
        border-radius: 8px;
        font-size: 1.1rem;
        margin-top: 2rem;
    }
    .pick-list {
        background-color: #FFF2CC;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #F4B183;
        font-family: 'Courier New', monospace;
    }
    .sharing-info {
        background-color: #E2F0D9;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #70AD47;
        margin: 1rem 0;
    }
    .stButton>button {
        background-color: #4472C4;
        color: white;
        font-weight: bold;
        padding: 0.5rem 2rem;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0
if 'order_number' not in st.session_state:
    st.session_state.order_number = f"2025-{datetime.now().strftime('%m%d')}-001"
if 'order_history' not in st.session_state:
    st.session_state.order_history = []

# Generate unique key based on reset counter
def get_key(base_key):
    return f"{base_key}_{st.session_state.reset_counter}"

# PDF Generation Class
class PickListPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        self.set_font('Arial', 'B', 18)
        self.set_text_color(31, 78, 120)
        self.cell(0, 10, 'KETOS ENVIRONMENTAL LABORATORY', 0, 1, 'C')
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SAMPLING KIT - PICK LIST', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'KELP-SOP-KIT-001 | ISO/IEC 17025:2017 | Page {self.page_no()}', 0, 0, 'C')

def generate_pdf_picklist(order_info, pick_list_items, special_notes, cost_info):
    """Generate professional PDF pick list using fpdf2"""
    pdf = PickListPDF()
    
    # Order Information Section
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(217, 225, 242)
    
    # Table header
    pdf.cell(45, 7, 'Order Number:', 1, 0, 'L', True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(90, 7, order_info['order_number'], 1, 0, 'L')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 7, 'Date:', 1, 0, 'L', True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 7, datetime.now().strftime('%B %d, %Y'), 1, 1, 'L')
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(45, 7, 'Customer:', 1, 0, 'L', True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(90, 7, order_info['customer'], 1, 0, 'L')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 7, 'Time:', 1, 0, 'L', True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 7, datetime.now().strftime('%I:%M %p'), 1, 1, 'L')
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(45, 7, 'Project:', 1, 0, 'L', True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(90, 7, order_info['project'], 1, 0, 'L')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 7, 'Technician:', 1, 0, 'L', True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 7, '________________', 1, 1, 'L')
    
    pdf.ln(3)
    
    # Tests Ordered
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, f'Tests Ordered: {order_info["tests"]}', 0, 1, 'L')
    pdf.ln(5)
    
    # Components Section
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(68, 114, 196)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, 'COMPONENTS TO PICK', 0, 1, 'L', True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    
    # Table header
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(68, 114, 196)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(10, 7, '', 1, 0, 'C', True)  # Checkbox
    pdf.cell(90, 7, 'Item Description', 1, 0, 'L', True)
    pdf.cell(15, 7, 'Qty', 1, 0, 'C', True)
    pdf.cell(35, 7, 'P/N', 1, 0, 'L', True)
    pdf.cell(40, 7, 'Location', 1, 1, 'L', True)
    
    # Table rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    
    fill = False
    for item in pick_list_items:
        if fill:
            pdf.set_fill_color(240, 240, 240)
        else:
            pdf.set_fill_color(255, 255, 255)
        
        # Checkbox
        pdf.cell(10, 6, '[ ]', 1, 0, 'C', fill)
        
        # Item description
        item_text = item['item']
        if item['qty'] > 1:
            item_text += f" x {item['qty']}"
        pdf.cell(90, 6, item_text[:50], 1, 0, 'L', fill)
        
        # Quantity
        pdf.cell(15, 6, str(item['qty']), 1, 0, 'C', fill)
        
        # Part number
        pdf.cell(35, 6, item['pn'], 1, 0, 'L', fill)
        
        # Location
        pdf.cell(40, 6, item['location'], 1, 1, 'L', fill)
        
        fill = not fill
    
    pdf.ln(5)
    
    # Special Instructions
    if special_notes:
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(192, 0, 0)
        pdf.cell(0, 8, 'SPECIAL INSTRUCTIONS', 0, 1, 'L')
        pdf.set_font('Arial', '', 9)
        for note in special_notes:
            pdf.multi_cell(0, 5, f'  * {note}')
        pdf.ln(3)
        pdf.set_text_color(0, 0, 0)
    
    # Assembly Information
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(226, 240, 217)
    pdf.cell(0, 8, 'ASSEMBLY INFORMATION', 0, 1, 'L', True)
    pdf.ln(1)
    
    pdf.set_font('Arial', '', 9)
    pdf.cell(50, 6, 'Total Items:', 0, 0, 'L')
    pdf.cell(45, 6, str(len(pick_list_items)), 0, 0, 'L')
    pdf.cell(50, 6, 'Assembly Time:', 0, 0, 'L')
    pdf.cell(0, 6, '~7 minutes', 0, 1, 'L')
    
    pdf.cell(50, 6, 'Shipping Method:', 0, 0, 'L')
    pdf.cell(45, 6, order_info['shipping'][:30], 0, 0, 'L')
    pdf.cell(50, 6, 'Customer Price:', 0, 0, 'L')
    pdf.cell(0, 6, f"${cost_info['customer_price']:.2f}", 0, 1, 'L')
    
    pdf.ln(8)
    
    # Quality Control Signatures
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(255, 242, 204)
    pdf.cell(0, 8, 'QUALITY CONTROL', 0, 1, 'L', True)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 9)
    # First row
    pdf.cell(40, 7, 'Assembled By:', 1, 0, 'L')
    pdf.cell(60, 7, '________________', 1, 0, 'C')
    pdf.cell(20, 7, 'Date:', 1, 0, 'L')
    pdf.cell(35, 7, '__________', 1, 0, 'C')
    pdf.cell(15, 7, 'Time:', 1, 0, 'L')
    pdf.cell(0, 7, '__________', 1, 1, 'C')
    
    # Second row
    pdf.cell(40, 7, 'QC Reviewed By:', 1, 0, 'L')
    pdf.cell(60, 7, '________________', 1, 0, 'C')
    pdf.cell(20, 7, 'Date:', 1, 0, 'L')
    pdf.cell(35, 7, '__________', 1, 0, 'C')
    pdf.cell(15, 7, 'Initials:', 1, 0, 'L')
    pdf.cell(0, 7, '__________', 1, 1, 'C')
    
    pdf.ln(5)
    
    # Footer note
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 4, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | TNI Accredited Laboratory')
    
    # Return PDF as bytes
    return bytes(pdf.output())

# Component database
COMPONENT_LIBRARY = {
    'base': {
        'name': 'BASE COMPONENTS',
        'description': 'Included in every kit',
        'cost': 9.50,
        'items': [
            {'item': 'COC Form', 'qty': 1, 'cost': 0.50, 'pn': 'Form_01', 'location': 'Shelf A1'},
            {'item': 'Waterproof Labels (sheet)', 'qty': 1, 'cost': 0.50, 'pn': 'Label_01', 'location': 'Shelf A2'},
            {'item': 'Nitrile Gloves (pairs)', 'qty': 2, 'cost': 1.00, 'pn': 'PPE_01', 'location': 'Shelf A3'},
            {'item': 'Bubble Wrap/Dividers', 'qty': 1, 'cost': 2.00, 'pn': 'Pack_01', 'location': 'Shelf A4'},
            {'item': 'Shipping Box (Standard)', 'qty': 1, 'cost': 4.00, 'pn': 'Box_01', 'location': 'Shelf A5'},
            {'item': 'Instruction Sheet', 'qty': 1, 'cost': 1.00, 'pn': 'Inst_01', 'location': 'Shelf A6'},
        ],
        'color': '#1F4E78'
    },
    'module_a': {
        'name': 'MODULE A: General Chemistry',
        'description': 'Alkalinity, Hardness, Turbidity, TDS',
        'cost': 2.50,
        'items': [
            {'item': '250mL HDPE bottle (general chemistry)', 'qty': 1, 'cost': 2.50, 'pn': 'Bottle_GenChem', 'location': 'Shelf B1'},
        ],
        'color': '#4472C4',
        'tests': ['Alkalinity', 'Total Hardness', 'Calcium Hardness', 'Turbidity', 'TDS'],
        'preservation': 'NONE',
        'can_share_with': ['module_c'],
        'note': 'No acid preservation - compatible with anions'
    },
    'module_b': {
        'name': 'MODULE B: Metals (EPA 200.8)',
        'description': 'Lead, Copper, Arsenic, Chromium, Zinc, Iron, Manganese',
        'cost': 5.00,
        'items': [
            {'item': '250mL HDPE bottle (trace-metal clean)', 'qty': 1, 'cost': 3.50, 'pn': 'Bottle_02', 'location': 'Shelf B2'},
            {'item': 'HNO3 preservative vial (2mL)', 'qty': 1, 'cost': 1.50, 'pn': 'Pres_HNO3', 'location': 'Shelf D1'},
        ],
        'color': '#70AD47',
        'tests': ['Lead (Pb)', 'Copper (Cu)', 'Arsenic (As)', 'Chromium (Cr)', 'Zinc (Zn)', 'Iron (Fe)', 'Manganese (Mn)', 'Other trace metals'],
        'preservation': 'HNO3 to pH <2',
        'can_share_with': [],
        'note': 'Requires HNO3 preservation - SEPARATE bottle required'
    },
    'module_c': {
        'name': 'MODULE C: Anions (EPA 300.1)',
        'description': 'Chloride, Sulfate, Nitrate, Fluoride',
        'cost': 0.00,
        'items': [],
        'color': '#FFC000',
        'tests': ['Chloride (Cl-)', 'Sulfate (SO4 2-)', 'Nitrate (NO3-)', 'Fluoride (F-)'],
        'preservation': 'NONE',
        'can_share_with': ['module_a'],
        'note': 'No acid preservation - can SHARE bottle with Module A'
    },
    'module_d': {
        'name': 'MODULE D: Nutrients',
        'description': 'Ammonia, TKN, Nitrite, Phosphate',
        'cost': 4.00,
        'items': [
            {'item': '500mL PP bottle (nutrients)', 'qty': 1, 'cost': 2.50, 'pn': 'Bottle_04', 'location': 'Shelf B4'},
            {'item': 'H2SO4 preservative vial (2mL)', 'qty': 1, 'cost': 1.50, 'pn': 'Pres_H2SO4', 'location': 'Shelf D2'},
        ],
        'color': '#5B9BD5',
        'tests': ['Ammonia (NH3)', 'Total Kjeldahl Nitrogen (TKN)', 'Nitrite (NO2-)', 'Phosphate (PO4 3-)'],
        'preservation': 'H2SO4 to pH <2',
        'can_share_with': [],
        'note': 'Requires H2SO4 preservation - SEPARATE bottle required'
    },
    'module_p': {
        'name': 'MODULE P: PFAS (EPA 537.1 / 1633)',
        'description': 'PFAS panels (3, 14, 18, 25, or 40-compound)',
        'cost': 15.50,
        'items': [
            {'item': '250mL PP bottle (PFAS-free cert)', 'qty': 2, 'cost': 10.00, 'pn': 'Bottle_05', 'location': 'Shelf C1'},
            {'item': 'PP caps w/ PE liners', 'qty': 2, 'cost': 3.00, 'pn': 'Cap_PFAS', 'location': 'Shelf C2'},
            {'item': 'PFAS-free labels', 'qty': 2, 'cost': 1.00, 'pn': 'Label_PFAS', 'location': 'Shelf C3'},
            {'item': 'PFAS-free gloves (UPGRADE)', 'qty': 1, 'cost': 1.50, 'pn': 'PPE_PFAS', 'location': 'Shelf E1'},
        ],
        'color': '#E7E6E6',
        'tests': ['PFAS-3', 'PFAS-14', 'PFAS-18', 'PFAS-25', 'PFAS-40'],
        'special_warning': 'PFAS KIT - Use ONLY PFAS-free materials! NO standard foam, NO fluorinated materials!',
        'preservation': 'NONE (but requires PFAS-free containers)',
        'can_share_with': [],
        'note': 'PFAS-free containers required - CANNOT share'
    },
    'module_m': {
        'name': 'MODULE M: Microbiology',
        'description': 'Total Coliform, E. coli',
        'cost': 2.50,
        'items': [
            {'item': '100mL sterile bottle', 'qty': 1, 'cost': 2.00, 'pn': 'Bottle_Sterile', 'location': 'Shelf B5'},
            {'item': 'Sodium thiosulfate tablet', 'qty': 1, 'cost': 0.50, 'pn': 'Pres_Thio', 'location': 'Shelf D3'},
        ],
        'color': '#A5A5A5',
        'tests': ['Total Coliform', 'E. coli', 'Fecal Coliform'],
        'preservation': 'Sodium thiosulfate (for dechlorination)',
        'can_share_with': [],
        'note': 'Sterile bottle required - CANNOT share'
    },
}

SHIPPING_OPTIONS = {
    'standard': {
        'name': 'Standard Shipping (Ground)',
        'cost': 8.00,
        'description': 'USPS/FedEx Ground - 3-5 business days',
        'items': []
    },
    'compliance': {
        'name': 'Compliance Shipping (Cooler + Ice)',
        'cost': 50.00,
        'description': 'For regulatory samples requiring temperature control',
        'items': [
            {'item': 'Cooler bag (12L insulated)', 'qty': 1, 'cost': 15.00, 'pn': 'Cool_12L', 'location': 'Shelf F1'},
            {'item': 'Ice packs (gel)', 'qty': 4, 'cost': 10.00, 'pn': 'Ice_Gel', 'location': 'Shelf F2'},
            {'item': 'FedEx 2-Day Shipping', 'qty': 1, 'cost': 25.00, 'pn': 'Ship_2Day', 'location': 'N/A'},
        ]
    }
}

LABOR_COST = 7.46

# Header
st.markdown('<div class="main-header">🧪 KELP Smart Kit Builder v2.1</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Intelligent sample sharing • Zero redundancy • EPA compliant</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📋 Order Information")
    order_number = st.text_input("Order Number", value=st.session_state.order_number, key=get_key("order_num"))
    customer_name = st.text_input("Customer Name", placeholder="ABC Water District", key=get_key("customer"))
    project_name = st.text_input("Project Name", placeholder="Monthly Monitoring", key=get_key("project"))
    
    st.divider()
    
    st.header("⚙️ Settings")
    markup_factor = st.slider("Markup Factor", min_value=1.0, max_value=2.0, value=1.4, step=0.05, 
                               help="Multiplier applied to cost to determine customer price", key=get_key("markup"))
    show_costs = st.checkbox("Show Internal Costs", value=True, help="Display cost breakdown (internal use)", key=get_key("show_costs"))
    
    st.divider()
    
    if st.button("🔄 Reset Configuration", type="secondary", key=get_key("reset_btn")):
        st.session_state.reset_counter += 1
        st.rerun()

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("1️⃣ Select Test Modules")
    st.markdown("*Choose the analytical tests your customer needs. The system automatically optimizes bottle usage.*")
    
    modules_to_show = ['module_a', 'module_b', 'module_c', 'module_d', 'module_p', 'module_m']
    
    selected_modules = []
    for module_key in modules_to_show:
        module = COMPONENT_LIBRARY[module_key]
        
        with st.expander(f"**{module['name']}** - ${module['cost']:.2f}", expanded=False):
            col_check, col_info = st.columns([1, 4])
            
            with col_check:
                selected = st.checkbox(
                    "Select",
                    value=False,
                    key=get_key(f"check_{module_key}"),
                    label_visibility="collapsed"
                )
                if selected:
                    selected_modules.append(module_key)
            
            with col_info:
                st.markdown(f"**Tests Included:** {module['description']}")
                if 'tests' in module:
                    tests_str = ", ".join(module['tests'])
                    st.caption(f"📊 {tests_str}")
                
                st.caption(f"🧪 **Preservation:** {module.get('preservation', 'N/A')}")
                
                if 'can_share_with' in module and module['can_share_with']:
                    share_names = [COMPONENT_LIBRARY[m]['name'] for m in module['can_share_with']]
                    st.success(f"✅ Can share bottle with: {', '.join(share_names)}")
                
                if selected and 'special_warning' in module:
                    st.warning(module['special_warning'])
    
    st.divider()
    
    st.header("2️⃣ Select Shipping Option")
    
    col_std, col_comp = st.columns(2)
    
    compliance_shipping = st.session_state.get('compliance_shipping', False)
    
    with col_std:
        if st.button("📦 Standard Shipping - $8.00", key=get_key("ship_standard"), 
                     type="primary" if not compliance_shipping else "secondary",
                     use_container_width=True):
            st.session_state.compliance_shipping = False
            compliance_shipping = False
        st.caption("USPS/FedEx Ground (3-5 days)")
    
    with col_comp:
        if st.button("❄️ Compliance Shipping - $50.00", key=get_key("ship_compliance"),
                     type="primary" if compliance_shipping else "secondary",
                     use_container_width=True):
            st.session_state.compliance_shipping = True
            compliance_shipping = True
        st.caption("FedEx 2-Day with cooler & ice")

with col2:
    st.header("💰 Cost Summary")
    
    # Calculate costs with sharing logic
    material_cost = COMPONENT_LIBRARY['base']['cost']
    bottles_count = 0
    preservatives_count = 0
    
    sharing_a_c = ('module_a' in selected_modules and 'module_c' in selected_modules)
    
    for module_key in selected_modules:
        module = COMPONENT_LIBRARY[module_key]
        
        if module_key == 'module_c' and sharing_a_c:
            continue
        elif module_key == 'module_c' and not sharing_a_c:
            material_cost += 1.50
            bottles_count += 1
        else:
            material_cost += module['cost']
            
            if module_key == 'module_a':
                bottles_count += 1
            elif module_key == 'module_b':
                bottles_count += 1
                preservatives_count += 1
            elif module_key == 'module_d':
                bottles_count += 1
                preservatives_count += 1
            elif module_key == 'module_p':
                bottles_count += 2
            elif module_key == 'module_m':
                bottles_count += 1
                preservatives_count += 1
    
    if compliance_shipping:
        shipping_cost = SHIPPING_OPTIONS['compliance']['cost']
        shipping_type = 'Compliance'
    else:
        shipping_cost = SHIPPING_OPTIONS['standard']['cost']
        shipping_type = 'Standard'
    
    total_cost = material_cost + LABOR_COST + shipping_cost
    customer_price = total_cost * markup_factor
    margin = customer_price - total_cost
    margin_pct = (margin / customer_price) * 100 if customer_price > 0 else 0
    
    st.markdown(f"""
    <div class="cost-summary">
        <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">Modules Selected: {len(selected_modules)}</div>
        <div style="font-size: 1.3rem; font-weight: bold; color: #1F4E78; margin-bottom: 1rem;">
            CUSTOMER PRICE: ${customer_price:.2f}
        </div>
    """, unsafe_allow_html=True)
    
    if show_costs:
        st.markdown(f"""
        <div style="font-size: 0.85rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #ccc;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                <span>Material Cost:</span>
                <span style="font-weight: bold;">${material_cost:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                <span>Labor (7 min):</span>
                <span style="font-weight: bold;">${LABOR_COST:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                <span>Shipping ({shipping_type}):</span>
                <span style="font-weight: bold;">${shipping_cost:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding-top: 0.5rem; border-top: 1px solid #ccc;">
                <span style="font-weight: bold;">Total Cost:</span>
                <span style="font-weight: bold; color: #1F4E78;">${total_cost:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 0.5rem; color: #70AD47;">
                <span>Profit Margin:</span>
                <span style="font-weight: bold;">${margin:.2f} ({margin_pct:.1f}%)</span>
            </div>
        </div>
        </div>
    """, unsafe_allow_html=True)
    else:
        st.markdown("</div>", unsafe_allow_html=True)
    
    if sharing_a_c:
        st.markdown("""
        <div class="sharing-info">
            <strong>✅ SMART SHARING:</strong><br>
            General Chemistry + Anions share 1 bottle<br>
            <em>Savings: $1.50 + 1 bottle</em>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📦 Kit Contents")
    st.metric("Sample Bottles", bottles_count)
    st.metric("Preservatives", preservatives_count)
    st.metric("Temp Control", "Yes ❄️" if compliance_shipping else "No")

# Pick List
st.divider()
st.header("📝 PICK LIST")

if len(selected_modules) > 0:
    pick_list_items = []
    special_notes = []
    
    for item in COMPONENT_LIBRARY['base']['items']:
        if 'Gloves' in item['item'] and 'module_p' in selected_modules:
            continue
        pick_list_items.append(item)
    
    for module_key in selected_modules:
        module = COMPONENT_LIBRARY[module_key]
        
        if module_key == 'module_c':
            if sharing_a_c:
                special_notes.append("Anions (NO3, Cl, SO4, F) share bottle with General Chemistry")
                continue
            else:
                pick_list_items.append({
                    'item': '250mL PP bottle (anions)', 
                    'qty': 1, 
                    'cost': 1.50, 
                    'pn': 'Bottle_03', 
                    'location': 'Shelf B3'
                })
        else:
            for item in module['items']:
                pick_list_items.append(item)
        
        if 'special_warning' in module:
            special_notes.append(module['special_warning'])
    
    shipping_key = 'compliance' if compliance_shipping else 'standard'
    for item in SHIPPING_OPTIONS[shipping_key].get('items', []):
        pick_list_items.append(item)
    
    # Display preview
    st.markdown(f"""
    <div class="pick-list">
    <strong>ORDER:</strong> {order_number} | <strong>CUSTOMER:</strong> {customer_name if customer_name else 'N/A'}<br>
    <strong>TESTS:</strong> {', '.join([COMPONENT_LIBRARY[m]['name'].split(':')[1].strip() for m in selected_modules])}<br><br>
    <strong>COMPONENTS:</strong><br>
    """, unsafe_allow_html=True)
    
    for item in pick_list_items:
        st.markdown(f"☐ {item['item']} × {item['qty']} [{item['location']}]<br>", unsafe_allow_html=True)
    
    if special_notes:
        st.markdown("<br><strong style='color: red;'>⚠️ SPECIAL NOTES:</strong><br>", unsafe_allow_html=True)
        for note in special_notes:
            st.markdown(f"• {note}<br>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Download buttons
    col_pdf, col_csv = st.columns(2)
    
    with col_pdf:
        order_info = {
            'order_number': order_number,
            'customer': customer_name if customer_name else '[Not specified]',
            'project': project_name if project_name else '[Not specified]',
            'tests': ', '.join([COMPONENT_LIBRARY[m]['name'].split(':')[1].strip() for m in selected_modules]),
            'shipping': SHIPPING_OPTIONS[shipping_key]['name']
        }
        
        cost_info = {
            'material_cost': material_cost,
            'labor_cost': LABOR_COST,
            'shipping_cost': shipping_cost,
            'total_cost': total_cost,
            'customer_price': customer_price
        }
        
        pdf_bytes = generate_pdf_picklist(order_info, pick_list_items, special_notes, cost_info)
        
        st.download_button(
            label="📄 Download PDF Pick List",
            data=pdf_bytes,
            file_name=f"KELP_PickList_{order_number}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    
    with col_csv:
        df_components = pd.DataFrame(pick_list_items)
        csv = df_components.to_csv(index=False)
        
        st.download_button(
            label="📊 Download CSV",
            data=csv,
            file_name=f"KELP_Components_{order_number}.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    st.info("👆 Please select at least one test module.")

# Footer
st.divider()
st.caption(f"""
**KETOS Environmental Laboratory (KELP)** | Smart Kit Builder v2.1  
ISO/IEC 17025:2017 | TNI Accredited | Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
""")
