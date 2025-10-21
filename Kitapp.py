
import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io

# Page configuration
st.set_page_config(
    page_title="KELP Smart Kit Builder v2.0",
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

# Initialize session state with unique key
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0
if 'order_number' not in st.session_state:
    st.session_state.order_number = f"2025-{datetime.now().strftime('%m%d')}-001"
if 'order_history' not in st.session_state:
    st.session_state.order_history = []

# Generate unique key based on reset counter
def get_key(base_key):
    return f"{base_key}_{st.session_state.reset_counter}"

# Component database - CORRECTED VERSION
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
        'can_share_with': ['module_c'],  # Can share bottle with anions
        'note': 'No acid preservation - compatible with anions'
    },
    'module_b': {
        'name': 'MODULE B: Metals (EPA 200.8)',
        'description': 'Lead, Copper, Arsenic, Chromium, Zinc, Iron, Manganese',
        'cost': 5.00,
        'items': [
            {'item': '250mL HDPE bottle (trace-metal clean)', 'qty': 1, 'cost': 3.50, 'pn': 'Bottle_02', 'location': 'Shelf B2'},
            {'item': 'HNO₃ preservative vial (2mL)', 'qty': 1, 'cost': 1.50, 'pn': 'Pres_HNO3', 'location': 'Shelf D1'},
        ],
        'color': '#70AD47',
        'tests': ['Lead (Pb)', 'Copper (Cu)', 'Arsenic (As)', 'Chromium (Cr)', 'Zinc (Zn)', 'Iron (Fe)', 'Manganese (Mn)', 'Other trace metals'],
        'preservation': 'HNO₃ to pH <2',
        'can_share_with': [],  # CANNOT share - requires acid
        'note': 'Requires HNO₃ preservation - SEPARATE bottle required'
    },
    'module_c': {
        'name': 'MODULE C: Anions (EPA 300.1)',
        'description': 'Chloride, Sulfate, Nitrate, Fluoride',
        'cost': 0.00,  # COST = 0 if sharing with Module A
        'items': [
            # Items added conditionally based on sharing
        ],
        'color': '#FFC000',
        'tests': ['Chloride (Cl⁻)', 'Sulfate (SO₄²⁻)', 'Nitrate (NO₃⁻)', 'Fluoride (F⁻)'],
        'preservation': 'NONE',
        'can_share_with': ['module_a'],  # Can share bottle with gen chem
        'note': 'No acid preservation - can SHARE bottle with Module A'
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
        'can_share_with': [],  # CANNOT share - requires acid
        'note': 'Requires H₂SO₄ preservation - SEPARATE bottle required'
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

LABOR_COST = 7.46  # 7 minutes at $63.94/hour

def generate_pdf_picklist(order_info, pick_list_items, special_notes, cost_info):
    """Generate professional PDF pick list"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1F4E78'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1F4E78'),
        spaceAfter=10,
        spaceBefore=10
    )
    
    # Title
    story.append(Paragraph("KETOS ENVIRONMENTAL LABORATORY", title_style))
    story.append(Paragraph("SAMPLING KIT - PICK LIST", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Order information table
    order_data = [
        ['Order Number:', order_info['order_number'], 'Date:', datetime.now().strftime('%B %d, %Y')],
        ['Customer:', order_info['customer'], 'Time:', datetime.now().strftime('%I:%M %p')],
        ['Project:', order_info['project'], 'Technician:', '________________'],
    ]
    
    order_table = Table(order_data, colWidths=[1.2*inch, 2.5*inch, 0.8*inch, 1.5*inch])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#D9E1F2')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#D9E1F2')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(order_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Tests ordered
    story.append(Paragraph(f"<b>Tests Ordered:</b> {order_info['tests']}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Pick list header
    story.append(Paragraph("COMPONENTS TO PICK", header_style))
    
    # Pick list table
    pick_data = [['☐', 'Item Description', 'Qty', 'P/N', 'Location']]
    for item in pick_list_items:
        pick_data.append([
            '☐',
            item['item'],
            str(item['qty']),
            item['pn'],
            item['location']
        ])
    
    pick_table = Table(pick_data, colWidths=[0.3*inch, 3.2*inch, 0.5*inch, 1.0*inch, 1.0*inch])
    pick_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F0F0')]),
    ]))
    story.append(pick_table)
    story.append(Spacer(1, 0.15*inch))
    
    # Special notes
    if special_notes:
        story.append(Paragraph("⚠️ SPECIAL INSTRUCTIONS", header_style))
        for note in special_notes:
            warning_style = ParagraphStyle(
                'Warning',
                parent=styles['Normal'],
                textColor=colors.HexColor('#C00000'),
                fontSize=10,
                leftIndent=10
            )
            story.append(Paragraph(f"• {note}", warning_style))
        story.append(Spacer(1, 0.15*inch))
    
    # Assembly information
    story.append(Paragraph("ASSEMBLY INFORMATION", header_style))
    assembly_data = [
        ['Total Items:', str(len(pick_list_items)), 'Assembly Time:', '~7 minutes'],
        ['Shipping Method:', order_info['shipping'], 'Customer Price:', f"${cost_info['customer_price']:.2f}"],
    ]
    
    assembly_table = Table(assembly_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    assembly_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E2F0D9')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#E2F0D9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(assembly_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Signature section
    story.append(Paragraph("QUALITY CONTROL", header_style))
    sig_data = [
        ['Assembled By:', '________________', 'Date:', '__________', 'Time:', '__________'],
        ['QC Reviewed By:', '________________', 'Date:', '__________', 'Initials:', '__________'],
    ]
    
    sig_table = Table(sig_data, colWidths=[1.2*inch, 1.5*inch, 0.6*inch, 1.0*inch, 0.7*inch, 1.0*inch])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FFF2CC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Footer
    footer_text = f"<font size=8>KELP-SOP-KIT-001 | ISO/IEC 17025:2017 | TNI Accredited | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</font>"
    story.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

# Header
st.markdown('<div class="main-header">🧪 KELP Smart Kit Builder v2.0</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Intelligent sample sharing • Zero redundancy • EPA compliant</div>', unsafe_allow_html=True)

# Sidebar - Order Information
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
    
    # FIXED RESET BUTTON
    if st.button("🔄 Reset Configuration", type="secondary", key=get_key("reset_btn")):
        st.session_state.reset_counter += 1
        st.rerun()

# Main content area - Two columns
col1, col2 = st.columns([2, 1])

with col1:
    st.header("1️⃣ Select Test Modules")
    st.markdown("*Choose the analytical tests your customer needs. The system automatically optimizes bottle usage.*")
    
    # Module selection with expandable details
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
    
    # Shipping selection
    st.header("2️⃣ Select Shipping Option")
    
    col_std, col_comp = st.columns(2)
    
    compliance_shipping = False
    with col_std:
        if st.button("📦 Standard Shipping - $8.00", key=get_key("ship_standard"), 
                     type="primary" if not compliance_shipping else "secondary",
                     use_container_width=True):
            compliance_shipping = False
        st.caption("USPS/FedEx Ground (3-5 days)")
        st.caption("✓ Research/non-compliance samples")
    
    with col_comp:
        if st.button("❄️ Compliance Shipping - $50.00", key=get_key("ship_compliance"),
                     type="secondary",
                     use_container_width=True):
            compliance_shipping = True
        st.caption("FedEx 2-Day with cooler & ice")
        st.caption("✓ Regulatory/compliance samples")

with col2:
    st.header("💰 Cost Summary")
    
    # Calculate costs with SAMPLE SHARING LOGIC
    material_cost = COMPONENT_LIBRARY['base']['cost']
    bottles_count = 0
    preservatives_count = 0
    
    # Check for sample sharing
    sharing_a_c = ('module_a' in selected_modules and 'module_c' in selected_modules)
    
    # Add costs for selected modules
    for module_key in selected_modules:
        module = COMPONENT_LIBRARY[module_key]
        
        # Special handling for Module C (anions)
        if module_key == 'module_c' and sharing_a_c:
            # Module C shares bottle with Module A - NO additional cost or bottle
            st.info("📦 Anions sharing bottle with General Chemistry")
            continue
        elif module_key == 'module_c' and not sharing_a_c:
            # Module C needs its own bottle
            material_cost += 1.50
            bottles_count += 1
        else:
            material_cost += module['cost']
            
            # Count bottles
            if module_key == 'module_a':
                bottles_count += 1
            elif module_key == 'module_b':
                bottles_count += 1
                preservatives_count += 1
            elif module_key == 'module_d':
                bottles_count += 1
                preservatives_count += 1
            elif module_key == 'module_p':
                bottles_count += 2  # PFAS needs 2 bottles
            elif module_key == 'module_m':
                bottles_count += 1
                preservatives_count += 1
    
    # Add shipping
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
    
    # Sample sharing notification
    if sharing_a_c:
        st.markdown("""
        <div class="sharing-info">
            <strong>✅ SMART SHARING:</strong><br>
            General Chemistry + Anions tests will share a single 250mL bottle<br>
            <em>Savings: 1 bottle, $1.50</em>
        </div>
        """, unsafe_allow_html=True)
    
    # Visual indicator
    st.divider()
    st.subheader("📦 Kit Contents")
    
    st.metric("Sample Bottles", bottles_count)
    st.metric("Preservative Vials", preservatives_count)
    
    has_ice = compliance_shipping
    st.metric("Temperature Control", "Yes ❄️" if has_ice else "No")

# Pick List Section
st.divider()
st.header("📝 PICK LIST - For Lab Technician")

if len(selected_modules) > 0:
    
    # Generate pick list with sample sharing logic
    pick_list_items = []
    special_notes = []
    
    # Always include base
    for item in COMPONENT_LIBRARY['base']['items']:
        # Check if PFAS is selected - skip standard gloves
        if 'Gloves' in item['item'] and 'module_p' in selected_modules:
            continue  # Skip standard gloves, PFAS module adds PFAS-free gloves
        pick_list_items.append(item)
    
    # Add module components with SHARING LOGIC
    for module_key in selected_modules:
        module = COMPONENT_LIBRARY[module_key]
        
        # Special handling for Module C
        if module_key == 'module_c':
            if sharing_a_c:
                # Module C shares with Module A - add note but no bottle
                special_notes.append("✅ Anions (NO₃, Cl, SO₄, F) will use SAME bottle as General Chemistry (no acid preservation)")
                continue
            else:
                # Module C needs own bottle
                pick_list_items.append({
                    'item': '250mL PP bottle (anions)', 
                    'qty': 1, 
                    'cost': 1.50, 
                    'pn': 'Bottle_03', 
                    'location': 'Shelf B3'
                })
        else:
            # Add all items from other modules
            for item in module['items']:
                pick_list_items.append(item)
        
        # Add special warnings
        if 'special_warning' in module:
            special_notes.append(module['special_warning'])
    
    # Add shipping items
    shipping_key = 'compliance' if compliance_shipping else 'standard'
    for item in SHIPPING_OPTIONS[shipping_key].get('items', []):
        pick_list_items.append(item)
    
    # Display web preview
    st.markdown(f"""
    <div class="pick-list">
    <div style="font-weight: bold; font-size: 1.2rem; margin-bottom: 1rem; border-bottom: 2px solid #F4B183; padding-bottom: 0.5rem;">
    📋 PICK LIST PREVIEW
    </div>
    <div style="margin-bottom: 1rem;">
        <strong>ORDER #:</strong> {order_number}<br>
        <strong>CUSTOMER:</strong> {customer_name if customer_name else '[Not specified]'}<br>
        <strong>PROJECT:</strong> {project_name if project_name else '[Not specified]'}<br>
        <strong>TESTS ORDERED:</strong> {', '.join([COMPONENT_LIBRARY[m]['name'].split(':')[1].strip() for m in selected_modules])}
    </div>
    <div style="background-color: white; padding: 1rem; border-radius: 5px; margin: 1rem 0;">
    <strong>COMPONENTS TO PICK:</strong><br>
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
        </div>
    """, unsafe_allow_html=True)
    
    # Download buttons
    col_pdf, col_csv = st.columns(2)
    
    with col_pdf:
        # Generate PDF
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
        
        pdf_buffer = generate_pdf_picklist(order_info, pick_list_items, special_notes, cost_info)
        
        st.download_button(
            label="📄 Download PDF Pick List",
            data=pdf_buffer,
            file_name=f"KELP_PickList_{order_number}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    
    with col_csv:
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
    
    # Save/Clear buttons
    st.divider()
    col_save, col_clear = st.columns(2)
    
    with col_save:
        if st.button("💾 Save Order to History", type="primary", use_container_width=True, key=get_key("save_btn")):
            order_data = {
                'order_number': order_number,
                'customer': customer_name,
                'project': project_name,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'modules': selected_modules,
                'sharing': sharing_a_c,
                'shipping': shipping_key,
                'total_cost': total_cost,
                'customer_price': customer_price,
                'items_count': len(pick_list_items),
                'bottles_count': bottles_count
            }
            st.session_state.order_history.append(order_data)
            st.success(f"✅ Order {order_number} saved successfully!")

else:
    st.info("👆 Please select at least one test module to generate a pick list.")

# Order History
if len(st.session_state.order_history) > 0:
    st.divider()
    st.header("📚 Order History")
    
    df_history = pd.DataFrame(st.session_state.order_history)
    df_history['modules_str'] = df_history['modules'].apply(lambda x: ', '.join([m.replace('module_', '').upper() for m in x]))
    
    display_df = df_history[['order_number', 'customer', 'date', 'modules_str', 'bottles_count', 'customer_price']].copy()
    display_df.columns = ['Order #', 'Customer', 'Date', 'Modules', 'Bottles', 'Price']
    display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:.2f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    if st.button("🗑️ Clear Order History", key=get_key("clear_history")):
        st.session_state.order_history = []
        st.rerun()

# Footer
st.divider()
st.caption(f"""
**KETOS Environmental Laboratory (KELP)** | Smart Kit Builder v2.0 - CORRECTED  
✅ Sample sharing enabled | ✅ Reset button fixed | ✅ PDF generation | ✅ Field parameters removed  
ISO/IEC 17025:2017 Compliant | TNI Accredited  
Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
""")
