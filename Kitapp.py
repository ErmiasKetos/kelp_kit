"""
KELP Smart Kit Builder Pro v6.0
===============================
Intelligent Water Testing Kit Configuration System

Features:
- Pre-configured Bundles with Pre-Packed Kit SKUs
- Custom Module Selection with Component-Level Pick Lists
- Multi-Package Support
- PDF Pick List Generation
- FedEx Integration

Author: KELP Laboratory Services
Version: 6.0
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
        """Initialize FedEx API with credentials from secrets or demo mode"""
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
        """Calculate shipping rate (demo mode returns estimates)"""
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
        """Generate shipping label (demo mode returns sample tracking)"""
        if self.demo_mode:
            import random
            tracking = ''.join([str(random.randint(0, 9)) for _ in range(12)])
            return {
                'tracking_number': tracking,
                'label_url': f"https://demo.fedex.com/label/{tracking}.pdf",
                'package_number': package_number,
                'total_packages': total_packages,
                'demo_mode': True
            }
        return None


# =============================================================================
# PRE-PACKED KIT SKUs
# =============================================================================

PREPACKED_KIT_SKUS = {
    'standard': {
        'sku': '1300-00001_REV01',
        'name': 'KIT KELP (Metals + Anion + Gen Chem)',
        'description': 'Pre-packed kit for standard water testing (non-PFAS)',
        'weight_lbs': 2.5
    },
    'pfas': {
        'sku': '1300-00003_REV01',
        'name': 'KIT KELP (PFAS)',
        'description': 'Pre-packed kit for PFAS testing',
        'weight_lbs': 1.5
    }
}

# =============================================================================
# BUNDLE DEFINITIONS (Pre-Packed Kits)
# =============================================================================

BUNDLE_DEFINITIONS = {
    'COM-001': {
        'name': 'Food & Beverage Water Quality Package',
        'category': 'Commercial',
        'description': 'Process water quality for F&B operations',
        'price': 325.00,
        'kits': [{'type': 'standard', 'qty': 1}],
        'has_pfas': False
    },
    'COM-002': {
        'name': 'Agricultural Irrigation Package',
        'category': 'Commercial',
        'description': 'Irrigation water quality assessment',
        'price': 295.00,
        'kits': [{'type': 'standard', 'qty': 1}],
        'has_pfas': False
    },
    'RE-001': {
        'name': 'Real Estate Well Water Package',
        'category': 'Real Estate',
        'description': 'Well water testing for property transactions',
        'price': 399.00,
        'kits': [{'type': 'standard', 'qty': 1}],
        'has_pfas': False
    },
    'RE-002': {
        'name': 'Conventional Loan Testing Package',
        'category': 'Real Estate',
        'description': 'Standard loan requirement testing',
        'price': 275.00,
        'kits': [{'type': 'standard', 'qty': 1}],
        'has_pfas': False
    },
    'RES-001': {
        'name': 'Essential Home Water Test Package',
        'category': 'Residential',
        'description': 'Basic water quality for homeowners',
        'price': 249.00,
        'kits': [{'type': 'standard', 'qty': 1}],
        'has_pfas': False
    },
    'RES-002': {
        'name': 'Complete Homeowner Package',
        'category': 'Residential',
        'description': 'Comprehensive water quality with nutrients',
        'price': 349.00,
        'kits': [{'type': 'standard', 'qty': 1}],
        'has_pfas': False
    },
    'RES-003': {
        'name': 'PFAS Home Safety Package',
        'category': 'Residential - PFAS',
        'description': 'PFAS testing for home safety',
        'price': 425.00,
        'kits': [{'type': 'standard', 'qty': 1}, {'type': 'pfas', 'qty': 1}],
        'has_pfas': True
    },
    'RES-004': {
        'name': 'Basic PFAS Screen',
        'category': 'Residential - PFAS',
        'description': 'PFAS testing with essential metals and anions',
        'price': 475.00,
        'kits': [{'type': 'standard', 'qty': 1}, {'type': 'pfas', 'qty': 1}],
        'has_pfas': True
    },
    'RES-005': {
        'name': 'Comprehensive Home Safety Screen',
        'category': 'Residential - Premium',
        'description': 'Full panel including PFAS',
        'price': 595.00,
        'kits': [{'type': 'standard', 'qty': 1}, {'type': 'pfas', 'qty': 1}],
        'has_pfas': True
    },
    'RES-006': {
        'name': 'Ultimate Water Safety Suite',
        'category': 'Residential - Premium',
        'description': 'Complete testing - all modules including PFAS',
        'price': 795.00,
        'kits': [{'type': 'standard', 'qty': 1}, {'type': 'pfas', 'qty': 1}],
        'has_pfas': True
    }
}

# =============================================================================
# COMPONENT LIBRARY (For Custom Orders Only)
# =============================================================================

KIT_COMPONENTS = {
    "1300-00007": {"type": "Bottle", "description": "Bottle: Anions + Gen Chem"},
    "1300-00008": {"type": "Bottle", "description": "Bottle: Metals (HNO₃)"},
    "1300-00009": {"type": "Bottle", "description": "Bottle: Nutrients (H₂SO₄)"},
    "1300-00010": {"type": "Bottle", "description": "Bottle: PFAS"},
    "1300-00058": {"type": "Box", "description": "Shipping Box"},
    "1300-00018": {"type": "Gloves", "description": "Gloves (Nitrile)"},
    "1300-00019": {"type": "Gloves", "description": "Gloves (PFAS-free)"},
    "1300-00027": {"type": "Packaging", "description": "Bottle Protection (Generic)"},
    "1300-00028": {"type": "Packaging", "description": "Bottle Protection (PFAS)"},
    "1300-00029": {"type": "Document", "description": "Collection Instructions"},
    "1300-00030": {"type": "Document", "description": "COC Form"},
}

MODULE_LIBRARY = {
    'module_a': {
        'name': 'Module A: General Chemistry',
        'short_name': 'MOD-A',
        'cost': 2.50,
        'weight_lbs': 0.3,
        'bottle': '1300-00007',
        'tests': ['Alkalinity', 'Hardness', 'TDS', 'pH', 'Conductivity']
    },
    'module_b': {
        'name': 'Module B: Metals (ICP-MS)',
        'short_name': 'MOD-B',
        'cost': 5.00,
        'weight_lbs': 0.4,
        'bottle': '1300-00008',
        'tests': ['EPA 200.8 Metals Panel']
    },
    'module_c': {
        'name': 'Module C: Anions',
        'short_name': 'MOD-C',
        'cost': 1.50,
        'cost_shared': 0.00,
        'weight_lbs': 0.3,
        'bottle': '1300-00007',
        'tests': ['Chloride', 'Sulfate', 'Nitrate', 'Phosphate']
    },
    'module_d': {
        'name': 'Module D: Nutrients',
        'short_name': 'MOD-D',
        'cost': 4.00,
        'weight_lbs': 0.5,
        'bottle': '1300-00009',
        'tests': ['EPA 300.1 Nutrients']
    },
    'module_p': {
        'name': 'Module P: PFAS Testing',
        'short_name': 'MOD-P',
        'cost': 15.50,
        'weight_lbs': 0.8,
        'bottle': '1300-00010',
        'bottles_needed': 2,
        'tests': ['EPA 537.1/1633A PFAS Panel']
    }
}

# Constants
BASE_KIT_COST = 9.50
BASE_KIT_WEIGHT = 1.5
ASSEMBLY_TIME_MINUTES = 7


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_fedex_service_type(is_compliance: bool) -> str:
    """Get FedEx service type code"""
    return "FEDEX_2_DAY" if is_compliance else "FEDEX_GROUND"


def count_bottles_custom(selected_modules: List[str], sharing_active: bool) -> int:
    """Count bottles for custom orders"""
    bottles = 0
    for mod in selected_modules:
        if mod == 'module_a':
            bottles += 1
        elif mod == 'module_b':
            bottles += 1
        elif mod == 'module_c' and not sharing_active:
            bottles += 1
        elif mod == 'module_d':
            bottles += 1
        elif mod == 'module_p':
            bottles += 2
    return bottles


def calculate_custom_package_info(selected_modules: List[str], sharing_active: bool) -> Tuple[int, float, int]:
    """Calculate bottles, weight, and packages for custom orders"""
    bottle_count = count_bottles_custom(selected_modules, sharing_active)
    package_count = max(1, math.ceil(bottle_count / 2))
    
    weight = BASE_KIT_WEIGHT * package_count
    for mod in selected_modules:
        if mod in MODULE_LIBRARY:
            weight += MODULE_LIBRARY[mod].get('weight_lbs', 0)
    
    return bottle_count, round(weight, 2), package_count


def calculate_custom_material_cost(selected_modules: List[str], sharing_active: bool, package_count: int) -> float:
    """Calculate material cost for custom orders"""
    cost = BASE_KIT_COST * package_count
    for mod in selected_modules:
        if mod == 'module_c' and sharing_active:
            cost += MODULE_LIBRARY[mod]['cost_shared']
        elif mod in MODULE_LIBRARY:
            cost += MODULE_LIBRARY[mod]['cost']
    return round(cost, 2)


def estimate_shipping_cost(is_compliance: bool, package_count: int) -> float:
    """Estimate shipping when FedEx rate unavailable"""
    per_package = 50.00 if is_compliance else 12.00
    return per_package * package_count


def calculate_total_shipping(
    fedex_api: FedExAPI, 
    destination: Dict, 
    weight_per_pkg: float, 
    package_count: int,
    service_type: str, 
    is_compliance: bool
) -> Optional[Dict]:
    """Calculate total shipping for all packages"""
    total = 0
    last_rate = None
    
    for _ in range(package_count):
        rate = fedex_api.calculate_shipping_rate(destination, weight_per_pkg, service_type, is_compliance)
        if rate:
            total += rate['total_charge']
            last_rate = rate
        else:
            return None
    
    if last_rate:
        return {
            'total_charge': round(total, 2),
            'service_name': last_rate['service_name'],
            'transit_time': last_rate.get('transit_time', 'N/A'),
            'package_count': package_count,
            'cost_per_package': round(total / package_count, 2),
            'demo_mode': last_rate.get('demo_mode', False)
        }
    return None


# =============================================================================
# PICK LIST GENERATION
# =============================================================================

def generate_bundle_pick_list(bundle_sku: str, bundle_data: Dict) -> Dict:
    """Generate pick list for pre-packed bundle (just kit SKUs)"""
    items = []
    total_kits = 0
    
    for kit in bundle_data['kits']:
        kit_info = PREPACKED_KIT_SKUS[kit['type']]
        items.append({
            'part': kit_info['sku'],
            'description': kit_info['name'],
            'qty': kit['qty'],
            'note': None
        })
        total_kits += kit['qty']
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'order_type': 'BUNDLE',
        'bundle_sku': bundle_sku,
        'bundle_name': bundle_data['name'],
        'category': bundle_data['category'],
        'has_pfas': bundle_data['has_pfas'],
        'total_kits': total_kits,
        'items': items,
        'special_notes': [
            f"📦 PRE-PACKED BUNDLE: {bundle_sku}",
            "All components are pre-assembled in kit boxes - no individual picking required"
        ] + (["⚠️ PFAS KIT INCLUDED - Handle with PFAS-free gloves"] if bundle_data['has_pfas'] else [])
    }


def generate_custom_pick_list(
    selected_modules: List[str], 
    bottle_count: int, 
    package_count: int, 
    sharing_active: bool
) -> Dict:
    """Generate pick list for custom orders (individual components)"""
    has_pfas = 'module_p' in selected_modules
    items = []
    
    # Shipping Box
    items.append({'part': '1300-00058', 'description': 'Shipping Box', 'qty': package_count, 'note': None})
    
    # Bottles
    if 'module_a' in selected_modules or 'module_c' in selected_modules:
        note = 'SHARED by MOD-A & MOD-C' if sharing_active else None
        items.append({'part': '1300-00007', 'description': 'Bottle: Anions + Gen Chem', 'qty': 1, 'note': note})
    
    if 'module_b' in selected_modules:
        items.append({'part': '1300-00008', 'description': 'Bottle: Metals (HNO₃)', 'qty': 1, 'note': None})
    
    if 'module_d' in selected_modules:
        items.append({'part': '1300-00009', 'description': 'Bottle: Nutrients (H₂SO₄)', 'qty': 1, 'note': None})
    
    if 'module_p' in selected_modules:
        items.append({'part': '1300-00010', 'description': 'Bottle: PFAS', 'qty': 2, 'note': 'Always 2 bottles'})
    
    # Gloves
    if has_pfas:
        items.append({'part': '1300-00019', 'description': 'Gloves (PFAS-free)', 'qty': package_count * 2, 'note': 'PFAS order'})
    else:
        items.append({'part': '1300-00018', 'description': 'Gloves (Nitrile)', 'qty': package_count * 2, 'note': None})
    
    # Packaging
    non_pfas_bottles = bottle_count - (2 if has_pfas else 0)
    if non_pfas_bottles > 0:
        items.append({'part': '1300-00027', 'description': 'Bottle Protection (Generic)', 'qty': non_pfas_bottles, 'note': None})
    if has_pfas:
        items.append({'part': '1300-00028', 'description': 'Bottle Protection (PFAS)', 'qty': 2, 'note': None})
    
    # Documents
    items.append({'part': '1300-00029', 'description': 'Collection Instructions', 'qty': package_count, 'note': None})
    items.append({'part': '1300-00030', 'description': 'COC Form', 'qty': 1, 'note': None})
    
    # Build notes
    notes = ["🔧 CUSTOM ORDER - Individual component picking required"]
    if package_count > 1:
        notes.append(f"⚠️ MULTI-PACKAGE: {package_count} boxes (max 2 bottles per box)")
    if has_pfas:
        notes.append("⚠️ PFAS ORDER: Use PFAS-free gloves and PFAS packaging")
    if sharing_active:
        notes.append("✅ A+C SHARING: MOD-A and MOD-C share bottle 1300-00007")
    
    module_names = [MODULE_LIBRARY[m]['short_name'] for m in selected_modules if m in MODULE_LIBRARY]
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'order_type': 'CUSTOM',
        'bundle_sku': None,
        'bundle_name': 'Custom Order',
        'modules': module_names,
        'has_pfas': has_pfas,
        'bottle_count': bottle_count,
        'package_count': package_count,
        'sharing_active': sharing_active,
        'assembly_time': ASSEMBLY_TIME_MINUTES * package_count,
        'items': items,
        'special_notes': notes
    }


def format_pick_list_text(pick_list: Dict) -> str:
    """Format pick list as text"""
    lines = []
    lines.append("=" * 60)
    lines.append("KELP LABORATORY SERVICES")
    lines.append("KIT ASSEMBLY PICK LIST")
    lines.append("=" * 60)
    lines.append(f"Generated: {pick_list['timestamp']}")
    lines.append(f"Order Type: {pick_list['order_type']}")
    
    if pick_list['order_type'] == 'BUNDLE':
        lines.append(f"Bundle SKU: {pick_list['bundle_sku']}")
        lines.append(f"Bundle Name: {pick_list['bundle_name']}")
        lines.append(f"Category: {pick_list['category']}")
        lines.append(f"Total Kits: {pick_list['total_kits']}")
    else:
        lines.append(f"Modules: {', '.join(pick_list.get('modules', []))}")
        lines.append(f"Bottles: {pick_list.get('bottle_count', 0)}")
        lines.append(f"Packages: {pick_list.get('package_count', 1)}")
        lines.append(f"Est. Assembly: {pick_list.get('assembly_time', 7)} minutes")
    
    lines.append(f"PFAS Included: {'Yes ⚠️' if pick_list['has_pfas'] else 'No'}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("SPECIAL NOTES:")
    for note in pick_list['special_notes']:
        lines.append(f"  {note}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("PICK LIST:")
    lines.append(f"{'Part Number':<20} {'Description':<30} {'Qty':>6}")
    lines.append("-" * 60)
    
    for item in pick_list['items']:
        lines.append(f"☐ {item['part']:<18} {item['description']:<30} {item['qty']:>6}")
        if item.get('note'):
            lines.append(f"   → {item['note']}")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("Assembled By: _________________________ Date: ____________")
    lines.append("Verified By:  _________________________ Date: ____________")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def generate_pick_list_pdf(pick_list: Dict, order_id: str = None, customer_name: str = None) -> Optional[bytes]:
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
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=20, spaceAfter=6,
        alignment=TA_CENTER, textColor=colors.HexColor('#0066B2')
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'], fontSize=11, spaceAfter=6, alignment=TA_CENTER
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading2'], fontSize=12,
        spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#0066B2')
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("KELP LABORATORY SERVICES", title_style))
    elements.append(Paragraph("Kit Assembly Pick List", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Order info
    info_parts = [f"Generated: {pick_list['timestamp']}"]
    if order_id:
        info_parts.append(f"Order: {order_id}")
    if customer_name:
        info_parts.append(f"Customer: {customer_name}")
    elements.append(Paragraph(" | ".join(info_parts), subtitle_style))
    
    # Order type badge
    order_type_text = f"<b>{pick_list['order_type']}</b>"
    if pick_list['order_type'] == 'BUNDLE':
        order_type_text += f" - {pick_list['bundle_sku']} - {pick_list['bundle_name']}"
    elements.append(Paragraph(order_type_text, subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary
    elements.append(Paragraph("Order Summary", section_style))
    
    if pick_list['order_type'] == 'BUNDLE':
        summary_data = [
            ['Bundle SKU:', pick_list['bundle_sku']],
            ['Bundle Name:', pick_list['bundle_name']],
            ['Category:', pick_list['category']],
            ['Total Kits:', str(pick_list['total_kits'])],
            ['PFAS Included:', 'Yes ⚠️' if pick_list['has_pfas'] else 'No'],
        ]
    else:
        summary_data = [
            ['Modules:', ', '.join(pick_list.get('modules', []))],
            ['Bottles:', str(pick_list.get('bottle_count', 0))],
            ['Packages:', str(pick_list.get('package_count', 1))],
            ['A+C Sharing:', 'Yes' if pick_list.get('sharing_active') else 'No'],
            ['PFAS Included:', 'Yes ⚠️' if pick_list['has_pfas'] else 'No'],
            ['Est. Assembly:', f"{pick_list.get('assembly_time', 7)} minutes"],
        ]
    
    summary_table = Table(summary_data, colWidths=[1.5*inch, 4*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Pick list table
    elements.append(Paragraph("Pick List Items", section_style))
    
    pick_data = [['☐', 'Part Number', 'Description', 'Qty']]
    for item in pick_list['items']:
        desc = item['description']
        if item.get('note'):
            desc += f" ({item['note']})"
        pick_data.append(['☐', item['part'], desc, str(item['qty'])])
    
    pick_table = Table(pick_data, colWidths=[0.4*inch, 1.5*inch, 3.2*inch, 0.5*inch])
    pick_table.setStyle(TableStyle([
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
    elements.append(pick_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Special notes
    if pick_list['special_notes']:
        elements.append(Paragraph("Special Instructions", section_style))
        for note in pick_list['special_notes']:
            elements.append(Paragraph(f"• {note}", styles['Normal']))
        elements.append(Spacer(1, 0.1*inch))
    
    # Signature section
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("─" * 70, styles['Normal']))
    footer_data = [
        ['Assembled By:', '________________________', 'Date:', '____________'],
        ['Verified By:', '________________________', 'Date:', '____________'],
    ]
    footer_table = Table(footer_data, colWidths=[1*inch, 2.2*inch, 0.5*inch, 1.5*inch])
    footer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(footer_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# CUSTOM CSS
# =============================================================================

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    
    .bundle-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #0066B2;
        margin: 0.5rem 0;
        transition: all 0.2s;
    }
    
    .bundle-card:hover {
        background: #f0f8ff;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .bundle-card.selected {
        background: #e6f3ff;
        border-color: #00A86B;
        border-width: 3px;
    }
    
    .pfas-warning {
        background: #FFF3CD;
        border-left: 4px solid #FFA500;
        padding: 0.75rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    
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
    
    .price-display {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #0066B2 0%, #3399CC 100%);
        border-radius: 8px;
        color: white;
        margin: 1rem 0;
    }
    
    .price-display .label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    .price-display .amount {
        font-size: 2.5rem;
        font-weight: bold;
    }
    
    .shipping-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #0066B2;
        margin: 1rem 0;
    }
    
    .rate-display {
        font-size: 1.5rem;
        font-weight: bold;
        color: #00A86B;
        padding: 1rem;
        background: #f0f8f5;
        border-radius: 4px;
        text-align: center;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

if 'order_type' not in st.session_state:
    st.session_state.order_type = 'bundle'
if 'selected_bundle' not in st.session_state:
    st.session_state.selected_bundle = None
if 'modules_selected' not in st.session_state:
    st.session_state.modules_selected = {}
if 'shipping_address' not in st.session_state:
    st.session_state.shipping_address = None
if 'shipping_rate' not in st.session_state:
    st.session_state.shipping_rate = None
if 'current_pick_list' not in st.session_state:
    st.session_state.current_pick_list = None
if 'order_history' not in st.session_state:
    st.session_state.order_history = []
if 'fedex_api' not in st.session_state:
    st.session_state.fedex_api = FedExAPI()


# =============================================================================
# HEADER
# =============================================================================

st.title("🧪 KELP Smart Kit Builder Pro")
st.markdown("""
**Intelligent Water Testing Kit Configuration System**  
*Pre-Packed Bundles & Custom Orders with Professional Pick Lists*
""")

st.divider()


# =============================================================================
# SIDEBAR - SHIPPING CONFIGURATION
# =============================================================================

with st.sidebar:
    st.header("📍 Shipping Configuration")
    
    if st.button("🔄 Reset All", key="reset_btn"):
        st.session_state.order_type = 'bundle'
        st.session_state.selected_bundle = None
        st.session_state.modules_selected = {}
        st.session_state.shipping_address = None
        st.session_state.shipping_rate = None
        st.session_state.current_pick_list = None
        st.rerun()
    
    st.divider()
    
    st.subheader("Destination Address")
    
    contact_name = st.text_input("Contact Name", placeholder="John Smith", key="contact")
    street = st.text_input("Street Address", placeholder="123 Main Street", key="street")
    street2 = st.text_input("Address Line 2", placeholder="Suite 100", key="street2")
    
    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("City", placeholder="San Francisco", key="city")
    with col2:
        state = st.text_input("State", placeholder="CA", max_chars=2, key="state")
    
    col3, col4 = st.columns(2)
    with col3:
        zip_code = st.text_input("ZIP Code", placeholder="94102", key="zip")
    with col4:
        phone = st.text_input("Phone", placeholder="4155551234", key="phone")
    
    if st.button("💾 Save Address", type="primary", key="save_addr"):
        if city and state and zip_code:
            street_lines = [street] if street else []
            if street2:
                street_lines.append(street2)
            st.session_state.shipping_address = {
                'contact_name': contact_name,
                'streetLines': street_lines,
                'city': city,
                'stateOrProvinceCode': state.upper(),
                'postalCode': zip_code,
                'countryCode': 'US',
                'phone': phone
            }
            st.success("✅ Address saved!")
            st.rerun()
        else:
            st.error("⚠️ City, State, ZIP required")
    
    if st.session_state.shipping_address:
        st.divider()
        addr = st.session_state.shipping_address
        st.markdown(f"**Current:** {addr['city']}, {addr['stateOrProvinceCode']} {addr['postalCode']}")
        if st.button("🗑️ Clear Address", key="clear_addr"):
            st.session_state.shipping_address = None
            st.session_state.shipping_rate = None
            st.rerun()


# =============================================================================
# STEP 1: ORDER TYPE SELECTION
# =============================================================================

st.header("1️⃣ Select Order Type")

order_type = st.radio(
    "How would you like to order?",
    options=['bundle', 'custom'],
    format_func=lambda x: "📦 Pre-Packed Bundle (10 options)" if x == 'bundle' else "🔧 Custom Module Selection",
    horizontal=True,
    key='order_type_radio'
)
st.session_state.order_type = order_type

st.divider()


# =============================================================================
# BUNDLE SELECTION
# =============================================================================

if st.session_state.order_type == 'bundle':
    st.subheader("📦 Select a Pre-Packed Bundle")
    st.markdown("Each bundle is a **pre-assembled kit** - pick list shows kit SKU only.")
    
    # Group by category
    categories = {}
    for sku, data in BUNDLE_DEFINITIONS.items():
        cat = data['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((sku, data))
    
    # Display
    for category, bundles in categories.items():
        st.markdown(f"**{category}**")
        
        cols = st.columns(min(len(bundles), 3))
        for i, (sku, data) in enumerate(bundles):
            with cols[i % 3]:
                is_selected = st.session_state.selected_bundle == sku
                
                # Kit info
                kit_skus = [PREPACKED_KIT_SKUS[k['type']]['sku'] for k in data['kits']]
                
                btn_label = f"{'✅ ' if is_selected else ''}{sku}\n{data['name']}\n${data['price']:.0f}"
                
                if st.button(btn_label, key=f"bundle_{sku}", type="primary" if is_selected else "secondary"):
                    st.session_state.selected_bundle = sku
                    st.session_state.shipping_rate = None
                    st.session_state.current_pick_list = None
                    st.rerun()
                
                if data['has_pfas']:
                    st.caption("⚠️ Includes PFAS Kit")
        
        st.markdown("")
    
    # Selected bundle info
    if st.session_state.selected_bundle:
        bundle = BUNDLE_DEFINITIONS[st.session_state.selected_bundle]
        
        st.success(f"**Selected: {st.session_state.selected_bundle} - {bundle['name']}**")
        st.markdown(f"_{bundle['description']}_")
        
        st.markdown("**Pre-Packed Kits Included:**")
        for kit in bundle['kits']:
            kit_info = PREPACKED_KIT_SKUS[kit['type']]
            st.markdown(f"- `{kit_info['sku']}` - {kit_info['name']} × {kit['qty']}")
    
    # Clear selection for custom mode
    st.session_state.modules_selected = {}


# =============================================================================
# CUSTOM MODULE SELECTION
# =============================================================================

else:
    st.subheader("🔧 Custom Module Selection")
    st.markdown("Select individual modules - pick list shows **all components**.")
    
    modules_to_show = ['module_a', 'module_b', 'module_c', 'module_d', 'module_p']
    
    sharing_active = (
        st.session_state.modules_selected.get('module_a', False) and 
        st.session_state.modules_selected.get('module_c', False)
    )
    
    for mod_key in modules_to_show:
        mod = MODULE_LIBRARY[mod_key]
        is_selected = st.session_state.modules_selected.get(mod_key, False)
        
        # Special title for shared module C
        if mod_key == 'module_c' and sharing_active:
            title = f"✅ {mod['name']} 🎁 FREE (SHARED)" if is_selected else f"{mod['name']} 🎁 FREE when with MOD-A"
        elif mod_key == 'module_p':
            title = f"✅ {mod['name']} ⚠️" if is_selected else f"{mod['name']} ⚠️"
        else:
            title = f"✅ {mod['name']}" if is_selected else mod['name']
        
        with st.expander(title, expanded=(mod_key == 'module_c' and sharing_active)):
            checked = st.checkbox(
                f"Select {mod['short_name']}", 
                key=f"mod_{mod_key}", 
                value=is_selected
            )
            st.session_state.modules_selected[mod_key] = checked
            
            if mod_key == 'module_c' and sharing_active:
                st.success("✅ **Smart Sharing!** Uses same bottle as MOD-A - FREE!")
            
            if mod_key == 'module_p' and checked:
                st.warning("⚠️ **PFAS Special Handling** - PFAS-free gloves required")
            
            st.markdown(f"**Part:** {mod['bottle']} | **Tests:** {', '.join(mod['tests'])}")
            
            if mod_key == 'module_c' and sharing_active:
                st.markdown("**Cost:** $0.00 (FREE!)")
            else:
                st.markdown(f"**Cost:** ${mod['cost']:.2f}")
    
    # Clear bundle selection
    st.session_state.selected_bundle = None

st.divider()


# =============================================================================
# SHIPPING OPTIONS
# =============================================================================

st.subheader("📦 Shipping Options")

is_compliance = st.checkbox(
    "**Compliance Shipping** (FedEx 2-Day)",
    key="compliance_check",
    value=st.session_state.modules_selected.get('compliance_shipping', False)
)
st.session_state.modules_selected['compliance_shipping'] = is_compliance

if is_compliance:
    st.info("📦 2-Day shipping for time-sensitive samples")

st.divider()


# =============================================================================
# CALCULATE ORDER DETAILS
# =============================================================================

# Determine what's selected
if st.session_state.order_type == 'bundle' and st.session_state.selected_bundle:
    bundle = BUNDLE_DEFINITIONS[st.session_state.selected_bundle]
    has_selection = True
    has_pfas = bundle['has_pfas']
    total_kits = sum(k['qty'] for k in bundle['kits'])
    package_count = total_kits
    total_weight = sum(PREPACKED_KIT_SKUS[k['type']]['weight_lbs'] * k['qty'] for k in bundle['kits'])
    customer_price = bundle['price']
    
elif st.session_state.order_type == 'custom':
    selected_modules = [k for k in ['module_a', 'module_b', 'module_c', 'module_d', 'module_p'] 
                       if st.session_state.modules_selected.get(k, False)]
    has_selection = len(selected_modules) > 0
    
    if has_selection:
        sharing_active = 'module_a' in selected_modules and 'module_c' in selected_modules
        has_pfas = 'module_p' in selected_modules
        bottle_count, total_weight, package_count = calculate_custom_package_info(selected_modules, sharing_active)
        material_cost = calculate_custom_material_cost(selected_modules, sharing_active, package_count)
    else:
        has_pfas = False
        package_count = 0
        total_weight = 0
        material_cost = 0
else:
    has_selection = False
    has_pfas = False
    package_count = 0
    total_weight = 0


# =============================================================================
# STEP 2: SHIPPING RATE
# =============================================================================

st.header("2️⃣ Calculate Shipping Rate")

if has_selection:
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        if st.session_state.order_type == 'bundle':
            st.metric("Kits", total_kits)
        else:
            st.metric("Bottles", bottle_count)
    with col_m2:
        st.metric("Packages", package_count)
    with col_m3:
        st.metric("Weight", f"{total_weight:.1f} lbs")
    
    if is_compliance:
        total_weight += 5.0 * package_count  # Add cooler weight
    
    has_address = st.session_state.shipping_address and 'city' in st.session_state.shipping_address
    
    if has_address:
        if st.button(f"🔄 Get FedEx Rate ({package_count} pkg)", type="primary", key="get_rate"):
            with st.spinner("Calculating..."):
                service_type = get_fedex_service_type(is_compliance)
                weight_per_pkg = total_weight / package_count if package_count > 0 else total_weight
                
                rate = calculate_total_shipping(
                    st.session_state.fedex_api,
                    st.session_state.shipping_address,
                    weight_per_pkg,
                    package_count,
                    service_type,
                    is_compliance
                )
                
                if rate:
                    st.session_state.shipping_rate = rate
                    st.success("✅ Rate calculated!")
                    st.rerun()
        
        if st.session_state.shipping_rate:
            rate = st.session_state.shipping_rate
            st.markdown(f"""
            <div class="shipping-card">
                <p><strong>Service:</strong> {rate['service_name']} | <strong>Packages:</strong> {rate['package_count']}</p>
                <div class="rate-display">Shipping: ${rate['total_charge']:.2f}</div>
                {'<p style="text-align:center; color:#999; font-size:0.9rem;">Demo Mode</p>' if rate.get('demo_mode') else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("💡 Enter shipping address in sidebar")
        estimated = estimate_shipping_cost(is_compliance, package_count)
        st.caption(f"Estimated: ${estimated:.2f}")
else:
    st.warning("⚠️ Select a bundle or modules first")

st.divider()


# =============================================================================
# STEP 3: COST SUMMARY
# =============================================================================

st.header("3️⃣ Cost Summary")

if has_selection:
    if st.session_state.shipping_rate:
        shipping_cost = st.session_state.shipping_rate['total_charge']
    else:
        shipping_cost = estimate_shipping_cost(is_compliance, package_count)
    
    if st.session_state.order_type == 'bundle':
        base_price = bundle['price']
        total_price = base_price + shipping_cost
        price_label = f"Bundle: {st.session_state.selected_bundle}"
    else:
        base_price = material_cost
        total_price = base_price + shipping_cost
        price_label = "Custom Order"
    
    st.markdown(f"""
    <div class="price-display">
        <div class="label">{price_label}</div>
        <div class="amount">${total_price:.2f}</div>
        <div class="label">includes ${shipping_cost:.2f} shipping</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()


# =============================================================================
# STEP 4: GENERATE PICK LIST
# =============================================================================

st.header("4️⃣ Generate Pick List")

if has_selection:
    if st.button("📋 Generate Pick List", type="primary", key="gen_pick"):
        if st.session_state.order_type == 'bundle':
            pick_list = generate_bundle_pick_list(
                st.session_state.selected_bundle,
                BUNDLE_DEFINITIONS[st.session_state.selected_bundle]
            )
        else:
            pick_list = generate_custom_pick_list(
                selected_modules, bottle_count, package_count, sharing_active
            )
        
        st.session_state.current_pick_list = pick_list
        st.success("✅ Pick list generated!")
    
    # Display pick list
    if st.session_state.current_pick_list:
        pick_list = st.session_state.current_pick_list
        pick_text = format_pick_list_text(pick_list)
        
        st.markdown(f"<div class='pick-list-box'>{pick_text}</div>", unsafe_allow_html=True)
        
        # Downloads
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            filename_base = pick_list.get('bundle_sku') or 'CUSTOM'
            st.download_button(
                "📥 Download TXT",
                data=pick_text,
                file_name=f"KELP_PickList_{filename_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="dl_txt"
            )
        
        with col_dl2:
            order_id = st.text_input("Order ID:", placeholder="ORD-001", key="order_id")
            customer = st.text_input("Customer:", placeholder="John Smith", key="customer")
            
            if st.button("📄 Generate PDF", key="gen_pdf"):
                pdf_bytes = generate_pick_list_pdf(pick_list, order_id, customer)
                if pdf_bytes:
                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"KELP_PickList_{filename_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        key="dl_pdf"
                    )
                else:
                    st.error("Install reportlab: `pip install reportlab`")
else:
    st.warning("⚠️ Select a bundle or modules first")

st.divider()


# =============================================================================
# STEP 5: COMPLETE ORDER
# =============================================================================

st.header("5️⃣ Complete Order")

if has_selection and st.session_state.current_pick_list:
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        if st.button("💾 Save Order & Reset", type="primary", key="save_order"):
            order = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': st.session_state.order_type,
                'bundle': st.session_state.selected_bundle,
                'packages': package_count,
                'price': total_price if 'total_price' in dir() else 0,
            }
            st.session_state.order_history.append(order)
            
            # Reset
            st.session_state.selected_bundle = None
            st.session_state.modules_selected = {}
            st.session_state.shipping_rate = None
            st.session_state.current_pick_list = None
            
            st.success("✅ Order saved!")
            st.balloons()
            st.rerun()
    
    with col_b2:
        if st.button("🔄 Reset (Don't Save)", key="reset_no_save"):
            st.session_state.selected_bundle = None
            st.session_state.modules_selected = {}
            st.session_state.shipping_rate = None
            st.session_state.current_pick_list = None
            st.rerun()
else:
    st.info("💡 Generate pick list to complete order")


# =============================================================================
# ORDER HISTORY
# =============================================================================

if st.session_state.order_history:
    st.divider()
    st.header("📊 Order History")
    df = pd.DataFrame(st.session_state.order_history)
    st.dataframe(df)


# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.markdown("""
---
**KELP Kit Builder Pro v6.0** | Pre-Packed Bundles | February 2026

**Pre-Packed Kit SKUs:**
- `1300-00001_REV01` - KIT KELP (Metals + Anion + Gen Chem)
- `1300-00003_REV01` - KIT KELP (PFAS)

**Bundles:** COM-001, COM-002, RE-001, RE-002, RES-001 through RES-006
---
""")
