"""
KELP Smart Kit Builder Pro v7.0
===============================
Intelligent Water Testing Kit Configuration System

Features:
- 10 Pre-configured Bundles with Pre-Packed Kit SKUs
- Custom Order Selection with Component-Level Pick Lists
- Professional PDF Pick List Generation
- FedEx Shipping Integration

Author: KELP Laboratory Services
Version: 7.0
Date: February 2026
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import math
from io import BytesIO

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="KELP Kit Builder Pro",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# FEDEX API CLASS
# =============================================================================

class FedExAPI:
    """FedEx API Integration with Demo Mode Support"""
    
    def __init__(self):
        try:
            self.api_key = st.secrets.get("FEDEX_API_KEY", "")
            self.secret_key = st.secrets.get("FEDEX_SECRET_KEY", "")
            self.account_number = st.secrets.get("FEDEX_ACCOUNT_NUMBER", "")
        except Exception:
            self.api_key = ""
            self.secret_key = ""
            self.account_number = ""
        
        self.demo_mode = not all([self.api_key, self.secret_key, self.account_number])
        
        try:
            self.origin = {
                "streetLines": [st.secrets.get("LAB_STREET", "123 Innovation Way")],
                "city": st.secrets.get("LAB_CITY", "Sunnyvale"),
                "stateOrProvinceCode": st.secrets.get("LAB_STATE", "CA"),
                "postalCode": st.secrets.get("LAB_ZIP", "94085"),
                "countryCode": "US"
            }
        except Exception:
            self.origin = {
                "streetLines": ["123 Innovation Way"],
                "city": "Sunnyvale",
                "stateOrProvinceCode": "CA",
                "postalCode": "94085",
                "countryCode": "US"
            }
        
        if self.demo_mode:
            st.sidebar.info("ℹ️ **FedEx Demo Mode** - Using estimated rates")
    
    def calculate_shipping_rate(
        self, 
        destination: Dict, 
        weight_lbs: float, 
        service_type: str = "FEDEX_GROUND",
        is_compliance: bool = False
    ) -> Optional[Dict]:
        if self.demo_mode:
            base_rate = 50.0 if service_type == "FEDEX_2_DAY" else 12.0
            if weight_lbs > 5:
                base_rate += (weight_lbs - 5) * 2
            return {
                'total_charge': round(base_rate, 2),
                'service_name': 'FedEx 2Day' if service_type == "FEDEX_2_DAY" else 'FedEx Ground',
                'transit_time': '2 business days' if service_type == "FEDEX_2_DAY" else '3-5 business days',
                'delivery_date': datetime.now().strftime('%Y-%m-%d'),
                'demo_mode': True
            }
        return None
    
    def generate_label(
        self, 
        destination: Dict, 
        weight_lbs: float, 
        service_type: str = "FEDEX_GROUND",
        package_number: int = 1, 
        total_packages: int = 1
    ) -> Optional[Dict]:
        if self.demo_mode:
            import random
            tracking = ''.join([str(random.randint(0, 9)) for _ in range(12)])
            return {
                'tracking_number': tracking,
                'package_number': package_number,
                'total_packages': total_packages,
                'demo_mode': True
            }
        return None


# =============================================================================
# PRE-PACKED KIT SKUs
# =============================================================================

PREPACKED_KITS = {
    '1300-00001_REV01': {
        'name': 'KIT KELP (Metals + Anion + Gen Chem)',
        'description': 'Standard water testing kit - pre-packed',
        'weight_lbs': 2.5
    },
    '1300-00003_REV01': {
        'name': 'KIT KELP (PFAS)',
        'description': 'PFAS testing kit - pre-packed',
        'weight_lbs': 1.5
    }
}


# =============================================================================
# BUNDLE DEFINITIONS - EXACT MAPPING FROM SPREADSHEET
# =============================================================================

BUNDLE_CATALOG = {
    # Commercial Bundles
    'COM-001': {
        'name': 'Food & Beverage Water Quality Package',
        'type': 'Commercial',
        'description': 'Process water quality testing for F&B operations',
        'price': 325.00,
        'kits': {
            '1300-00001_REV01': 1
        }
    },
    'COM-002': {
        'name': 'Agricultural Irrigation Package',
        'type': 'Commercial',
        'description': 'Irrigation water quality assessment',
        'price': 295.00,
        'kits': {
            '1300-00001_REV01': 1
        }
    },
    
    # Real Estate Bundles
    'RE-001': {
        'name': 'Real Estate Well Water Package',
        'type': 'Real Estate',
        'description': 'Well water testing for property transactions',
        'price': 399.00,
        'kits': {
            '1300-00001_REV01': 1
        }
    },
    'RE-002': {
        'name': 'Conventional Loan Testing Package',
        'type': 'Real Estate',
        'description': 'Standard loan requirement testing',
        'price': 275.00,
        'kits': {
            '1300-00001_REV01': 1
        }
    },
    
    # Residential Bundles (Non-PFAS)
    'RES-001': {
        'name': 'Essential Home Water Test Package',
        'type': 'Residential',
        'description': 'Basic water quality for homeowners',
        'price': 249.00,
        'kits': {
            '1300-00001_REV01': 1
        }
    },
    'RES-002': {
        'name': 'Complete Homeowner Package',
        'type': 'Residential',
        'description': 'Comprehensive water quality with nutrients',
        'price': 349.00,
        'kits': {
            '1300-00001_REV01': 1
        }
    },
    
    # Residential Bundles (With PFAS)
    'RES-003': {
        'name': 'PFAS Home Safety Package',
        'type': 'Residential + PFAS',
        'description': 'Standard testing plus PFAS screening',
        'price': 475.00,
        'kits': {
            '1300-00001_REV01': 1,
            '1300-00003_REV01': 1
        }
    },
    'RES-004': {
        'name': 'Basic PFAS Screen',
        'type': 'Residential + PFAS',
        'description': 'PFAS testing with essential metals and anions',
        'price': 495.00,
        'kits': {
            '1300-00001_REV01': 1,
            '1300-00003_REV01': 1
        }
    },
    'RES-005': {
        'name': 'Comprehensive Home Safety Screen',
        'type': 'Residential + PFAS',
        'description': 'Full panel including PFAS',
        'price': 595.00,
        'kits': {
            '1300-00001_REV01': 1,
            '1300-00003_REV01': 1
        }
    },
    'RES-006': {
        'name': 'Ultimate Water Safety Suite',
        'type': 'Residential + PFAS',
        'description': 'Complete testing - all parameters including PFAS',
        'price': 795.00,
        'kits': {
            '1300-00001_REV01': 1,
            '1300-00003_REV01': 1
        }
    }
}


# =============================================================================
# COMPONENT LIBRARY (For Custom Orders Only)
# =============================================================================

COMPONENTS = {
    "1300-00007": {"type": "Bottle", "desc": "Bottle: Anions + Gen Chem (unpreserved)"},
    "1300-00008": {"type": "Bottle", "desc": "Bottle: Metals (HNO₃ preserved)"},
    "1300-00009": {"type": "Bottle", "desc": "Bottle: Nutrients (H₂SO₄ preserved)"},
    "1300-00010": {"type": "Bottle", "desc": "Bottle: PFAS (PFAS-certified)"},
    "1300-00058": {"type": "Box", "desc": "Shipping Box"},
    "1300-00018": {"type": "Gloves", "desc": "Gloves - Nitrile"},
    "1300-00019": {"type": "Gloves", "desc": "Gloves - PFAS-free"},
    "1300-00027": {"type": "Packaging", "desc": "Bottle Protection - Generic"},
    "1300-00028": {"type": "Packaging", "desc": "Bottle Protection - PFAS"},
    "1300-00029": {"type": "Document", "desc": "Collection Instructions"},
    "1300-00030": {"type": "Document", "desc": "Chain of Custody Form"},
}

# Test Parameters for Custom Orders
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
        'bottle': '1300-00007',  # Shares with General Chemistry
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
        'tests': ['Nitrate/Nitrite (EPA 353.2)', 'Phosphate']
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
ASSEMBLY_TIME_PER_PKG = 7


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_fedex_service(is_compliance: bool) -> str:
    return "FEDEX_2_DAY" if is_compliance else "FEDEX_GROUND"


def bundle_has_pfas(bundle_sku: str) -> bool:
    """Check if bundle includes PFAS kit"""
    if bundle_sku not in BUNDLE_CATALOG:
        return False
    return '1300-00003_REV01' in BUNDLE_CATALOG[bundle_sku]['kits']


def get_bundle_total_kits(bundle_sku: str) -> int:
    """Get total number of kits in a bundle"""
    if bundle_sku not in BUNDLE_CATALOG:
        return 0
    return sum(BUNDLE_CATALOG[bundle_sku]['kits'].values())


def get_bundle_weight(bundle_sku: str) -> float:
    """Calculate total weight for a bundle"""
    if bundle_sku not in BUNDLE_CATALOG:
        return 0.0
    total = 0.0
    for kit_sku, qty in BUNDLE_CATALOG[bundle_sku]['kits'].items():
        if kit_sku in PREPACKED_KITS:
            total += PREPACKED_KITS[kit_sku]['weight_lbs'] * qty
    return total


def calculate_custom_order(selected_tests: List[str]) -> Dict:
    """Calculate details for a custom order"""
    sharing_active = 'general_chemistry' in selected_tests and 'anions' in selected_tests
    has_pfas = 'pfas' in selected_tests
    
    # Count bottles
    bottles = 0
    for test in selected_tests:
        if test == 'general_chemistry':
            bottles += 1
        elif test == 'metals':
            bottles += 1
        elif test == 'anions' and not sharing_active:
            bottles += 1
        elif test == 'nutrients':
            bottles += 1
        elif test == 'pfas':
            bottles += 2
    
    # Calculate packages (max 2 bottles per package)
    packages = max(1, math.ceil(bottles / 2))
    
    # Calculate weight
    weight = BASE_KIT_WEIGHT * packages
    for test in selected_tests:
        if test in TEST_PARAMETERS:
            weight += TEST_PARAMETERS[test]['weight']
    
    # Calculate cost
    cost = BASE_KIT_COST * packages
    for test in selected_tests:
        if test in TEST_PARAMETERS:
            if test == 'anions' and sharing_active:
                cost += TEST_PARAMETERS[test].get('cost_when_shared', 0)
            else:
                cost += TEST_PARAMETERS[test]['cost']
    
    return {
        'bottles': bottles,
        'packages': packages,
        'weight': round(weight, 2),
        'cost': round(cost, 2),
        'sharing_active': sharing_active,
        'has_pfas': has_pfas
    }


def estimate_shipping(is_compliance: bool, packages: int) -> float:
    per_pkg = 50.0 if is_compliance else 12.0
    return per_pkg * packages


def calc_total_shipping(
    api: FedExAPI, 
    dest: Dict, 
    weight_per_pkg: float, 
    packages: int,
    service: str, 
    compliance: bool
) -> Optional[Dict]:
    total = 0
    last = None
    for _ in range(packages):
        rate = api.calculate_shipping_rate(dest, weight_per_pkg, service, compliance)
        if rate:
            total += rate['total_charge']
            last = rate
        else:
            return None
    if last:
        return {
            'total_charge': round(total, 2),
            'service_name': last['service_name'],
            'transit_time': last.get('transit_time', 'N/A'),
            'packages': packages,
            'per_package': round(total / packages, 2),
            'demo_mode': last.get('demo_mode', False)
        }
    return None


# =============================================================================
# PICK LIST GENERATION
# =============================================================================

def create_bundle_pick_list(bundle_sku: str) -> Dict:
    """Create pick list for a pre-packed bundle order"""
    bundle = BUNDLE_CATALOG[bundle_sku]
    
    items = []
    for kit_sku, qty in bundle['kits'].items():
        kit_info = PREPACKED_KITS[kit_sku]
        items.append({
            'part_number': kit_sku,
            'description': kit_info['name'],
            'quantity': qty
        })
    
    total_kits = sum(bundle['kits'].values())
    has_pfas = '1300-00003_REV01' in bundle['kits']
    
    notes = [
        f"📦 PRE-PACKED BUNDLE ORDER: {bundle_sku}",
        "All components are pre-assembled - no individual picking required"
    ]
    if has_pfas:
        notes.append("⚠️ PFAS KIT INCLUDED - Handle with PFAS-free gloves")
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'order_type': 'BUNDLE',
        'bundle_sku': bundle_sku,
        'bundle_name': bundle['name'],
        'bundle_type': bundle['type'],
        'total_kits': total_kits,
        'has_pfas': has_pfas,
        'items': items,
        'notes': notes
    }


def create_custom_pick_list(selected_tests: List[str], order_info: Dict) -> Dict:
    """Create pick list for a custom order with individual components"""
    bottles = order_info['bottles']
    packages = order_info['packages']
    sharing = order_info['sharing_active']
    has_pfas = order_info['has_pfas']
    
    items = []
    
    # Shipping boxes
    items.append({'part_number': '1300-00058', 'description': 'Shipping Box', 'quantity': packages})
    
    # Bottles
    if 'general_chemistry' in selected_tests or 'anions' in selected_tests:
        note = " (shared Gen Chem + Anions)" if sharing else ""
        items.append({
            'part_number': '1300-00007', 
            'description': f'Bottle: Anions + Gen Chem{note}', 
            'quantity': 1
        })
    
    if 'metals' in selected_tests:
        items.append({'part_number': '1300-00008', 'description': 'Bottle: Metals (HNO₃)', 'quantity': 1})
    
    if 'nutrients' in selected_tests:
        items.append({'part_number': '1300-00009', 'description': 'Bottle: Nutrients (H₂SO₄)', 'quantity': 1})
    
    if 'pfas' in selected_tests:
        items.append({'part_number': '1300-00010', 'description': 'Bottle: PFAS', 'quantity': 2})
    
    # Gloves
    if has_pfas:
        items.append({'part_number': '1300-00019', 'description': 'Gloves - PFAS-free', 'quantity': packages * 2})
    else:
        items.append({'part_number': '1300-00018', 'description': 'Gloves - Nitrile', 'quantity': packages * 2})
    
    # Packaging
    non_pfas_bottles = bottles - (2 if has_pfas else 0)
    if non_pfas_bottles > 0:
        items.append({'part_number': '1300-00027', 'description': 'Bottle Protection - Generic', 'quantity': non_pfas_bottles})
    if has_pfas:
        items.append({'part_number': '1300-00028', 'description': 'Bottle Protection - PFAS', 'quantity': 2})
    
    # Documents
    items.append({'part_number': '1300-00029', 'description': 'Collection Instructions', 'quantity': packages})
    items.append({'part_number': '1300-00030', 'description': 'Chain of Custody Form', 'quantity': 1})
    
    # Notes
    notes = ["🔧 CUSTOM ORDER - Individual component picking required"]
    if packages > 1:
        notes.append(f"⚠️ MULTIPLE PACKAGES: {packages} boxes required (max 2 bottles per box)")
    if has_pfas:
        notes.append("⚠️ PFAS ORDER: Use PFAS-free gloves and PFAS packaging only")
    if sharing:
        notes.append("✅ BOTTLE SHARING: General Chemistry & Anions share bottle 1300-00007")
    
    test_names = [TEST_PARAMETERS[t]['name'] for t in selected_tests]
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'order_type': 'CUSTOM',
        'tests_selected': test_names,
        'total_bottles': bottles,
        'total_packages': packages,
        'sharing_active': sharing,
        'has_pfas': has_pfas,
        'assembly_time': ASSEMBLY_TIME_PER_PKG * packages,
        'items': items,
        'notes': notes
    }


def format_pick_list_text(pick_list: Dict) -> str:
    """Format pick list as printable text"""
    lines = []
    lines.append("=" * 65)
    lines.append("              KELP LABORATORY SERVICES")
    lines.append("              KIT ASSEMBLY PICK LIST")
    lines.append("=" * 65)
    lines.append(f"Generated: {pick_list['timestamp']}")
    lines.append(f"Order Type: {pick_list['order_type']}")
    lines.append("")
    
    if pick_list['order_type'] == 'BUNDLE':
        lines.append(f"Bundle SKU: {pick_list['bundle_sku']}")
        lines.append(f"Bundle Name: {pick_list['bundle_name']}")
        lines.append(f"Bundle Type: {pick_list['bundle_type']}")
        lines.append(f"Total Kits: {pick_list['total_kits']}")
    else:
        lines.append(f"Tests: {', '.join(pick_list['tests_selected'])}")
        lines.append(f"Total Bottles: {pick_list['total_bottles']}")
        lines.append(f"Total Packages: {pick_list['total_packages']}")
        lines.append(f"Est. Assembly Time: {pick_list['assembly_time']} minutes")
    
    lines.append(f"PFAS Included: {'YES ⚠️' if pick_list['has_pfas'] else 'No'}")
    lines.append("")
    
    lines.append("-" * 65)
    lines.append("NOTES:")
    for note in pick_list['notes']:
        lines.append(f"  {note}")
    lines.append("")
    
    lines.append("-" * 65)
    lines.append("PICK LIST ITEMS:")
    lines.append(f"{'Part Number':<22} {'Description':<32} {'Qty':>6}")
    lines.append("-" * 65)
    
    for item in pick_list['items']:
        lines.append(f"☐ {item['part_number']:<20} {item['description']:<32} {item['quantity']:>6}")
    
    lines.append("")
    lines.append("=" * 65)
    lines.append("")
    lines.append("Assembled By: ___________________________ Date: ______________")
    lines.append("")
    lines.append("Verified By:  ___________________________ Date: ______________")
    lines.append("")
    lines.append("=" * 65)
    
    return "\n".join(lines)


def generate_pdf(pick_list: Dict, order_id: str = None, customer: str = None) -> Optional[bytes]:
    """Generate PDF pick list"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        return None
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, 
                                  spaceAfter=6, alignment=TA_CENTER, textColor=colors.HexColor('#0066B2'))
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=11, 
                                     spaceAfter=6, alignment=TA_CENTER)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=12,
                                    spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#0066B2'))
    
    elements = []
    
    # Header
    elements.append(Paragraph("KELP LABORATORY SERVICES", title_style))
    elements.append(Paragraph("Kit Assembly Pick List", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Order info
    info = [f"Generated: {pick_list['timestamp']}"]
    if order_id:
        info.append(f"Order: {order_id}")
    if customer:
        info.append(f"Customer: {customer}")
    elements.append(Paragraph(" | ".join(info), subtitle_style))
    
    order_label = f"<b>{pick_list['order_type']}</b>"
    if pick_list['order_type'] == 'BUNDLE':
        order_label += f" - {pick_list['bundle_sku']} - {pick_list['bundle_name']}"
    elements.append(Paragraph(order_label, subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary
    elements.append(Paragraph("Order Summary", section_style))
    
    if pick_list['order_type'] == 'BUNDLE':
        summary = [
            ['Bundle SKU:', pick_list['bundle_sku']],
            ['Bundle Name:', pick_list['bundle_name']],
            ['Bundle Type:', pick_list['bundle_type']],
            ['Total Kits:', str(pick_list['total_kits'])],
            ['PFAS Included:', 'YES ⚠️' if pick_list['has_pfas'] else 'No'],
        ]
    else:
        summary = [
            ['Tests:', ', '.join(pick_list['tests_selected'])],
            ['Total Bottles:', str(pick_list['total_bottles'])],
            ['Total Packages:', str(pick_list['total_packages'])],
            ['Bottle Sharing:', 'Yes' if pick_list['sharing_active'] else 'No'],
            ['PFAS Included:', 'YES ⚠️' if pick_list['has_pfas'] else 'No'],
            ['Est. Assembly:', f"{pick_list['assembly_time']} minutes"],
        ]
    
    summary_tbl = Table(summary, colWidths=[1.5*inch, 4*inch])
    summary_tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_tbl)
    elements.append(Spacer(1, 0.2*inch))
    
    # Pick list
    elements.append(Paragraph("Pick List Items", section_style))
    
    tbl_data = [['☐', 'Part Number', 'Description', 'Qty']]
    for item in pick_list['items']:
        tbl_data.append(['☐', item['part_number'], item['description'], str(item['quantity'])])
    
    pick_tbl = Table(tbl_data, colWidths=[0.4*inch, 1.6*inch, 3.0*inch, 0.5*inch])
    pick_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066B2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    elements.append(pick_tbl)
    elements.append(Spacer(1, 0.2*inch))
    
    # Notes
    if pick_list['notes']:
        elements.append(Paragraph("Special Instructions", section_style))
        for note in pick_list['notes']:
            elements.append(Paragraph(f"• {note}", styles['Normal']))
        elements.append(Spacer(1, 0.1*inch))
    
    # Signatures
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("─" * 70, styles['Normal']))
    sig_data = [
        ['Assembled By:', '________________________', 'Date:', '____________'],
        ['Verified By:', '________________________', 'Date:', '____________'],
    ]
    sig_tbl = Table(sig_data, colWidths=[1*inch, 2.2*inch, 0.5*inch, 1.5*inch])
    sig_tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(sig_tbl)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# CSS STYLES
# =============================================================================

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    
    .pick-list-box {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        white-space: pre-wrap;
        max-height: 500px;
        overflow-y: auto;
    }
    
    .price-box {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #0066B2 0%, #3399CC 100%);
        border-radius: 8px;
        color: white;
        margin: 1rem 0;
    }
    
    .price-box .label { font-size: 0.9rem; opacity: 0.9; }
    .price-box .amount { font-size: 2.5rem; font-weight: bold; }
    
    .shipping-box {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #0066B2;
        margin: 1rem 0;
    }
    
    .rate-box {
        font-size: 1.5rem;
        font-weight: bold;
        color: #00A86B;
        padding: 1rem;
        background: #f0f8f5;
        border-radius: 4px;
        text-align: center;
        margin-top: 1rem;
    }
    
    .pfas-alert {
        background: #FFF3CD;
        border-left: 4px solid #FFA500;
        padding: 0.75rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

defaults = {
    'order_mode': 'bundle',
    'selected_bundle': None,
    'selected_tests': {},
    'shipping_address': None,
    'shipping_rate': None,
    'pick_list': None,
    'order_history': [],
    'fedex': None
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

if st.session_state.fedex is None:
    st.session_state.fedex = FedExAPI()


# =============================================================================
# HEADER
# =============================================================================

st.title("🧪 KELP Smart Kit Builder Pro")
st.markdown("**Water Testing Kit Configuration System** | *Pre-Packed Bundles & Custom Orders*")
st.divider()


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.header("📍 Shipping")
    
    if st.button("🔄 Reset All", key="reset"):
        for key in ['selected_bundle', 'selected_tests', 'shipping_address', 'shipping_rate', 'pick_list']:
            st.session_state[key] = defaults[key] if key in defaults else None
        st.session_state.order_mode = 'bundle'
        st.rerun()
    
    st.divider()
    
    contact = st.text_input("Contact Name", key="contact")
    street = st.text_input("Street", key="street")
    street2 = st.text_input("Street 2", key="street2")
    
    c1, c2 = st.columns(2)
    city = c1.text_input("City", key="city")
    state = c2.text_input("State", max_chars=2, key="state")
    
    c3, c4 = st.columns(2)
    zipcode = c3.text_input("ZIP", key="zip")
    phone = c4.text_input("Phone", key="phone")
    
    if st.button("💾 Save Address", type="primary", key="save_addr"):
        if city and state and zipcode:
            st.session_state.shipping_address = {
                'contact_name': contact,
                'streetLines': [s for s in [street, street2] if s],
                'city': city,
                'stateOrProvinceCode': state.upper(),
                'postalCode': zipcode,
                'countryCode': 'US',
                'phone': phone
            }
            st.success("✅ Saved!")
            st.rerun()
        else:
            st.error("City, State, ZIP required")
    
    if st.session_state.shipping_address:
        addr = st.session_state.shipping_address
        st.caption(f"📍 {addr['city']}, {addr['stateOrProvinceCode']} {addr['postalCode']}")


# =============================================================================
# STEP 1: ORDER TYPE
# =============================================================================

st.header("1️⃣ Select Order Type")

order_mode = st.radio(
    "Order Type:",
    ['bundle', 'custom'],
    format_func=lambda x: "📦 Pre-Packed Bundle" if x == 'bundle' else "🔧 Custom Order",
    horizontal=True,
    key="order_mode_radio"
)
st.session_state.order_mode = order_mode

st.divider()


# =============================================================================
# BUNDLE SELECTION
# =============================================================================

if st.session_state.order_mode == 'bundle':
    st.subheader("📦 Select Bundle")
    st.caption("Pick list will show pre-packed kit SKU(s) only")
    
    # Group by type
    groups = {}
    for sku, data in BUNDLE_CATALOG.items():
        t = data['type']
        if t not in groups:
            groups[t] = []
        groups[t].append((sku, data))
    
    for group_name, bundles in groups.items():
        st.markdown(f"**{group_name}**")
        cols = st.columns(min(len(bundles), 3))
        
        for i, (sku, data) in enumerate(bundles):
            with cols[i % 3]:
                selected = st.session_state.selected_bundle == sku
                has_pfas = '1300-00003_REV01' in data['kits']
                total_kits = sum(data['kits'].values())
                
                label = f"{'✅ ' if selected else ''}{sku}\n{data['name']}\n{total_kits} kit{'s' if total_kits > 1 else ''} | ${data['price']:.0f}"
                
                if st.button(label, key=f"b_{sku}", type="primary" if selected else "secondary"):
                    st.session_state.selected_bundle = sku
                    st.session_state.shipping_rate = None
                    st.session_state.pick_list = None
                    st.rerun()
                
                if has_pfas:
                    st.caption("⚠️ Includes PFAS")
        st.markdown("")
    
    # Show selection
    if st.session_state.selected_bundle:
        b = BUNDLE_CATALOG[st.session_state.selected_bundle]
        st.success(f"**Selected: {st.session_state.selected_bundle}** - {b['name']}")
        
        st.markdown("**Kits to Pick:**")
        for kit_sku, qty in b['kits'].items():
            st.markdown(f"- `{kit_sku}` - {PREPACKED_KITS[kit_sku]['name']} × **{qty}**")
    
    st.session_state.selected_tests = {}


# =============================================================================
# CUSTOM ORDER
# =============================================================================

else:
    st.subheader("🔧 Custom Order")
    st.caption("Pick list will show individual components")
    
    for test_key, test_data in TEST_PARAMETERS.items():
        checked = st.session_state.selected_tests.get(test_key, False)
        
        # Check for sharing
        sharing = (test_key == 'anions' and 
                   st.session_state.selected_tests.get('general_chemistry', False))
        
        label = test_data['name']
        if test_key == 'pfas':
            label += " ⚠️"
        if sharing:
            label += " 🎁 FREE (shares bottle)"
        
        with st.expander(f"{'✅ ' if checked else ''}{label}", expanded=sharing):
            new_val = st.checkbox(f"Select {test_data['name']}", value=checked, key=f"t_{test_key}")
            st.session_state.selected_tests[test_key] = new_val
            
            if sharing and new_val:
                st.success("✅ Shares bottle with General Chemistry - FREE!")
            if test_key == 'pfas' and new_val:
                st.warning("⚠️ PFAS requires special handling")
            
            st.markdown(f"**Bottle:** {test_data['bottle']} | **Tests:** {', '.join(test_data['tests'])}")
            
            if sharing:
                st.markdown("**Cost:** $0.00 (FREE)")
            else:
                st.markdown(f"**Cost:** ${test_data['cost']:.2f}")
    
    st.session_state.selected_bundle = None

st.divider()


# =============================================================================
# SHIPPING OPTIONS
# =============================================================================

st.subheader("📦 Shipping")

compliance = st.checkbox("**Compliance Shipping** (FedEx 2-Day)", key="compliance")

st.divider()


# =============================================================================
# CALCULATE ORDER
# =============================================================================

has_order = False
total_kits = 0
packages = 0
weight = 0.0
base_price = 0.0
has_pfas = False

if st.session_state.order_mode == 'bundle' and st.session_state.selected_bundle:
    has_order = True
    b = BUNDLE_CATALOG[st.session_state.selected_bundle]
    total_kits = sum(b['kits'].values())
    packages = total_kits
    weight = get_bundle_weight(st.session_state.selected_bundle)
    base_price = b['price']
    has_pfas = bundle_has_pfas(st.session_state.selected_bundle)

elif st.session_state.order_mode == 'custom':
    selected = [k for k, v in st.session_state.selected_tests.items() if v]
    if selected:
        has_order = True
        info = calculate_custom_order(selected)
        total_kits = info['bottles']
        packages = info['packages']
        weight = info['weight']
        base_price = info['cost']
        has_pfas = info['has_pfas']


# =============================================================================
# STEP 2: SHIPPING
# =============================================================================

st.header("2️⃣ Calculate Shipping")

if has_order:
    c1, c2, c3 = st.columns(3)
    c1.metric("Items" if st.session_state.order_mode == 'bundle' else "Bottles", total_kits)
    c2.metric("Packages", packages)
    c3.metric("Weight", f"{weight:.1f} lbs")
    
    ship_weight = weight + (5.0 * packages if compliance else 0)
    
    if st.session_state.shipping_address:
        if st.button(f"🔄 Get FedEx Rate", type="primary", key="get_rate"):
            with st.spinner("Calculating..."):
                rate = calc_total_shipping(
                    st.session_state.fedex,
                    st.session_state.shipping_address,
                    ship_weight / packages,
                    packages,
                    get_fedex_service(compliance),
                    compliance
                )
                if rate:
                    st.session_state.shipping_rate = rate
                    st.success("✅ Done!")
                    st.rerun()
        
        if st.session_state.shipping_rate:
            r = st.session_state.shipping_rate
            st.markdown(f"""
            <div class="shipping-box">
                <p><strong>Service:</strong> {r['service_name']} | <strong>Packages:</strong> {r['packages']}</p>
                <div class="rate-box">Shipping: ${r['total_charge']:.2f}</div>
                {'<p style="text-align:center;color:#999;">Demo Mode</p>' if r.get('demo_mode') else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("💡 Enter address in sidebar")
        est = estimate_shipping(compliance, packages)
        st.caption(f"Estimated: ${est:.2f}")
else:
    st.warning("⚠️ Select a bundle or tests first")

st.divider()


# =============================================================================
# STEP 3: SUMMARY
# =============================================================================

st.header("3️⃣ Cost Summary")

if has_order:
    ship_cost = st.session_state.shipping_rate['total_charge'] if st.session_state.shipping_rate else estimate_shipping(compliance, packages)
    total = base_price + ship_cost
    
    label = f"Bundle: {st.session_state.selected_bundle}" if st.session_state.order_mode == 'bundle' else "Custom Order"
    
    st.markdown(f"""
    <div class="price-box">
        <div class="label">{label}</div>
        <div class="amount">${total:.2f}</div>
        <div class="label">includes ${ship_cost:.2f} shipping</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()


# =============================================================================
# STEP 4: PICK LIST
# =============================================================================

st.header("4️⃣ Generate Pick List")

if has_order:
    if st.button("📋 Generate Pick List", type="primary", key="gen_pick"):
        if st.session_state.order_mode == 'bundle':
            st.session_state.pick_list = create_bundle_pick_list(st.session_state.selected_bundle)
        else:
            selected = [k for k, v in st.session_state.selected_tests.items() if v]
            info = calculate_custom_order(selected)
            st.session_state.pick_list = create_custom_pick_list(selected, info)
        st.success("✅ Generated!")
    
    if st.session_state.pick_list:
        pl = st.session_state.pick_list
        text = format_pick_list_text(pl)
        
        st.markdown(f"<div class='pick-list-box'>{text}</div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        
        with c1:
            fname = pl.get('bundle_sku', 'CUSTOM')
            st.download_button(
                "📥 Download TXT",
                data=text,
                file_name=f"KELP_PickList_{fname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="dl_txt"
            )
        
        with c2:
            oid = st.text_input("Order ID:", key="oid")
            cust = st.text_input("Customer:", key="cust")
            
            if st.button("📄 Generate PDF", key="gen_pdf"):
                pdf = generate_pdf(pl, oid, cust)
                if pdf:
                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf,
                        file_name=f"KELP_PickList_{fname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        key="dl_pdf"
                    )
                else:
                    st.error("Install reportlab: `pip install reportlab`")
else:
    st.warning("⚠️ Make a selection first")

st.divider()


# =============================================================================
# STEP 5: COMPLETE
# =============================================================================

st.header("5️⃣ Complete Order")

if has_order and st.session_state.pick_list:
    c1, c2 = st.columns(2)
    
    with c1:
        if st.button("💾 Save & Reset", type="primary", key="save"):
            order = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': st.session_state.order_mode,
                'ref': st.session_state.selected_bundle or 'CUSTOM',
                'packages': packages,
                'total': total if 'total' in dir() else 0
            }
            st.session_state.order_history.append(order)
            
            for key in ['selected_bundle', 'selected_tests', 'shipping_rate', 'pick_list']:
                st.session_state[key] = defaults.get(key, None)
            
            st.success("✅ Saved!")
            st.balloons()
            st.rerun()
    
    with c2:
        if st.button("🔄 Reset", key="just_reset"):
            for key in ['selected_bundle', 'selected_tests', 'shipping_rate', 'pick_list']:
                st.session_state[key] = defaults.get(key, None)
            st.rerun()
else:
    st.info("💡 Generate pick list first")


# =============================================================================
# HISTORY
# =============================================================================

if st.session_state.order_history:
    st.divider()
    st.header("📊 Order History")
    st.dataframe(pd.DataFrame(st.session_state.order_history))


# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.markdown("""
---
**KELP Kit Builder Pro v7.0** | February 2026

**Pre-Packed Kit SKUs:**
| SKU | Description |
|-----|-------------|
| `1300-00001_REV01` | KIT KELP (Metals + Anion + Gen Chem) |
| `1300-00003_REV01` | KIT KELP (PFAS) |

**Bundle → Kit Mapping:**
| Bundle | Standard Kit | PFAS Kit | Total |
|--------|--------------|----------|-------|
| COM-001, COM-002, RE-001, RE-002, RES-001, RES-002 | 1 | - | 1 |
| RES-003, RES-004, RES-005, RES-006 | 1 | 1 | 2 |
---
""")
