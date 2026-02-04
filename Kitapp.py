import streamlit as st
import pandas as pd
from datetime import datetime
import json
import requests
from typing import Dict, Optional, Tuple, List
import base64
import math
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="KELP Kit Builder Pro",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# KIT COMPONENTS MASTER DATA (Using agreed part numbers)
# ============================================================================

KIT_COMPONENTS = {
    "1300-00007": {"type": "Bottle with Label", "description": "For: Anions + Gen Chem"},
    "1300-00008": {"type": "Bottle with Label", "description": "For: Metals"},
    "1300-00009": {"type": "Bottle with Label", "description": "For: Nutrients"},
    "1300-00010": {"type": "Bottle with Label", "description": "For: PFAS"},
    "1300-00058": {"type": "Box (Kit)", "description": "Shipping Box"},
    "1300-00018": {"type": "Gloves", "description": "Nitrile - Size L"},
    "1300-00019": {"type": "Gloves PFAS Free", "description": "PFAS-free gloves"},
    "1300-00027": {"type": "Packaging", "description": "Bottle protection (Generic)"},
    "1300-00028": {"type": "Packaging for PFAS", "description": "Bottle protection (PFAS)"},
    "1300-00029": {"type": "Printed document", "description": "Collection Instructions"},
    "1300-00030": {"type": "Printed document", "description": "COC Form"},
}

# Module definitions with bottle mappings
MODULE_LIBRARY = {
    'MOD-A': {
        'name': 'General Chemistry',
        'description': 'Alkalinity, Hardness, TDS, pH, Conductivity',
        'bottle_part': '1300-00007',
        'bottles_needed': 1,
        'can_share_with': 'MOD-C',
        'methods': ['SM 2320B', 'SM 2340C', 'SM 2510B', 'SM 2540C'],
        'weight_lbs': 0.3,
    },
    'MOD-B': {
        'name': 'Metals (ICP-MS)',
        'description': 'EPA 200.8 Full Metals Panel',
        'bottle_part': '1300-00008',
        'bottles_needed': 1,
        'can_share_with': None,
        'methods': ['EPA 200.8'],
        'special_handling': 'Pre-acidified HNO₃',
        'weight_lbs': 0.4,
    },
    'MOD-C': {
        'name': 'Anions (IC)',
        'description': 'Chloride, Sulfate, Fluoride, Nitrate, Phosphate',
        'bottle_part': '1300-00007',
        'bottles_needed': 1,
        'can_share_with': 'MOD-A',
        'methods': ['EPA 300.1'],
        'weight_lbs': 0.3,
    },
    'MOD-D': {
        'name': 'Nutrients',
        'description': 'Nitrate, Nitrite (EPA 353.2)',
        'bottle_part': '1300-00009',
        'bottles_needed': 1,
        'can_share_with': None,
        'methods': ['EPA 353.2', 'EPA 365.1'],
        'special_handling': 'Pre-acidified H₂SO₄',
        'weight_lbs': 0.5,
    },
    'MOD-P': {
        'name': 'PFAS Testing',
        'description': 'EPA 537.1/533/1633A PFAS Panel',
        'bottle_part': '1300-00010',
        'bottles_needed': 2,  # Always 2 bottles for PFAS
        'can_share_with': None,
        'methods': ['EPA 537.1', 'EPA 533', 'EPA 1633A'],
        'special_handling': 'PFAS-free gloves required',
        'weight_lbs': 0.8,
    },
}

# Bundle definitions with module flags
BUNDLE_DEFINITIONS = {
    'RES-001': {'name': 'Essential Home Water Test', 'modules': ['MOD-A', 'MOD-B', 'MOD-C']},
    'RES-002': {'name': 'Complete Homeowner', 'modules': ['MOD-A', 'MOD-B', 'MOD-C', 'MOD-D']},
    'RES-004': {'name': 'Basic PFAS Screen', 'modules': ['MOD-B', 'MOD-C', 'MOD-P']},
    'RES-005': {'name': 'Comprehensive Home Safety', 'modules': ['MOD-A', 'MOD-B', 'MOD-C', 'MOD-P']},
    'RES-006': {'name': 'Ultimate Water Safety Suite', 'modules': ['MOD-A', 'MOD-B', 'MOD-C', 'MOD-D', 'MOD-P']},
    'RE-001': {'name': 'Real Estate Well Water', 'modules': ['MOD-A', 'MOD-B', 'MOD-C', 'MOD-D']},
    'RE-002': {'name': 'Conventional Loan Testing', 'modules': ['MOD-A', 'MOD-B', 'MOD-C']},
    'COM-001': {'name': 'Food & Beverage Water Quality', 'modules': ['MOD-A', 'MOD-B', 'MOD-C']},
    'COM-002': {'name': 'Agricultural Irrigation', 'modules': ['MOD-A', 'MOD-B', 'MOD-C']},
}

# Assembly rules
ASSEMBLY_RULES = {
    'ac_sharing': "MOD-A and MOD-C share bottle 1300-00007 when both selected",
    'pfas_always_2': "MOD-P always requires 2 bottles (1300-00010)",
    'max_per_package': 2,  # Max bottles per shipping box
    'pfas_gloves': "Use 1300-00019 (PFAS-free) instead of 1300-00018 when PFAS included",
    'pkg_multiplier': "Box, gloves, instructions multiply by package count",
}

ASSEMBLY_TIME_MINUTES = 7  # Per package


# ============================================================================
# PICK LIST GENERATION FUNCTIONS
# ============================================================================

def calculate_kit_requirements(selected_modules: List[str]) -> Dict:
    """
    Calculate all kit requirements based on selected modules.
    Applies all assembly rules including A+C sharing and PFAS handling.
    
    Returns dict with:
        - bottles: dict of bottle part numbers and quantities
        - total_bottles: int
        - packages: int
        - has_pfas: bool
        - ac_sharing: bool
        - pick_list: list of (part_number, description, quantity)
    """
    if not selected_modules:
        return {
            'bottles': {},
            'total_bottles': 0,
            'packages': 0,
            'has_pfas': False,
            'ac_sharing': False,
            'pick_list': []
        }
    
    # Check conditions
    has_mod_a = 'MOD-A' in selected_modules
    has_mod_b = 'MOD-B' in selected_modules
    has_mod_c = 'MOD-C' in selected_modules
    has_mod_d = 'MOD-D' in selected_modules
    has_mod_p = 'MOD-P' in selected_modules
    
    ac_sharing = has_mod_a and has_mod_c
    has_pfas = has_mod_p
    
    # Calculate bottles needed
    bottles = {}
    
    # 1300-00007: Anions + Gen Chem (MOD-A and/or MOD-C, shared if both)
    if has_mod_a or has_mod_c:
        bottles['1300-00007'] = 1  # Always 1, even if both (sharing rule)
    
    # 1300-00008: Metals (MOD-B)
    if has_mod_b:
        bottles['1300-00008'] = 1
    
    # 1300-00009: Nutrients (MOD-D)
    if has_mod_d:
        bottles['1300-00009'] = 1
    
    # 1300-00010: PFAS (MOD-P) - always 2
    if has_mod_p:
        bottles['1300-00010'] = 2
    
    total_bottles = sum(bottles.values())
    packages = math.ceil(total_bottles / ASSEMBLY_RULES['max_per_package'])
    packages = max(1, packages)  # At least 1 package
    
    # Build pick list
    pick_list = []
    
    # Shipping boxes (1 per package)
    pick_list.append(('1300-00058', 'Shipping Box', packages))
    
    # Bottles
    for part_num, qty in bottles.items():
        desc = KIT_COMPONENTS[part_num]['description']
        pick_list.append((part_num, f"Bottle: {desc}", qty))
    
    # Gloves (2 pairs per package)
    if has_pfas:
        pick_list.append(('1300-00019', 'Gloves (PFAS-free)', packages * 2))
    else:
        pick_list.append(('1300-00018', 'Gloves (Nitrile)', packages * 2))
    
    # Packaging/protection
    non_pfas_bottles = total_bottles - bottles.get('1300-00010', 0)
    if non_pfas_bottles > 0:
        pick_list.append(('1300-00027', 'Packaging (Generic)', non_pfas_bottles))
    if has_pfas:
        pick_list.append(('1300-00028', 'Packaging (PFAS)', 2))
    
    # Documents
    pick_list.append(('1300-00029', 'Collection Instructions', packages))
    pick_list.append(('1300-00030', 'COC Form', 1))
    
    return {
        'bottles': bottles,
        'total_bottles': total_bottles,
        'packages': packages,
        'has_pfas': has_pfas,
        'ac_sharing': ac_sharing,
        'pick_list': pick_list,
        'selected_modules': selected_modules,
    }


def generate_pick_list_pdf(kit_info: Dict, order_id: str = None, customer_name: str = None) -> bytes:
    """
    Generate a PDF pick list for the kit assembly.
    Returns PDF as bytes.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        st.error("ReportLab not installed. Run: pip install reportlab")
        return None
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0066B2')
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor('#0066B2')
    )
    
    elements = []
    
    # Title
    elements.append(Paragraph("KELP LABORATORY SERVICES", title_style))
    elements.append(Paragraph("Kit Assembly Pick List", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Order info
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    order_info = f"Generated: {timestamp}"
    if order_id:
        order_info += f" | Order: {order_id}"
    if customer_name:
        order_info += f" | Customer: {customer_name}"
    elements.append(Paragraph(order_info, subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary section
    elements.append(Paragraph("Order Summary", section_style))
    
    summary_data = [
        ['Total Bottles:', str(kit_info['total_bottles'])],
        ['Packages:', str(kit_info['packages'])],
        ['A+C Sharing:', 'Yes' if kit_info['ac_sharing'] else 'No'],
        ['PFAS Included:', 'Yes ⚠️' if kit_info['has_pfas'] else 'No'],
        ['Modules:', ', '.join(kit_info['selected_modules'])],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Pick list section
    elements.append(Paragraph("Pick List Items", section_style))
    
    # Table header
    pick_data = [['☐', 'Part Number', 'Description', 'Qty']]
    
    for part_num, desc, qty in kit_info['pick_list']:
        pick_data.append(['☐', part_num, desc, str(qty)])
    
    pick_table = Table(pick_data, colWidths=[0.4*inch, 1.2*inch, 3.5*inch, 0.6*inch])
    pick_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066B2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Checkbox
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Part number
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Description
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Qty
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        
        # Alternate row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    elements.append(pick_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Special notes
    if kit_info['has_pfas'] or kit_info['ac_sharing'] or kit_info['packages'] > 1:
        elements.append(Paragraph("Special Instructions", section_style))
        
        notes = []
        if kit_info['has_pfas']:
            notes.append("⚠️ PFAS ORDER: Use PFAS-free gloves (1300-00019). Do NOT use nitrile gloves.")
        if kit_info['ac_sharing']:
            notes.append("✓ A+C SHARING: MOD-A and MOD-C share one bottle (1300-00007).")
        if kit_info['packages'] > 1:
            notes.append(f"📦 MULTI-PACKAGE: Prepare {kit_info['packages']} separate boxes (max 2 bottles each).")
        
        for note in notes:
            elements.append(Paragraph(note, styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("_" * 60, styles['Normal']))
    elements.append(Spacer(1, 0.1*inch))
    
    footer_data = [
        ['Assembled By:', '_________________', 'Date:', '_________________'],
        ['Verified By:', '_________________', 'Date:', '_________________'],
    ]
    footer_table = Table(footer_data, colWidths=[1*inch, 2*inch, 0.5*inch, 2*inch])
    footer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(footer_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================================
# FEDEX API CLASS
# ============================================================================

class FedExAPI:
    """FedEx API Integration for shipping rates and labels"""
    
    def __init__(self):
        try:
            self.api_key = st.secrets.get("FEDEX_API_KEY", "")
            self.secret_key = st.secrets.get("FEDEX_SECRET_KEY", "")
            self.account_number = st.secrets.get("FEDEX_ACCOUNT_NUMBER", "")
        except:
            self.api_key = ""
            self.secret_key = ""
            self.account_number = ""
        
        self.demo_mode = not all([self.api_key, self.secret_key, self.account_number])
        
        try:
            env = st.secrets.get("FEDEX_ENVIRONMENT", "production")
        except:
            env = "production"
            
        if env == "sandbox":
            self.base_url = "https://apis-sandbox.fedex.com"
        else:
            self.base_url = "https://apis.fedex.com"
            
        self.auth_url = f"{self.base_url}/oauth/token"
        self.rate_url = f"{self.base_url}/rate/v1/rates/quotes"
        
        try:
            self.origin = {
                "streetLines": [st.secrets.get("LAB_STREET", "123 Innovation Way")],
                "city": st.secrets.get("LAB_CITY", "Sunnyvale"),
                "stateOrProvinceCode": st.secrets.get("LAB_STATE", "CA"),
                "postalCode": st.secrets.get("LAB_ZIP", "94085"),
                "countryCode": "US"
            }
        except:
            self.origin = {
                "streetLines": ["123 Innovation Way"],
                "city": "Sunnyvale",
                "stateOrProvinceCode": "CA",
                "postalCode": "94085",
                "countryCode": "US"
            }
        
        self.access_token = None
        self.auth_failed = False
    
    def calculate_shipping_rate(self, destination: Dict, weight_lbs: float, 
                                service_type: str = "FEDEX_GROUND") -> Optional[Dict]:
        """Calculate shipping rate (demo mode returns estimates)"""
        if self.demo_mode:
            base_rate = 50.0 if service_type == "FEDEX_2_DAY" else 12.0
            if weight_lbs > 5:
                base_rate += (weight_lbs - 5) * 2
            
            return {
                'total_charge': round(base_rate, 2),
                'service_name': 'FedEx 2Day' if service_type == "FEDEX_2_DAY" else 'FedEx Ground',
                'transit_time': '2 business days' if service_type == "FEDEX_2_DAY" else '3-5 business days',
                'demo_mode': True
            }
        
        # Real API call would go here
        return None


# ============================================================================
# STREAMLIT UI
# ============================================================================

# Initialize session state
if 'selected_modules' not in st.session_state:
    st.session_state.selected_modules = []
if 'selected_bundle' not in st.session_state:
    st.session_state.selected_bundle = None
if 'shipping_address' not in st.session_state:
    st.session_state.shipping_address = None
if 'order_history' not in st.session_state:
    st.session_state.order_history = []

# Initialize FedEx
fedex = FedExAPI()

# Header
st.title("🧪 KELP Kit Builder Pro")
st.markdown("*Professional water testing kit assembly system*")

if fedex.demo_mode:
    st.sidebar.info("ℹ️ **FedEx Demo Mode** - Using estimated shipping rates")

st.divider()

# ============================================================================
# STEP 1: SELECT BUNDLE OR CUSTOM MODULES
# ============================================================================

st.header("1️⃣ Select Testing Package")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Pre-configured Bundles")
    
    bundle_options = ["-- Select Bundle --"] + list(BUNDLE_DEFINITIONS.keys())
    selected_bundle = st.selectbox(
        "Choose a bundle:",
        bundle_options,
        format_func=lambda x: f"{x}: {BUNDLE_DEFINITIONS[x]['name']}" if x in BUNDLE_DEFINITIONS else x
    )
    
    if selected_bundle != "-- Select Bundle --":
        bundle = BUNDLE_DEFINITIONS[selected_bundle]
        st.success(f"**{bundle['name']}**")
        st.write(f"Modules: {', '.join(bundle['modules'])}")
        st.session_state.selected_modules = bundle['modules']
        st.session_state.selected_bundle = selected_bundle

with col2:
    st.subheader("Or Custom Selection")
    
    custom_modules = []
    for mod_id, mod_info in MODULE_LIBRARY.items():
        if st.checkbox(f"{mod_id}: {mod_info['name']}", key=f"custom_{mod_id}"):
            custom_modules.append(mod_id)
    
    if custom_modules and selected_bundle == "-- Select Bundle --":
        st.session_state.selected_modules = custom_modules
        st.session_state.selected_bundle = "CUSTOM"

st.divider()

# ============================================================================
# STEP 2: VIEW KIT REQUIREMENTS & PICK LIST
# ============================================================================

st.header("2️⃣ Kit Requirements & Pick List")

if st.session_state.selected_modules:
    kit_info = calculate_kit_requirements(st.session_state.selected_modules)
    
    # Summary metrics
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Bottles", kit_info['total_bottles'])
    with col_m2:
        st.metric("Packages", kit_info['packages'])
    with col_m3:
        st.metric("A+C Sharing", "Yes ✓" if kit_info['ac_sharing'] else "No")
    with col_m4:
        st.metric("PFAS", "Yes ⚠️" if kit_info['has_pfas'] else "No")
    
    # Special alerts
    if kit_info['has_pfas']:
        st.warning("⚠️ **PFAS ORDER**: Use PFAS-free gloves (1300-00019). Do NOT use standard nitrile.")
    
    if kit_info['ac_sharing']:
        st.info("✓ **A+C SHARING ACTIVE**: MOD-A and MOD-C share one bottle (1300-00007)")
    
    if kit_info['packages'] > 1:
        st.info(f"📦 **MULTI-PACKAGE ORDER**: {kit_info['packages']} boxes required (max 2 bottles per box)")
    
    # Pick list table
    st.subheader("📋 Pick List")
    
    pick_df = pd.DataFrame(kit_info['pick_list'], columns=['Part Number', 'Description', 'Qty'])
    st.dataframe(pick_df, use_container_width=True, hide_index=True)
    
    # PDF Download button
    st.subheader("📄 Print Pick List")
    
    col_pdf1, col_pdf2 = st.columns([2, 1])
    with col_pdf1:
        order_id = st.text_input("Order ID (optional):", placeholder="e.g., ORD-2024-001")
        customer_name = st.text_input("Customer Name (optional):", placeholder="e.g., John Smith")
    
    with col_pdf2:
        st.write("")  # Spacer
        st.write("")
        if st.button("🖨️ Generate PDF Pick List", type="primary", use_container_width=True):
            with st.spinner("Generating PDF..."):
                try:
                    pdf_bytes = generate_pick_list_pdf(kit_info, order_id, customer_name)
                    if pdf_bytes:
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_bytes,
                            file_name=f"KELP_PickList_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.success("✅ PDF generated successfully!")
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")
                    st.info("Make sure reportlab is installed: `pip install reportlab`")

else:
    st.info("👆 Select a bundle or modules above to see kit requirements")

st.divider()

# ============================================================================
# STEP 3: SHIPPING
# ============================================================================

st.header("3️⃣ Shipping")

if st.session_state.selected_modules:
    kit_info = calculate_kit_requirements(st.session_state.selected_modules)
    
    col_ship1, col_ship2 = st.columns(2)
    
    with col_ship1:
        st.subheader("Destination Address")
        street = st.text_input("Street Address:")
        city = st.text_input("City:")
        state = st.text_input("State (2-letter):", max_chars=2)
        zip_code = st.text_input("ZIP Code:", max_chars=10)
        
        if all([street, city, state, zip_code]):
            st.session_state.shipping_address = {
                "streetLines": [street],
                "city": city,
                "stateOrProvinceCode": state.upper(),
                "postalCode": zip_code,
                "countryCode": "US"
            }
    
    with col_ship2:
        st.subheader("Shipping Options")
        
        has_pfas = kit_info['has_pfas']
        
        if has_pfas:
            st.warning("⚠️ PFAS samples require 2-Day shipping for holding time compliance")
            service_type = "FEDEX_2_DAY"
            st.write("**Service:** FedEx 2Day (Required)")
        else:
            service_option = st.radio(
                "Select service:",
                ["FedEx Ground (3-5 days)", "FedEx 2Day"],
                index=0
            )
            service_type = "FEDEX_2_DAY" if "2Day" in service_option else "FEDEX_GROUND"
        
        if st.session_state.shipping_address:
            if st.button("📦 Calculate Shipping", use_container_width=True):
                # Calculate weight
                base_weight = 1.5 * kit_info['packages']  # Base kit weight per package
                module_weight = sum(
                    MODULE_LIBRARY[m].get('weight_lbs', 0.3) 
                    for m in st.session_state.selected_modules
                )
                total_weight = base_weight + module_weight
                
                rate = fedex.calculate_shipping_rate(
                    st.session_state.shipping_address,
                    total_weight,
                    service_type
                )
                
                if rate:
                    st.success(f"**{rate['service_name']}**: ${rate['total_charge']:.2f}")
                    st.caption(f"Transit: {rate['transit_time']}")
                    if rate.get('demo_mode'):
                        st.caption("(Demo mode - estimated rate)")
else:
    st.info("👆 Select modules first to configure shipping")

st.divider()

# ============================================================================
# STEP 4: ORDER SUMMARY
# ============================================================================

st.header("4️⃣ Order Summary")

if st.session_state.selected_modules:
    kit_info = calculate_kit_requirements(st.session_state.selected_modules)
    
    col_sum1, col_sum2 = st.columns(2)
    
    with col_sum1:
        st.markdown("**Selected Modules:**")
        for mod_id in st.session_state.selected_modules:
            mod = MODULE_LIBRARY[mod_id]
            st.write(f"• {mod_id}: {mod['name']}")
        
        st.markdown(f"\n**Bundle:** {st.session_state.selected_bundle or 'Custom'}")
    
    with col_sum2:
        st.markdown("**Kit Details:**")
        st.write(f"• Bottles: {kit_info['total_bottles']}")
        st.write(f"• Packages: {kit_info['packages']}")
        st.write(f"• Assembly time: ~{ASSEMBLY_TIME_MINUTES * kit_info['packages']} minutes")
    
    st.divider()
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("💾 Save Order", type="primary", use_container_width=True):
            order = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'bundle': st.session_state.selected_bundle,
                'modules': st.session_state.selected_modules,
                'bottles': kit_info['total_bottles'],
                'packages': kit_info['packages'],
                'has_pfas': kit_info['has_pfas'],
            }
            st.session_state.order_history.append(order)
            st.success("✅ Order saved!")
            st.balloons()
    
    with col_btn2:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.selected_modules = []
            st.session_state.selected_bundle = None
            st.session_state.shipping_address = None
            st.rerun()

else:
    st.info("👆 Complete the steps above to view order summary")

# ============================================================================
# ORDER HISTORY
# ============================================================================

if st.session_state.order_history:
    st.divider()
    st.header("📊 Order History")
    
    history_df = pd.DataFrame(st.session_state.order_history)
    st.dataframe(history_df, use_container_width=True, hide_index=True)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
---
**KELP Kit Builder Pro v3.0** | Part Number Integration | PDF Pick Lists | February 2026  

**Part Numbers Used:**
- Bottles: 1300-00007 (Anions/GenChem), 1300-00008 (Metals), 1300-00009 (Nutrients), 1300-00010 (PFAS)
- Packaging: 1300-00058 (Box), 1300-00027 (Generic), 1300-00028 (PFAS)
- Gloves: 1300-00018 (Nitrile), 1300-00019 (PFAS-free)
- Documents: 1300-00029 (Instructions), 1300-00030 (COC)

**Assembly Rules:**
- MOD-A + MOD-C share bottle 1300-00007
- MOD-P always requires 2 bottles + PFAS-free gloves
- Max 2 bottles per shipping box
---
""")
