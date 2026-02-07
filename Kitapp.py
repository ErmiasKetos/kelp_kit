"""
KELP Smart Kit Builder Pro v8.0
===============================
Enterprise-Grade Water Testing Kit Configuration System

Features:
- Multi-step wizard navigation
- Professional pick list formatting
- Auto-generated order numbers
- Pre-packed bundle support
- Custom order support
- PDF generation

Author: KELP Laboratory Services
Version: 8.0
Date: February 2026
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List
import math
from io import BytesIO
import random

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="KELP Kit Builder Pro",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =============================================================================
# CONSTANTS & DATA
# =============================================================================

PREPACKED_KITS = {
    '1300-00001_REV01': {
        'name': 'KIT KELP (Metals + Anion + Gen Chem)',
        'weight_lbs': 2.5
    },
    '1300-00003_REV01': {
        'name': 'KIT KELP (PFAS)',
        'weight_lbs': 1.5
    }
}

BUNDLE_CATALOG = {
    'COM-001': {
        'name': 'Food & Beverage Water Quality Package',
        'type': 'Commercial',
        'description': 'Process water quality testing for F&B operations',
        'price': 325.00,
        'kits': {'1300-00001_REV01': 1}
    },
    'COM-002': {
        'name': 'Agricultural Irrigation Package',
        'type': 'Commercial',
        'description': 'Irrigation water quality assessment',
        'price': 295.00,
        'kits': {'1300-00001_REV01': 1}
    },
    'RE-001': {
        'name': 'Real Estate Well Water Package',
        'type': 'Real Estate',
        'description': 'Well water testing for property transactions',
        'price': 399.00,
        'kits': {'1300-00001_REV01': 1}
    },
    'RE-002': {
        'name': 'Conventional Loan Testing Package',
        'type': 'Real Estate',
        'description': 'Standard loan requirement testing',
        'price': 275.00,
        'kits': {'1300-00001_REV01': 1}
    },
    'RES-001': {
        'name': 'Essential Home Water Test Package',
        'type': 'Residential',
        'description': 'Basic water quality for homeowners',
        'price': 249.00,
        'kits': {'1300-00001_REV01': 1}
    },
    'RES-002': {
        'name': 'Complete Homeowner Package',
        'type': 'Residential',
        'description': 'Comprehensive water quality with nutrients',
        'price': 349.00,
        'kits': {'1300-00001_REV01': 1}
    },
    'RES-003': {
        'name': 'PFAS Home Safety Package',
        'type': 'Residential + PFAS',
        'description': 'Standard testing plus PFAS screening',
        'price': 475.00,
        'kits': {'1300-00001_REV01': 1, '1300-00003_REV01': 1}
    },
    'RES-004': {
        'name': 'Basic PFAS Screen',
        'type': 'Residential + PFAS',
        'description': 'PFAS testing with essential metals and anions',
        'price': 495.00,
        'kits': {'1300-00001_REV01': 1, '1300-00003_REV01': 1}
    },
    'RES-005': {
        'name': 'Comprehensive Home Safety Screen',
        'type': 'Residential + PFAS',
        'description': 'Full panel including PFAS',
        'price': 595.00,
        'kits': {'1300-00001_REV01': 1, '1300-00003_REV01': 1}
    },
    'RES-006': {
        'name': 'Ultimate Water Safety Suite',
        'type': 'Residential + PFAS',
        'description': 'Complete testing - all parameters including PFAS',
        'price': 795.00,
        'kits': {'1300-00001_REV01': 1, '1300-00003_REV01': 1}
    }
}

TEST_PARAMETERS = {
    'general_chemistry': {
        'name': 'General Chemistry',
        'bottle': '1300-00007',
        'cost': 2.50,
        'weight': 0.3,
        'tests': ['Alkalinity', 'Hardness', 'TDS', 'pH', 'Conductivity']
    },
    'metals': {
        'name': 'Metals (ICP-MS)',
        'bottle': '1300-00008',
        'cost': 5.00,
        'weight': 0.4,
        'tests': ['EPA 200.8 - Full Metals Panel']
    },
    'anions': {
        'name': 'Anions',
        'bottle': '1300-00007',
        'cost': 1.50,
        'cost_when_shared': 0.00,
        'weight': 0.3,
        'tests': ['Chloride', 'Sulfate', 'Fluoride', 'Nitrate']
    },
    'nutrients': {
        'name': 'Nutrients',
        'bottle': '1300-00009',
        'cost': 4.00,
        'weight': 0.5,
        'tests': ['Nitrate/Nitrite', 'Phosphate']
    },
    'pfas': {
        'name': 'PFAS Testing',
        'bottle': '1300-00010',
        'bottle_qty': 2,
        'cost': 15.50,
        'weight': 0.8,
        'tests': ['EPA 537.1/533/1633A PFAS Panel']
    }
}

BASE_KIT_COST = 9.50
BASE_KIT_WEIGHT = 1.5
ASSEMBLY_TIME = 7

STEP_NAMES = [
    "Order Type",
    "Selection", 
    "Shipping",
    "Review",
    "Pick List"
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_order_number() -> str:
    """Generate order number: ORDER-MM-DD-YYYY-XXX"""
    now = datetime.now()
    seq = random.randint(100, 999)
    return f"ORDER-{now.strftime('%m-%d-%Y')}-{seq}"


def bundle_has_pfas(sku: str) -> bool:
    return '1300-00003_REV01' in BUNDLE_CATALOG.get(sku, {}).get('kits', {})


def get_bundle_kits(sku: str) -> int:
    return sum(BUNDLE_CATALOG.get(sku, {}).get('kits', {}).values())


def get_bundle_weight(sku: str) -> float:
    total = 0.0
    for kit, qty in BUNDLE_CATALOG.get(sku, {}).get('kits', {}).items():
        total += PREPACKED_KITS.get(kit, {}).get('weight_lbs', 0) * qty
    return total


def calc_custom_order(tests: List[str]) -> Dict:
    sharing = 'general_chemistry' in tests and 'anions' in tests
    has_pfas = 'pfas' in tests
    
    bottles = 0
    for t in tests:
        if t == 'general_chemistry':
            bottles += 1
        elif t == 'metals':
            bottles += 1
        elif t == 'anions' and not sharing:
            bottles += 1
        elif t == 'nutrients':
            bottles += 1
        elif t == 'pfas':
            bottles += 2
    
    packages = max(1, math.ceil(bottles / 2))
    
    weight = BASE_KIT_WEIGHT * packages
    cost = BASE_KIT_COST * packages
    
    for t in tests:
        if t in TEST_PARAMETERS:
            weight += TEST_PARAMETERS[t]['weight']
            if t == 'anions' and sharing:
                cost += TEST_PARAMETERS[t].get('cost_when_shared', 0)
            else:
                cost += TEST_PARAMETERS[t]['cost']
    
    return {
        'bottles': bottles,
        'packages': packages,
        'weight': round(weight, 2),
        'cost': round(cost, 2),
        'sharing': sharing,
        'has_pfas': has_pfas
    }


def estimate_shipping(compliance: bool, packages: int) -> float:
    return (50.0 if compliance else 12.0) * packages


# =============================================================================
# PICK LIST GENERATION
# =============================================================================

def create_bundle_picklist(sku: str, order_num: str) -> Dict:
    bundle = BUNDLE_CATALOG[sku]
    items = []
    
    for kit_sku, qty in bundle['kits'].items():
        items.append({
            'part': kit_sku,
            'desc': PREPACKED_KITS[kit_sku]['name'],
            'qty': qty
        })
    
    return {
        'order_number': order_num,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'type': 'BUNDLE',
        'bundle_sku': sku,
        'bundle_name': bundle['name'],
        'bundle_type': bundle['type'],
        'total_kits': sum(bundle['kits'].values()),
        'has_pfas': '1300-00003_REV01' in bundle['kits'],
        'items': items
    }


def create_custom_picklist(tests: List[str], info: Dict, order_num: str) -> Dict:
    items = []
    
    # Boxes
    items.append({'part': '1300-00058', 'desc': 'Shipping Box', 'qty': info['packages']})
    
    # Bottles
    if 'general_chemistry' in tests or 'anions' in tests:
        items.append({'part': '1300-00007', 'desc': 'Bottle: Anions + Gen Chem', 'qty': 1})
    if 'metals' in tests:
        items.append({'part': '1300-00008', 'desc': 'Bottle: Metals (HNO₃ preserved)', 'qty': 1})
    if 'nutrients' in tests:
        items.append({'part': '1300-00009', 'desc': 'Bottle: Nutrients (H₂SO₄ preserved)', 'qty': 1})
    if 'pfas' in tests:
        items.append({'part': '1300-00010', 'desc': 'Bottle: PFAS', 'qty': 2})
    
    # Gloves
    if info['has_pfas']:
        items.append({'part': '1300-00019', 'desc': 'Gloves - PFAS-free', 'qty': info['packages'] * 2})
    else:
        items.append({'part': '1300-00018', 'desc': 'Gloves - Nitrile', 'qty': info['packages'] * 2})
    
    # Packaging
    non_pfas = info['bottles'] - (2 if info['has_pfas'] else 0)
    if non_pfas > 0:
        items.append({'part': '1300-00027', 'desc': 'Bottle Protection - Standard', 'qty': non_pfas})
    if info['has_pfas']:
        items.append({'part': '1300-00028', 'desc': 'Bottle Protection - PFAS', 'qty': 2})
    
    # Instructions only (no COC)
    items.append({'part': '1300-00029', 'desc': 'Collection Instructions', 'qty': info['packages']})
    
    test_names = [TEST_PARAMETERS[t]['name'] for t in tests]
    
    return {
        'order_number': order_num,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'type': 'CUSTOM',
        'tests': test_names,
        'bottles': info['bottles'],
        'packages': info['packages'],
        'sharing': info['sharing'],
        'has_pfas': info['has_pfas'],
        'assembly_time': ASSEMBLY_TIME * info['packages'],
        'items': items
    }


def format_professional_picklist(pl: Dict) -> str:
    """Generate professional formatted pick list"""
    lines = []
    
    # Header
    lines.append("┌" + "─" * 68 + "┐")
    lines.append("│" + " " * 68 + "│")
    lines.append("│" + "KELP LABORATORY SERVICES".center(68) + "│")
    lines.append("│" + "Kit Assembly Pick List".center(68) + "│")
    lines.append("│" + " " * 68 + "│")
    lines.append("├" + "─" * 68 + "┤")
    
    # Order Info
    lines.append("│" + " " * 68 + "│")
    lines.append("│  " + f"Order Number: {pl['order_number']}".ljust(66) + "│")
    lines.append("│  " + f"Generated: {pl['timestamp']}".ljust(66) + "│")
    lines.append("│  " + f"Order Type: {pl['type']}".ljust(66) + "│")
    
    if pl['type'] == 'BUNDLE':
        lines.append("│" + " " * 68 + "│")
        lines.append("│  " + f"Bundle: {pl['bundle_sku']} - {pl['bundle_name']}".ljust(66) + "│")
        lines.append("│  " + f"Category: {pl['bundle_type']}".ljust(66) + "│")
        lines.append("│  " + f"Total Kits: {pl['total_kits']}".ljust(66) + "│")
    else:
        lines.append("│" + " " * 68 + "│")
        lines.append("│  " + f"Tests: {', '.join(pl['tests'])}".ljust(66) + "│")
        lines.append("│  " + f"Bottles: {pl['bottles']} | Packages: {pl['packages']}".ljust(66) + "│")
        if pl['sharing']:
            lines.append("│  " + "Bottle Sharing: Yes (Gen Chem + Anions)".ljust(66) + "│")
        lines.append("│  " + f"Est. Assembly: {pl['assembly_time']} minutes".ljust(66) + "│")
    
    pfas_status = "YES ⚠" if pl['has_pfas'] else "No"
    lines.append("│  " + f"PFAS Included: {pfas_status}".ljust(66) + "│")
    lines.append("│" + " " * 68 + "│")
    
    # Pick List Header
    lines.append("├" + "─" * 68 + "┤")
    lines.append("│" + " " * 68 + "│")
    lines.append("│  " + "PICK LIST ITEMS".ljust(66) + "│")
    lines.append("│" + " " * 68 + "│")
    lines.append("│  " + "─" * 64 + "  │")
    lines.append("│  " + f"{'☐':<3}{'Part Number':<22}{'Description':<32}{'Qty':>7}" + "  │")
    lines.append("│  " + "─" * 64 + "  │")
    
    # Items
    for item in pl['items']:
        line = f"{'☐':<3}{item['part']:<22}{item['desc']:<32}{item['qty']:>7}"
        lines.append("│  " + line + "  │")
    
    lines.append("│  " + "─" * 64 + "  │")
    lines.append("│" + " " * 68 + "│")
    
    # Special Instructions
    if pl['type'] == 'BUNDLE':
        lines.append("│  " + "INSTRUCTIONS:".ljust(66) + "│")
        lines.append("│  " + "• Pre-packed bundle - no individual component picking required".ljust(66) + "│")
        if pl['has_pfas']:
            lines.append("│  " + "• ⚠ PFAS kit included - use PFAS-free gloves when handling".ljust(66) + "│")
    else:
        lines.append("│  " + "INSTRUCTIONS:".ljust(66) + "│")
        lines.append("│  " + "• Assemble components as listed above".ljust(66) + "│")
        if pl['packages'] > 1:
            lines.append("│  " + f"• Split into {pl['packages']} packages (max 2 bottles per box)".ljust(66) + "│")
        if pl['has_pfas']:
            lines.append("│  " + "• ⚠ PFAS order - use PFAS-free gloves and PFAS packaging ONLY".ljust(66) + "│")
        if pl['sharing']:
            lines.append("│  " + "• Gen Chem & Anions share bottle 1300-00007".ljust(66) + "│")
    
    lines.append("│" + " " * 68 + "│")
    
    # Signatures
    lines.append("├" + "─" * 68 + "┤")
    lines.append("│" + " " * 68 + "│")
    lines.append("│  " + "VERIFICATION".ljust(66) + "│")
    lines.append("│" + " " * 68 + "│")
    lines.append("│  " + "Assembled By: ________________________  Date: ______________".ljust(66) + "│")
    lines.append("│" + " " * 68 + "│")
    lines.append("│  " + "Verified By:  ________________________  Date: ______________".ljust(66) + "│")
    lines.append("│" + " " * 68 + "│")
    lines.append("└" + "─" * 68 + "┘")
    
    return "\n".join(lines)


def generate_pdf(pl: Dict) -> Optional[bytes]:
    """Generate professional PDF pick list"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        return None
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, 
                                  spaceAfter=4, alignment=TA_CENTER, 
                                  textColor=colors.HexColor('#003366'))
    
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=14, 
                                     spaceAfter=20, alignment=TA_CENTER,
                                     textColor=colors.HexColor('#666666'))
    
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=12,
                                    spaceBefore=16, spaceAfter=8, 
                                    textColor=colors.HexColor('#003366'),
                                    borderPadding=4)
    
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10,
                                   spaceAfter=4)
    
    elements = []
    
    # Header
    elements.append(Paragraph("KELP LABORATORY SERVICES", title_style))
    elements.append(Paragraph("Kit Assembly Pick List", subtitle_style))
    
    # Divider
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#003366')))
    elements.append(Spacer(1, 0.2*inch))
    
    # Order Info Box
    order_info = [
        [Paragraph(f"<b>Order Number:</b> {pl['order_number']}", normal_style),
         Paragraph(f"<b>Generated:</b> {pl['timestamp']}", normal_style)],
        [Paragraph(f"<b>Order Type:</b> {pl['type']}", normal_style),
         Paragraph(f"<b>PFAS Included:</b> {'YES ⚠️' if pl['has_pfas'] else 'No'}", normal_style)]
    ]
    
    if pl['type'] == 'BUNDLE':
        order_info.append([
            Paragraph(f"<b>Bundle:</b> {pl['bundle_sku']}", normal_style),
            Paragraph(f"<b>Name:</b> {pl['bundle_name']}", normal_style)
        ])
        order_info.append([
            Paragraph(f"<b>Category:</b> {pl['bundle_type']}", normal_style),
            Paragraph(f"<b>Total Kits:</b> {pl['total_kits']}", normal_style)
        ])
    else:
        order_info.append([
            Paragraph(f"<b>Tests:</b> {', '.join(pl['tests'])}", normal_style),
            Paragraph(f"<b>Assembly Time:</b> {pl['assembly_time']} min", normal_style)
        ])
        order_info.append([
            Paragraph(f"<b>Bottles:</b> {pl['bottles']}", normal_style),
            Paragraph(f"<b>Packages:</b> {pl['packages']}", normal_style)
        ])
    
    info_table = Table(order_info, colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F8FA')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#003366')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Pick List Section
    elements.append(Paragraph("Pick List Items", section_style))
    
    # Table Header
    tbl_data = [[
        Paragraph("<b>✓</b>", normal_style),
        Paragraph("<b>Part Number</b>", normal_style),
        Paragraph("<b>Description</b>", normal_style),
        Paragraph("<b>Qty</b>", normal_style)
    ]]
    
    # Table Rows
    for item in pl['items']:
        tbl_data.append([
            "☐",
            item['part'],
            item['desc'],
            str(item['qty'])
        ])
    
    pick_table = Table(tbl_data, colWidths=[0.4*inch, 1.8*inch, 4.0*inch, 0.6*inch])
    pick_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        
        # Body
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#003366')),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        
        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
    ]))
    elements.append(pick_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Instructions
    elements.append(Paragraph("Special Instructions", section_style))
    
    if pl['type'] == 'BUNDLE':
        elements.append(Paragraph("• Pre-packed bundle order - no individual component picking required", normal_style))
        if pl['has_pfas']:
            elements.append(Paragraph("• <b>⚠️ PFAS kit included</b> - Handle with PFAS-free gloves", normal_style))
    else:
        elements.append(Paragraph("• Assemble all components as listed in the pick list above", normal_style))
        if pl['packages'] > 1:
            elements.append(Paragraph(f"• <b>Multiple packages:</b> Split into {pl['packages']} boxes (max 2 bottles per box)", normal_style))
        if pl['has_pfas']:
            elements.append(Paragraph("• <b>⚠️ PFAS order:</b> Use PFAS-free gloves and PFAS packaging ONLY", normal_style))
        if pl.get('sharing'):
            elements.append(Paragraph("• <b>Bottle sharing:</b> General Chemistry & Anions share bottle 1300-00007", normal_style))
    
    elements.append(Spacer(1, 0.4*inch))
    
    # Signature Section
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CCCCCC')))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Verification", section_style))
    
    sig_data = [
        ["Assembled By:", "_" * 35, "Date:", "_" * 15],
        ["", "", "", ""],
        ["Verified By:", "_" * 35, "Date:", "_" * 15],
    ]
    
    sig_table = Table(sig_data, colWidths=[1*inch, 2.5*inch, 0.6*inch, 1.5*inch])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# CUSTOM CSS
# =============================================================================

st.markdown("""
<style>
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main container */
    .main { background-color: #f5f7fa; }
    
    /* Step indicator */
    .step-container {
        display: flex;
        justify-content: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .step-item {
        display: flex;
        align-items: center;
        margin: 0 0.5rem;
    }
    
    .step-circle {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 14px;
        margin-right: 8px;
    }
    
    .step-active .step-circle {
        background: #0066B2;
        color: white;
    }
    
    .step-complete .step-circle {
        background: #00A86B;
        color: white;
    }
    
    .step-pending .step-circle {
        background: #E0E0E0;
        color: #999;
    }
    
    .step-label {
        font-size: 13px;
        color: #666;
    }
    
    .step-active .step-label {
        color: #0066B2;
        font-weight: 600;
    }
    
    .step-complete .step-label {
        color: #00A86B;
    }
    
    .step-connector {
        width: 40px;
        height: 2px;
        background: #E0E0E0;
        margin: 0 0.5rem;
    }
    
    .step-connector.complete {
        background: #00A86B;
    }
    
    /* Card styles */
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    
    .card-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: #003366;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #0066B2;
    }
    
    /* Bundle cards */
    .bundle-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 1rem;
    }
    
    .bundle-card {
        background: white;
        border: 2px solid #E0E0E0;
        border-radius: 10px;
        padding: 1rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .bundle-card:hover {
        border-color: #0066B2;
        box-shadow: 0 4px 12px rgba(0,102,178,0.15);
    }
    
    .bundle-card.selected {
        border-color: #00A86B;
        background: #F0FFF4;
    }
    
    /* Price display */
    .price-display {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #003366 0%, #0066B2 100%);
        border-radius: 12px;
        color: white;
    }
    
    .price-label { font-size: 1rem; opacity: 0.9; }
    .price-amount { font-size: 3rem; font-weight: 700; }
    .price-sub { font-size: 0.9rem; opacity: 0.8; }
    
    /* Pick list */
    .picklist-box {
        background: #FAFAFA;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 12px;
        line-height: 1.4;
        white-space: pre;
        overflow-x: auto;
        max-height: 500px;
        overflow-y: auto;
    }
    
    /* Navigation buttons */
    .nav-container {
        display: flex;
        justify-content: space-between;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #E0E0E0;
    }
    
    /* Review section */
    .review-item {
        display: flex;
        justify-content: space-between;
        padding: 0.75rem 0;
        border-bottom: 1px solid #F0F0F0;
    }
    
    .review-label { color: #666; }
    .review-value { font-weight: 600; color: #333; }
    
    /* Success message */
    .success-box {
        background: #F0FFF4;
        border: 2px solid #00A86B;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
    }
    
    .success-icon { font-size: 3rem; margin-bottom: 1rem; }
    .success-title { font-size: 1.5rem; font-weight: 600; color: #00A86B; }
    .success-order { font-size: 1.25rem; color: #333; margin-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

if 'current_step' not in st.session_state:
    st.session_state.current_step = 0
if 'order_mode' not in st.session_state:
    st.session_state.order_mode = None
if 'selected_bundle' not in st.session_state:
    st.session_state.selected_bundle = None
if 'selected_tests' not in st.session_state:
    st.session_state.selected_tests = {}
if 'compliance' not in st.session_state:
    st.session_state.compliance = False
if 'order_number' not in st.session_state:
    st.session_state.order_number = None
if 'pick_list' not in st.session_state:
    st.session_state.pick_list = None
if 'order_complete' not in st.session_state:
    st.session_state.order_complete = False


def reset_wizard():
    st.session_state.current_step = 0
    st.session_state.order_mode = None
    st.session_state.selected_bundle = None
    st.session_state.selected_tests = {}
    st.session_state.compliance = False
    st.session_state.order_number = None
    st.session_state.pick_list = None
    st.session_state.order_complete = False


def go_next():
    st.session_state.current_step += 1


def go_back():
    st.session_state.current_step -= 1


# =============================================================================
# STEP INDICATOR
# =============================================================================

def render_step_indicator():
    step = st.session_state.current_step
    
    html = '<div class="step-container">'
    
    for i, name in enumerate(STEP_NAMES):
        if i < step:
            status = "complete"
            icon = "✓"
        elif i == step:
            status = "active"
            icon = str(i + 1)
        else:
            status = "pending"
            icon = str(i + 1)
        
        html += f'''
        <div class="step-item step-{status}">
            <div class="step-circle">{icon}</div>
            <div class="step-label">{name}</div>
        </div>
        '''
        
        if i < len(STEP_NAMES) - 1:
            conn_class = "complete" if i < step else ""
            html += f'<div class="step-connector {conn_class}"></div>'
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# =============================================================================
# HEADER
# =============================================================================

col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h1 style="color: #003366; margin-bottom: 0;">🧪 KELP Kit Builder Pro</h1>
        <p style="color: #666; font-size: 1rem;">Enterprise Water Testing Kit Configuration</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    if st.button("🔄 Start Over", key="reset_top"):
        reset_wizard()
        st.rerun()

st.divider()

# Render step indicator
render_step_indicator()


# =============================================================================
# STEP 0: ORDER TYPE
# =============================================================================

if st.session_state.current_step == 0:
    st.markdown('<div class="card"><div class="card-header">Select Order Type</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        bundle_selected = st.session_state.order_mode == 'bundle'
        if st.button(
            "📦 Pre-Packed Bundle\n\nSelect from 10 pre-configured packages",
            key="btn_bundle",
            type="primary" if bundle_selected else "secondary",
            use_container_width=True
        ):
            st.session_state.order_mode = 'bundle'
            st.rerun()
    
    with col2:
        custom_selected = st.session_state.order_mode == 'custom'
        if st.button(
            "🔧 Custom Order\n\nBuild your own test combination",
            key="btn_custom",
            type="primary" if custom_selected else "secondary",
            use_container_width=True
        ):
            st.session_state.order_mode = 'custom'
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col3:
        if st.session_state.order_mode:
            if st.button("Next →", key="next_0", type="primary", use_container_width=True):
                go_next()
                st.rerun()
        else:
            st.button("Next →", key="next_0_disabled", disabled=True, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# STEP 1: SELECTION
# =============================================================================

elif st.session_state.current_step == 1:
    
    if st.session_state.order_mode == 'bundle':
        st.markdown('<div class="card"><div class="card-header">Select Bundle</div>', unsafe_allow_html=True)
        
        # Group bundles
        groups = {}
        for sku, data in BUNDLE_CATALOG.items():
            t = data['type']
            if t not in groups:
                groups[t] = []
            groups[t].append((sku, data))
        
        for group_name, bundles in groups.items():
            st.subheader(group_name)
            
            cols = st.columns(3)
            for i, (sku, data) in enumerate(bundles):
                with cols[i % 3]:
                    selected = st.session_state.selected_bundle == sku
                    has_pfas = '1300-00003_REV01' in data['kits']
                    kits = sum(data['kits'].values())
                    
                    # Card content
                    pfas_badge = "⚠️ PFAS" if has_pfas else ""
                    btn_label = f"{'✅ ' if selected else ''}{sku}\n{data['name']}\n{kits} kit(s) • ${data['price']:.0f} {pfas_badge}"
                    
                    if st.button(btn_label, key=f"bundle_{sku}", 
                                type="primary" if selected else "secondary",
                                use_container_width=True):
                        st.session_state.selected_bundle = sku
                        st.rerun()
            
            st.markdown("")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        can_proceed = st.session_state.selected_bundle is not None
    
    else:  # Custom order
        st.markdown('<div class="card"><div class="card-header">Select Tests</div>', unsafe_allow_html=True)
        
        sharing = (st.session_state.selected_tests.get('general_chemistry', False) and 
                   st.session_state.selected_tests.get('anions', False))
        
        for key, data in TEST_PARAMETERS.items():
            checked = st.session_state.selected_tests.get(key, False)
            
            # Special labels
            label = data['name']
            if key == 'pfas':
                label += " ⚠️"
            if key == 'anions' and sharing:
                label += " 🎁 FREE"
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                new_val = st.checkbox(
                    label,
                    value=checked,
                    key=f"test_{key}"
                )
                st.session_state.selected_tests[key] = new_val
                
                # Show details
                if new_val:
                    if key == 'anions' and sharing:
                        st.success("✅ Shares bottle with General Chemistry - FREE!")
                    if key == 'pfas':
                        st.warning("⚠️ Requires PFAS-free handling")
            
            with col2:
                if key == 'anions' and sharing:
                    st.markdown("**$0.00**")
                else:
                    st.markdown(f"**${data['cost']:.2f}**")
            
            st.markdown("---")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        can_proceed = any(st.session_state.selected_tests.values())
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back", key="back_1", use_container_width=True):
            go_back()
            st.rerun()
    with col3:
        if can_proceed:
            if st.button("Next →", key="next_1", type="primary", use_container_width=True):
                go_next()
                st.rerun()
        else:
            st.button("Next →", key="next_1_disabled", disabled=True, use_container_width=True)


# =============================================================================
# STEP 2: SHIPPING
# =============================================================================

elif st.session_state.current_step == 2:
    st.markdown('<div class="card"><div class="card-header">Shipping Options</div>', unsafe_allow_html=True)
    
    st.session_state.compliance = st.checkbox(
        "**Compliance Shipping** (FedEx 2-Day Priority)",
        value=st.session_state.compliance,
        key="compliance_check"
    )
    
    if st.session_state.compliance:
        st.info("📦 FedEx 2-Day shipping for time-sensitive samples")
    else:
        st.info("📦 Standard FedEx Ground shipping (3-5 business days)")
    
    # Calculate and show estimate
    if st.session_state.order_mode == 'bundle':
        packages = get_bundle_kits(st.session_state.selected_bundle)
    else:
        tests = [k for k, v in st.session_state.selected_tests.items() if v]
        info = calc_custom_order(tests)
        packages = info['packages']
    
    ship_est = estimate_shipping(st.session_state.compliance, packages)
    
    st.markdown(f"""
    <div style="background: #F5F8FA; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
        <div style="display: flex; justify-content: space-between;">
            <span>Estimated Shipping ({packages} package{'s' if packages > 1 else ''}):</span>
            <span style="font-weight: 600;">${ship_est:.2f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back", key="back_2", use_container_width=True):
            go_back()
            st.rerun()
    with col3:
        if st.button("Next →", key="next_2", type="primary", use_container_width=True):
            go_next()
            st.rerun()


# =============================================================================
# STEP 3: REVIEW
# =============================================================================

elif st.session_state.current_step == 3:
    st.markdown('<div class="card"><div class="card-header">Review Order</div>', unsafe_allow_html=True)
    
    # Calculate totals
    if st.session_state.order_mode == 'bundle':
        bundle = BUNDLE_CATALOG[st.session_state.selected_bundle]
        base_price = bundle['price']
        packages = get_bundle_kits(st.session_state.selected_bundle)
        has_pfas = bundle_has_pfas(st.session_state.selected_bundle)
        
        st.markdown(f"**Order Type:** Pre-Packed Bundle")
        st.markdown(f"**Bundle:** {st.session_state.selected_bundle} - {bundle['name']}")
        st.markdown(f"**Category:** {bundle['type']}")
        st.markdown(f"**Total Kits:** {packages}")
        
    else:
        tests = [k for k, v in st.session_state.selected_tests.items() if v]
        info = calc_custom_order(tests)
        base_price = info['cost']
        packages = info['packages']
        has_pfas = info['has_pfas']
        
        test_names = [TEST_PARAMETERS[t]['name'] for t in tests]
        st.markdown(f"**Order Type:** Custom Order")
        st.markdown(f"**Tests:** {', '.join(test_names)}")
        st.markdown(f"**Bottles:** {info['bottles']}")
        st.markdown(f"**Packages:** {packages}")
        if info['sharing']:
            st.markdown("**Bottle Sharing:** Yes (Gen Chem + Anions)")
    
    st.markdown(f"**PFAS Included:** {'Yes ⚠️' if has_pfas else 'No'}")
    st.markdown(f"**Shipping:** {'Compliance (2-Day)' if st.session_state.compliance else 'Standard Ground'}")
    
    ship_cost = estimate_shipping(st.session_state.compliance, packages)
    total = base_price + ship_cost
    
    st.markdown(f"""
    <div class="price-display" style="margin-top: 1.5rem;">
        <div class="price-label">Total Price</div>
        <div class="price-amount">${total:.2f}</div>
        <div class="price-sub">Base: ${base_price:.2f} + Shipping: ${ship_cost:.2f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Confirmation
    st.markdown('<div class="card"><div class="card-header">Confirm & Generate Pick List</div>', unsafe_allow_html=True)
    
    st.markdown("Please review the order details above. Click **Confirm & Generate** to create the pick list.")
    
    confirmed = st.checkbox("I confirm this order is correct", key="confirm_order")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back", key="back_3", use_container_width=True):
            go_back()
            st.rerun()
    with col3:
        if confirmed:
            if st.button("Confirm & Generate →", key="next_3", type="primary", use_container_width=True):
                # Generate order number
                st.session_state.order_number = generate_order_number()
                
                # Generate pick list
                if st.session_state.order_mode == 'bundle':
                    st.session_state.pick_list = create_bundle_picklist(
                        st.session_state.selected_bundle,
                        st.session_state.order_number
                    )
                else:
                    tests = [k for k, v in st.session_state.selected_tests.items() if v]
                    info = calc_custom_order(tests)
                    st.session_state.pick_list = create_custom_picklist(
                        tests, info, st.session_state.order_number
                    )
                
                go_next()
                st.rerun()
        else:
            st.button("Confirm & Generate →", key="next_3_disabled", disabled=True, use_container_width=True)


# =============================================================================
# STEP 4: PICK LIST
# =============================================================================

elif st.session_state.current_step == 4:
    pl = st.session_state.pick_list
    
    # Success message
    st.markdown(f"""
    <div class="success-box">
        <div class="success-icon">✅</div>
        <div class="success-title">Pick List Generated Successfully!</div>
        <div class="success-order">{pl['order_number']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")
    
    # Pick List Display
    st.markdown('<div class="card"><div class="card-header">Pick List</div>', unsafe_allow_html=True)
    
    text = format_professional_picklist(pl)
    st.markdown(f'<div class="picklist-box">{text}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Downloads
    st.markdown('<div class="card"><div class="card-header">Download</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            "📥 Download TXT",
            data=text,
            file_name=f"{pl['order_number']}_PickList.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col2:
        pdf_bytes = generate_pdf(pl)
        if pdf_bytes:
            st.download_button(
                "📄 Download PDF",
                data=pdf_bytes,
                file_name=f"{pl['order_number']}_PickList.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.info("PDF requires reportlab: `pip install reportlab`")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation
    st.markdown("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Start New Order", key="new_order", type="primary", use_container_width=True):
            reset_wizard()
            st.rerun()


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("")
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.85rem;">
    KELP Kit Builder Pro v8.0 | Enterprise Edition | © 2026 KELP Laboratory Services
</div>
""", unsafe_allow_html=True)
