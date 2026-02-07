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
    W = 78  # Total width
    IW = W - 4  # Inner width (minus borders and padding)
    
    lines = []
    
    # Helper to create bordered line
    def bordered(text, pad=2):
        return "│" + " " * pad + text.ljust(W - 2 - pad) + "│"
    
    def separator(char="─", left="├", right="┤"):
        return left + char * (W - 2) + right
    
    # Header
    lines.append("┌" + "─" * (W - 2) + "┐")
    lines.append(bordered(""))
    lines.append(bordered("KELP LABORATORY SERVICES".center(IW)))
    lines.append(bordered("Kit Assembly Pick List".center(IW)))
    lines.append(bordered(""))
    lines.append(separator())
    
    # Order Info
    lines.append(bordered(""))
    lines.append(bordered(f"Order Number:  {pl['order_number']}"))
    lines.append(bordered(f"Generated:     {pl['timestamp']}"))
    lines.append(bordered(f"Order Type:    {pl['type']}"))
    
    if pl['type'] == 'BUNDLE':
        lines.append(bordered(""))
        # Truncate long bundle names
        bundle_name = pl['bundle_name'][:40] + "..." if len(pl['bundle_name']) > 40 else pl['bundle_name']
        lines.append(bordered(f"Bundle:        {pl['bundle_sku']} - {bundle_name}"))
        lines.append(bordered(f"Category:      {pl['bundle_type']}"))
        lines.append(bordered(f"Total Kits:    {pl['total_kits']}"))
    else:
        lines.append(bordered(""))
        tests_str = ', '.join(pl['tests'])
        if len(tests_str) > 55:
            tests_str = tests_str[:52] + "..."
        lines.append(bordered(f"Tests:         {tests_str}"))
        lines.append(bordered(f"Bottles:       {pl['bottles']}"))
        lines.append(bordered(f"Packages:      {pl['packages']}"))
        if pl['sharing']:
            lines.append(bordered("Sharing:       Yes (Gen Chem + Anions)"))
        lines.append(bordered(f"Assembly Time: {pl['assembly_time']} minutes"))
    
    pfas_status = "YES ⚠" if pl['has_pfas'] else "No"
    lines.append(bordered(f"PFAS:          {pfas_status}"))
    lines.append(bordered(""))
    
    # Pick List Section
    lines.append(separator())
    lines.append(bordered(""))
    lines.append(bordered("PICK LIST ITEMS"))
    lines.append(bordered(""))
    
    # Table header
    hdr = f"{'':2}{'Part Number':<20}  {'Description':<40}  {'Qty':>5}"
    lines.append(bordered(hdr))
    lines.append(bordered("─" * IW))
    
    # Items
    for item in pl['items']:
        desc = item['desc'][:38] + ".." if len(item['desc']) > 40 else item['desc']
        row = f"☐ {item['part']:<20}  {desc:<40}  {item['qty']:>5}"
        lines.append(bordered(row))
    
    lines.append(bordered("─" * IW))
    lines.append(bordered(""))
    
    # Instructions
    lines.append(bordered("INSTRUCTIONS:"))
    if pl['type'] == 'BUNDLE':
        lines.append(bordered("  • Pre-packed bundle - no individual picking required"))
        if pl['has_pfas']:
            lines.append(bordered("  • ⚠ PFAS kit included - use PFAS-free gloves"))
    else:
        lines.append(bordered("  • Assemble all components as listed above"))
        if pl['packages'] > 1:
            lines.append(bordered(f"  • Split into {pl['packages']} packages (max 2 bottles/box)"))
        if pl['has_pfas']:
            lines.append(bordered("  • ⚠ PFAS order - PFAS-free gloves & packaging only"))
        if pl.get('sharing'):
            lines.append(bordered("  • Gen Chem & Anions share bottle 1300-00007"))
    
    lines.append(bordered(""))
    
    # Verification
    lines.append(separator())
    lines.append(bordered(""))
    lines.append(bordered("VERIFICATION"))
    lines.append(bordered(""))
    lines.append(bordered("Assembled By: _____________________________   Date: ________________"))
    lines.append(bordered(""))
    lines.append(bordered("Verified By:  _____________________________   Date: ________________"))
    lines.append(bordered(""))
    lines.append("└" + "─" * (W - 2) + "┘")
    
    return "\n".join(lines)


def generate_pdf(pl: Dict) -> Optional[bytes]:
    """Generate professional PDF pick list using fpdf2"""
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
    except ImportError:
        return None
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Header
    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, 'KELP LABORATORY SERVICES', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, 'Kit Assembly Pick List', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(5)
    
    # Header line
    pdf.set_draw_color(0, 51, 102)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    
    # Order Info Box
    pdf.set_fill_color(245, 248, 250)
    pdf.set_draw_color(0, 51, 102)
    box_height = 48 if pl['type'] == 'BUNDLE' else 55
    pdf.rect(10, pdf.get_y(), 190, box_height, style='DF')
    
    y_start = pdf.get_y() + 6
    pdf.set_xy(15, y_start)
    
    # Row 1
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(35, 7, 'Order Number:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(55, 7, pl['order_number'], new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(25, 7, 'Generated:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, pl['timestamp'], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Row 2
    pdf.set_x(15)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(35, 7, 'Order Type:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(55, 7, pl['type'], new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(25, 7, 'PFAS:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 10)
    pfas_text = 'YES - Special Handling' if pl['has_pfas'] else 'No'
    pdf.cell(0, 7, pfas_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    if pl['type'] == 'BUNDLE':
        # Row 3 - Bundle info
        pdf.set_x(15)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(35, 7, 'Bundle:', new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 10)
        bundle_text = f"{pl['bundle_sku']} - {pl['bundle_name']}"
        if len(bundle_text) > 70:
            bundle_text = bundle_text[:67] + '...'
        pdf.cell(0, 7, bundle_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Row 4
        pdf.set_x(15)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(35, 7, 'Category:', new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(55, 7, pl['bundle_type'], new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(25, 7, 'Total Kits:', new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 7, str(pl['total_kits']), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        # Row 3 - Tests
        pdf.set_x(15)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(35, 7, 'Tests:', new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 10)
        tests_str = ', '.join(pl['tests'])
        if len(tests_str) > 75:
            tests_str = tests_str[:72] + '...'
        pdf.cell(0, 7, tests_str, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Row 4
        pdf.set_x(15)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(35, 7, 'Bottles:', new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(55, 7, str(pl['bottles']), new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(25, 7, 'Packages:', new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 7, str(pl['packages']), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Row 5
        pdf.set_x(15)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(35, 7, 'Assembly:', new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 7, f"{pl['assembly_time']} minutes", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(box_height - (pdf.get_y() - y_start) + 8)
    
    # Pick List Section
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, 'PICK LIST ITEMS', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    
    # Table Header
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(12, 10, '', fill=True, border=1)
    pdf.cell(48, 10, 'Part Number', fill=True, border=1)
    pdf.cell(112, 10, 'Description', fill=True, border=1)
    pdf.cell(18, 10, 'Qty', fill=True, border=1, align='C')
    pdf.ln()
    
    # Table Rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 10)
    
    row_fill = False
    for item in pl['items']:
        if row_fill:
            pdf.set_fill_color(248, 248, 248)
        else:
            pdf.set_fill_color(255, 255, 255)
        
        desc = item['desc']
        if len(desc) > 55:
            desc = desc[:52] + '...'
        
        pdf.cell(12, 10, '[ ]', fill=True, border=1, align='C')
        pdf.cell(48, 10, item['part'], fill=True, border=1)
        pdf.cell(112, 10, desc, fill=True, border=1)
        pdf.cell(18, 10, str(item['qty']), fill=True, border=1, align='C')
        pdf.ln()
        row_fill = not row_fill
    
    pdf.ln(8)
    
    # Instructions
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, 'SPECIAL INSTRUCTIONS', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    if pl['type'] == 'BUNDLE':
        pdf.cell(0, 6, '  * Pre-packed bundle - no individual component picking required', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if pl['has_pfas']:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(180, 0, 0)
            pdf.cell(0, 6, '  * WARNING: PFAS kit included - Handle with PFAS-free gloves', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.cell(0, 6, '  * Assemble all components as listed above', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if pl['packages'] > 1:
            pdf.cell(0, 6, f"  * Split into {pl['packages']} packages (max 2 bottles per box)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if pl['has_pfas']:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(180, 0, 0)
            pdf.cell(0, 6, '  * WARNING: PFAS order - Use PFAS-free gloves and packaging ONLY', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if pl.get('sharing'):
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 6, '  * Bottle sharing: Gen Chem & Anions share bottle 1300-00007', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(12)
    
    # Verification Section
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, 'VERIFICATION', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    pdf.cell(28, 8, 'Assembled By:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(75, 8, '_' * 45, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(12, 8, 'Date:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(0, 8, '_' * 28, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)
    
    pdf.cell(28, 8, 'Verified By:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(75, 8, '_' * 45, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(12, 8, 'Date:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(0, 8, '_' * 28, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Footer
    pdf.ln(15)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, 'KELP Laboratory Services | Sunnyvale, CA | Generated by Kit Builder Pro v8.0', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    return bytes(pdf.output())


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
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 11px;
        line-height: 1.5;
        white-space: pre;
        overflow-x: auto;
        overflow-y: auto;
        max-height: 600px;
        min-width: 100%;
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
            st.error("PDF generation failed. Check requirements.txt includes 'fpdf2'")
    
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
