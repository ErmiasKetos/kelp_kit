
import streamlit as st
import pandas as pd
from datetime import datetime
import json

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
    .module-card {
        background-color: #E2EFDA;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4472C4;
        margin-bottom: 1rem;
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
    .warning-box {
        background-color: #FCE4D6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #FF0000;
        margin: 1rem 0;
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
if 'order_number' not in st.session_state:
    st.session_state.order_number = f"2025-{datetime.now().strftime('%m%d')}-001"
if 'modules_selected' not in st.session_state:
    st.session_state.modules_selected = {'base': True}
if 'order_history' not in st.session_state:
    st.session_state.order_history = []

# Component database - CORRECTED: pH/Conductivity removed, sample sharing logic added
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
            {'item': '250mL HDPE bottle (general chemistry)', 'qty': 1, 'cost': 2.50, 'pn': 'Bottle_01', 'location': 'Shelf B1'},
        ],
        'color': '#4472C4',
        'tests': ['Alkalinity', 'Total Hardness', 'Calcium Hardness', 'Turbidity', 'TDS'],
        'preservation': 'None (no acid)',
        'can_share': True,
        'shares_with': 'Module C (Anions)'
    },
    'module_b': {
        'name': 'MODULE B: Metals (EPA 200.8)',
        'description': 'Lead, Copper, Arsenic, Chromium, Zinc, Iron, Manganese',
        'cost': 5.00,
        'items': [
            {'item': '250mL HDPE bottle (trace-metal)', 'qty': 1, 'cost': 3.50, 'pn': 'Bottle_02', 'location': 'Shelf B2'},
            {'item': 'HNO₃ preservative vial (2mL)', 'qty': 1, 'cost': 1.50, 'pn': 'Pres_HNO3', 'location': 'Shelf D1'},
        ],
        'color': '#70AD47',
        'tests': ['Lead (Pb)', 'Copper (Cu)', 'Arsenic (As)', 'Chromium (Cr)', 'Zinc (Zn)', 'Iron (Fe)', 'Manganese (Mn)', 'Other trace metals'],
        'preservation': 'HNO₃ to pH <2',
        'can_share': False
    },
    'module_c': {
        'name': 'MODULE C: Anions (EPA 300.1)',
        'description': 'Chloride, Sulfate, Nitrate, Fluoride',
        'cost': 1.50,
        'items': [
            {'item': '250mL PP bottle (anions)', 'qty': 1, 'cost': 1.50, 'pn': 'Bottle_03', 'location': 'Shelf B3'},
        ],
        'color': '#FFC000',
        'tests': ['Chloride (Cl⁻)', 'Sulfate (SO₄²⁻)', 'Nitrate (NO₃⁻)', 'Fluoride (F⁻)'],
        'preservation': 'None (no acid)',
        'can_share': True,
        'shares_with': 'Module A (Gen Chem)'
    },
    'module_d': {
        'name': 'MODULE D: Nutrients',
        'description': 'Ammonia, TKN, Nitrite, Phosphate',
        'cost': 4.00,
        'items': [
            {'item': '500mL PP bottle (nutrients)', 'qty': 1, 'cost': 2.50, 'pn': 'Bottle_04', 'location': 'Shelf B4'},
            {'item': 'H₂SO₄ preservative vial (2mL)', 'qty': 1, 'cost': 1.50, 'pn': 'Pres_H2SO4', 'location': 'Shelf D2'},
        ],
        'color': '#5B9BD5',
        'tests': ['Ammonia (NH₃)', 'Total Kjeldahl Nitrogen (TKN)', 'Nitrite (NO₂⁻)', 'Phosphate (PO₄³⁻)'],
        'preservation': 'H₂SO₄ to pH <2',
        'can_share': False
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
        'special_warning': '⚠️ PFAS KIT - Use ONLY PFAS-free materials! NO standard foam, NO fluorinated materials!',
        'preservation': 'None (PFAS-free containers)',
        'can_share': False
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
        'preservation': 'Sodium thiosulfate',
        'can_share': False
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

LABOR_COST = 7.46  # 7 minutes at $63.94/hour

# Header
st.markdown('<div class="main-header"> KELP Kit Builder</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Configure custom sampling kits with zero redundancy • Smart sample sharing</div>', unsafe_allow_html=True)

# Sidebar - Order Information
with st.sidebar:
    st.header("📋 Order Information")
    order_number = st.text_input("Order Number", value=st.session_state.order_number)
    customer_name = st.text_input("Customer Name", placeholder="ABC Water District")
    project_name = st.text_input("Project Name", placeholder="Monthly Monitoring")
    technician_name = st.text_input("Technician Name", placeholder="J. Smith", help="Required for audit trail and traceability")
    
    st.divider()
    
    st.header("⚙️ Settings")
    markup_factor = st.slider("Markup Factor", min_value=1.0, max_value=2.0, value=1.4, step=0.05, 
                               help="Multiplier applied to cost to determine customer price")
    show_costs = st.checkbox("Show Internal Costs", value=True, help="Display cost breakdown (internal use)")
    
    st.divider()
    
    if st.button("🔄 Reset Configuration", type="secondary"):
        st.session_state.modules_selected = {'base': True}
        st.rerun()

# Main content area - Two columns
col1, col2 = st.columns([2, 1])

with col1:
    st.header("1️⃣ Select Test Modules")
    st.markdown("*Choose the analytical tests your customer needs. The system will automatically optimize bottle usage.*")
    
    # Module selection with expandable details
    modules_to_show = ['module_a', 'module_b', 'module_c', 'module_d', 'module_p', 'module_m']
    
    for module_key in modules_to_show:
        module = COMPONENT_LIBRARY[module_key]
        
        with st.expander(f"**{module['name']}** - ${module['cost']:.2f}", expanded=False):
            col_check, col_info = st.columns([1, 4])
            
            with col_check:
                selected = st.checkbox(
                    "Select",
                    value=st.session_state.modules_selected.get(module_key, False),
                    key=f"check_{module_key}",
                    label_visibility="collapsed"
                )
                st.session_state.modules_selected[module_key] = selected
            
            with col_info:
                st.markdown(f"**Tests Included:** {module['description']}")
                if 'tests' in module:
                    tests_str = ", ".join(module['tests'])
                    st.caption(f"📊 {tests_str}")
                
                if 'preservation' in module:
                    st.caption(f"🧪 **Preservation:** {module['preservation']}")
                
                if module.get('can_share', False):
                    st.success(f"✅ Can share bottle with {module.get('shares_with', 'other modules')}")
                
                if selected and 'special_warning' in module:
                    st.warning(module['special_warning'])
    
    st.divider()
    
    # Shipping selection
    st.header("2️⃣ Select Shipping Option")
    
    col_std, col_comp = st.columns(2)
    
    with col_std:
        if st.button("📦 Standard Shipping - $8.00", key="ship_standard", 
                     type="secondary" if st.session_state.modules_selected.get('compliance_shipping', False) else "primary",
                     use_container_width=True):
            st.session_state.modules_selected['compliance_shipping'] = False
        st.caption("USPS/FedEx Ground (3-5 days)")
        st.caption("✓ Research/non-compliance samples")
    
    with col_comp:
        if st.button("❄️ Compliance Shipping - $50.00", key="ship_compliance",
                     type="primary" if st.session_state.modules_selected.get('compliance_shipping', False) else "secondary",
                     use_container_width=True):
            st.session_state.modules_selected['compliance_shipping'] = True
        st.caption("FedEx 2-Day with cooler & ice")
        st.caption("✓ Regulatory/compliance samples")

with col2:
    st.header("💰 Cost Summary")
    
    # Calculate costs WITH SAMPLE SHARING LOGIC
    material_cost = COMPONENT_LIBRARY['base']['cost']
    selected_modules = []
    
    # Check if A and C are both selected (sample sharing case)
    sharing_a_c = (st.session_state.modules_selected.get('module_a', False) and 
                   st.session_state.modules_selected.get('module_c', False))
    
    # Add selected modules
    for module_key in modules_to_show:
        if st.session_state.modules_selected.get(module_key, False):
            selected_modules.append(module_key)
            
            # Special handling for Module C when sharing with A
            if module_key == 'module_c' and sharing_a_c:
                # Don't add Module C cost if sharing with A
                continue
            else:
                material_cost += COMPONENT_LIBRARY[module_key]['cost']
    
    # Add shipping
    if st.session_state.modules_selected.get('compliance_shipping', False):
        shipping_cost = SHIPPING_OPTIONS['compliance']['cost']
        shipping_type = 'Compliance'
    else:
        shipping_cost = SHIPPING_OPTIONS['standard']['cost']
        shipping_type = 'Standard'
    
    total_cost = material_cost + LABOR_COST + shipping_cost
    customer_price = total_cost * markup_factor
    margin = customer_price - total_cost
    margin_pct = (margin / customer_price) * 100 if customer_price > 0 else 0
    
    # Display summary
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
                <span style="font-weight: bold;">Total Cost to KELP:</span>
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
    
    # Show smart sharing notification
    if sharing_a_c:
        st.markdown("""
        <div class="sharing-info">
            <strong>✅ SMART SHARING ENABLED</strong><br>
            General Chemistry + Anions share 1 bottle<br>
            <em>Savings: $1.50 + 1 bottle</em>
        </div>
        """, unsafe_allow_html=True)
    
    # Visual indicator
    st.divider()
    st.subheader("📦 Kit Contents")
    
    # Calculate bottles with sharing logic
    bottles_count = 0
    if st.session_state.modules_selected.get('module_a', False):
        bottles_count += 1
    if st.session_state.modules_selected.get('module_b', False):
        bottles_count += 1
    if st.session_state.modules_selected.get('module_c', False) and not sharing_a_c:
        bottles_count += 1  # Only add if NOT sharing with A
    if st.session_state.modules_selected.get('module_d', False):
        bottles_count += 1
    if st.session_state.modules_selected.get('module_p', False):
        bottles_count += 2  # PFAS needs 2 bottles
    if st.session_state.modules_selected.get('module_m', False):
        bottles_count += 1
    
    st.metric("Sample Bottles", bottles_count)
    st.metric("Preservative Vials", 
              (1 if st.session_state.modules_selected.get('module_b', False) else 0) + 
              (1 if st.session_state.modules_selected.get('module_d', False) else 0) +
              (1 if st.session_state.modules_selected.get('module_m', False) else 0))
    
    has_ice = st.session_state.modules_selected.get('compliance_shipping', False)
    st.metric("Temperature Control", "Yes ❄️" if has_ice else "No")

# Pick List Section
st.divider()
st.header("📝 PICK LIST - For Lab Technician")

if len(selected_modules) > 0:
    
    # Generate pick list with SMART SHARING
    pick_list_items = []
    special_notes = []
    
    # Always include base
    for item in COMPONENT_LIBRARY['base']['items']:
        # Check if PFAS is selected - skip standard gloves
        if 'Gloves' in item['item'] and st.session_state.modules_selected.get('module_p', False):
            continue  # Skip standard gloves, PFAS module adds PFAS-free gloves
        pick_list_items.append(item)
    
    # Add selected module components with SHARING LOGIC
    for module_key in selected_modules:
        module = COMPONENT_LIBRARY[module_key]
        
        # Special handling for Module C when sharing with Module A
        if module_key == 'module_c' and sharing_a_c:
            # Don't add Module C bottle - it shares with Module A
            special_notes.append("✅ Anions (Cl⁻, SO₄²⁻, NO₃⁻, F⁻) will use SAME 250mL bottle as General Chemistry (no acid preservation required)")
            continue
        
        # Add all items from the module
        for item in module['items']:
            pick_list_items.append(item)
        
        # Add special warnings
        if 'special_warning' in module:
            special_notes.append(module['special_warning'])
    
    # Add shipping items
    shipping_key = 'compliance' if st.session_state.modules_selected.get('compliance_shipping', False) else 'standard'
    for item in SHIPPING_OPTIONS[shipping_key].get('items', []):
        pick_list_items.append(item)
    
    # Display pick list
    col_print, col_download = st.columns([3, 1])
    
    with col_print:
        st.markdown(f"""
        <div class="pick-list">
        <div style="font-weight: bold; font-size: 1.2rem; margin-bottom: 1rem; border-bottom: 2px solid #F4B183; padding-bottom: 0.5rem;">
        📋 PICK LIST
        </div>
        <div style="margin-bottom: 1rem;">
            <strong>ORDER #:</strong> {order_number}<br>
            <strong>CUSTOMER:</strong> {customer_name if customer_name else '[Not specified]'}<br>
            <strong>PROJECT:</strong> {project_name if project_name else '[Not specified]'}<br>
            <strong>TECHNICIAN:</strong> {technician_name if technician_name else '[Not specified]'}<br>
            <strong>DATE:</strong> {datetime.now().strftime('%B %d, %Y - %I:%M %p')}<br>
            <strong>TESTS ORDERED:</strong> {', '.join([COMPONENT_LIBRARY[m]['name'].split(':')[1].strip() for m in selected_modules])}
        </div>
        <div style="background-color: white; padding: 1rem; border-radius: 5px; margin: 1rem 0;">
        <strong>PICK THE FOLLOWING ITEMS:</strong><br>
        """, unsafe_allow_html=True)
    
    for idx, item in enumerate(pick_list_items, start=1):
        item_line = f"☐ {item['item']}"
        if item['qty'] > 1:
            item_line += f" × {item['qty']}"
        item_line += f" [{item['location']}]"
        
        st.markdown(f"<div style='margin: 0.3rem 0; font-family: monospace;'>{item_line}</div>", unsafe_allow_html=True)
    
    if special_notes:
        st.markdown("<br><strong style='color: #C00000;'>⚠️ SPECIAL NOTES:</strong><br>", unsafe_allow_html=True)
        for note in special_notes:
            st.markdown(f"<div style='color: #C00000; margin: 0.5rem 0;'>{note}</div>", unsafe_allow_html=True)
    
    st.markdown(f"""
        </div>
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #ccc;">
            <strong>TOTAL ASSEMBLY TIME:</strong> ~7 minutes<br>
            <strong>SHIP VIA:</strong> {SHIPPING_OPTIONS[shipping_key]['name']}<br>
            <strong>CUSTOMER PRICE:</strong> ${customer_price:.2f}
        </div>
        <div style="margin-top: 1rem; border-top: 2px solid #F4B183; padding-top: 1rem;">
            <strong>TECHNICIAN SIGNATURE:</strong> __________________ <strong>DATE:</strong> __________<br>
            <strong>QC REVIEW:</strong> __________________ <strong>DATE:</strong> __________
        </div>
        </div>
    """, unsafe_allow_html=True)
    
    with col_download:
        # Create downloadable pick list (TEXT FORMAT)
        pick_list_text = f"""
KELP SAMPLING KIT - PICK LIST
{'='*60}

ORDER #: {order_number}
CUSTOMER: {customer_name if customer_name else '[Not specified]'}
PROJECT: {project_name if project_name else '[Not specified]'}
TECHNICIAN: {technician_name if technician_name else '[Not specified]'}
DATE: {datetime.now().strftime('%B %d, %Y - %I:%M %p')}
TESTS ORDERED: {', '.join([COMPONENT_LIBRARY[m]['name'].split(':')[1].strip() for m in selected_modules])}

{'='*60}
PICK THE FOLLOWING ITEMS:
{'='*60}

"""
        for idx, item in enumerate(pick_list_items, start=1):
            item_line = f"[ ] {item['item']}"
            if item['qty'] > 1:
                item_line += f" × {item['qty']}"
            item_line += f"\n    Location: {item['location']}\n"
            pick_list_text += item_line
        
        if special_notes:
            pick_list_text += f"\n{'='*60}\n⚠️ SPECIAL NOTES:\n{'='*60}\n"
            for note in special_notes:
                pick_list_text += f"\n{note}\n"
        
        pick_list_text += f"""
{'='*60}
ASSEMBLY DETAILS:
{'='*60}
Total Assembly Time: ~7 minutes
Ship Via: {SHIPPING_OPTIONS[shipping_key]['name']}
Customer Price: ${customer_price:.2f}

{'='*60}
SIGNATURES:
{'='*60}
Technician: __________________ Date: __________
QC Review: __________________ Date: __________
"""
        
        st.download_button(
            label="📄 Download Pick List",
            data=pick_list_text,
            file_name=f"KELP_PickList_{order_number}.txt",
            mime="text/plain",
            use_container_width=True
        )
        
        # Create CSV for components
        df_components = pd.DataFrame(pick_list_items)
        csv = df_components.to_csv(index=False)
        
        st.download_button(
            label="📊 Download CSV",
            data=csv,
            file_name=f"KELP_Components_{order_number}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    # Save order button
    st.divider()
    col_save, col_clear = st.columns(2)
    
    with col_save:
        if st.button("💾 Save Order to History", type="primary", use_container_width=True):
            order_data = {
                'order_number': order_number,
                'customer': customer_name,
                'project': project_name,
                'technician': technician_name,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'modules': selected_modules,
                'sharing': sharing_a_c,
                'shipping': shipping_key,
                'total_cost': total_cost,
                'customer_price': customer_price,
                'items_count': len(pick_list_items)
            }
            st.session_state.order_history.append(order_data)
            st.success(f"✅ Order {order_number} saved successfully!")
    
    with col_clear:
        if st.button("🗑️ Clear Configuration", use_container_width=True):
            st.session_state.modules_selected = {'base': True}
            st.rerun()

else:
    st.info("👆 Please select at least one test module to generate a pick list.")

# Order History
if len(st.session_state.order_history) > 0:
    st.divider()
    st.header("📚 Order History")
    
    df_history = pd.DataFrame(st.session_state.order_history)
    df_history['modules_str'] = df_history['modules'].apply(lambda x: ', '.join([m.replace('module_', '').upper() for m in x]))
    
    display_df = df_history[['order_number', 'customer', 'technician', 'date', 'modules_str', 'shipping', 'customer_price']].copy()
    display_df.columns = ['Order #', 'Customer', 'Technician', 'Date', 'Modules', 'Shipping', 'Price']
    display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:.2f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    if st.button("🗑️ Clear Order History"):
        st.session_state.order_history = []
        st.rerun()

# Footer
st.divider()
st.caption(f"""
**KETOS Environmental Laboratory (KELP)** | Kit Builder  
ISO/IEC 17025:2017 Compliant | TNI Accredited  
Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
""")
