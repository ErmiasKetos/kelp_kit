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

class FedExAPI:
    """FedEx API Integration with multi-package support"""
    
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
        self.ship_url = f"{self.base_url}/ship/v1/shipments"
        
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
        
        if self.demo_mode:
            st.sidebar.info("ℹ️ **FedEx Demo Mode** - Using estimated rates")
    
    def authenticate(self) -> bool:
        if self.demo_mode:
            return True
        if self.access_token:
            return True
        if self.auth_failed:
            return False
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {"grant_type": "client_credentials", "client_id": self.api_key, "client_secret": self.secret_key}
            response = requests.post(self.auth_url, headers=headers, data=data, timeout=10)
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                return True
            else:
                self.auth_failed = True
                return False
        except:
            self.auth_failed = True
            return False
    
    def calculate_shipping_rate(self, destination: Dict, weight_lbs: float, 
                                service_type: str = "FEDEX_GROUND", is_compliance: bool = False) -> Optional[Dict]:
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
        
        if not self.authenticate():
            return None
        
        try:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"}
            payload = {
                "accountNumber": {"value": self.account_number},
                "requestedShipment": {
                    "shipper": {"address": self.origin},
                    "recipient": {"address": destination},
                    "pickupType": "USE_SCHEDULED_PICKUP",
                    "serviceType": service_type,
                    "packagingType": "YOUR_PACKAGING",
                    "rateRequestType": ["ACCOUNT"],
                    "requestedPackageLineItems": [{
                        "weight": {"units": "LB", "value": weight_lbs},
                        "dimensions": {"length": 12, "width": 10, "height": 8, "units": "IN"}
                    }]
                }
            }
            response = requests.post(self.rate_url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'output' in data and 'rateReplyDetails' in data['output']:
                    rate_details = data['output']['rateReplyDetails'][0]
                    rated_shipment = rate_details['ratedShipmentDetails'][0]
                    return {
                        'total_charge': float(rated_shipment['totalNetCharge']),
                        'service_name': rate_details.get('serviceName', service_type),
                        'transit_time': rate_details.get('operationalDetail', {}).get('transitTime', 'N/A'),
                        'delivery_date': rate_details.get('operationalDetail', {}).get('deliveryDate', 'N/A'),
                        'demo_mode': False
                    }
            return None
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return None
    
    def generate_label(self, destination: Dict, weight_lbs: float, service_type: str = "FEDEX_GROUND",
                      package_number: int = 1, total_packages: int = 1) -> Optional[Dict]:
        if self.demo_mode:
            import random
            tracking = f"{''.join([str(random.randint(0,9)) for _ in range(12)])}"
            return {
                'tracking_number': tracking,
                'label_url': f"https://demo.fedex.com/label/{tracking}.pdf",
                'package_number': package_number,
                'total_packages': total_packages,
                'demo_mode': True
            }
        return None


# ============================================================================
# KIT COMPONENTS & BUNDLES CONFIGURATION
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

# Module definitions
COMPONENT_LIBRARY = {
    'base': {
        'name': 'Base Kit Components',
        'cost': 9.50,
        'weight_lbs': 1.5,
    },
    'module_a': {
        'name': 'Module A: General Chemistry',
        'short_name': 'MOD-A',
        'cost': 2.50,
        'weight_lbs': 0.3,
        'bottle': '1300-00007',
        'bottle_desc': '250mL HDPE unacidified',
        'tests': ['Alkalinity', 'Hardness', 'TDS', 'pH', 'Conductivity'],
        'methods': ['SM 2320B', 'SM 2340C', 'SM 2510B', 'SM 2540C']
    },
    'module_b': {
        'name': 'Module B: Metals (ICP-MS)',
        'short_name': 'MOD-B',
        'cost': 5.00,
        'weight_lbs': 0.4,
        'bottle': '1300-00008',
        'bottle_desc': '250mL HDPE pre-acidified (HNO₃)',
        'preservation': 'Pre-acidified with HNO₃',
        'tests': ['EPA 200.8 Metals Panel'],
        'methods': ['EPA 200.8']
    },
    'module_c': {
        'name': 'Module C: Anions/Nutrients',
        'short_name': 'MOD-C',
        'cost': 1.50,
        'cost_shared': 0.00,
        'weight_lbs': 0.3,
        'bottle': '1300-00007',
        'bottle_desc': '250mL HDPE unacidified (SHARED with A)',
        'tests': ['Chloride', 'Sulfate', 'Nitrate', 'Phosphate'],
        'methods': ['EPA 300.1']
    },
    'module_d': {
        'name': 'Module D: Nutrients (IC)',
        'short_name': 'MOD-D',
        'cost': 4.00,
        'weight_lbs': 0.5,
        'bottle': '1300-00009',
        'bottle_desc': '250mL PP pre-acidified (H₂SO₄)',
        'preservation': 'Pre-acidified with H₂SO₄',
        'tests': ['EPA 300.1 Nutrients'],
        'methods': ['EPA 353.2', 'EPA 365.1']
    },
    'module_p': {
        'name': 'Module P: PFAS Testing',
        'short_name': 'MOD-P',
        'cost': 15.50,
        'weight_lbs': 0.8,
        'bottle': '1300-00010',
        'bottle_desc': '2× 250mL PP PFAS-certified',
        'bottles_needed': 2,
        'preservation': 'PFAS-free containers',
        'special_handling': True,
        'tests': ['EPA 537.1/1633A PFAS Panel'],
        'methods': ['EPA 537.1', 'EPA 533', 'EPA 1633A']
    }
}

# Pre-configured bundles
BUNDLE_DEFINITIONS = {
    'RES-001': {
        'name': 'Essential Home Water Test',
        'description': 'Basic water quality for homeowners',
        'category': 'Residential',
        'modules': ['module_a', 'module_b', 'module_c'],
        'price': 249.00
    },
    'RES-002': {
        'name': 'Complete Homeowner Package',
        'description': 'Comprehensive water quality with nutrients',
        'category': 'Residential',
        'modules': ['module_a', 'module_b', 'module_c', 'module_d'],
        'price': 349.00
    },
    'RES-004': {
        'name': 'Basic PFAS Screen',
        'description': 'PFAS testing with essential metals and anions',
        'category': 'Residential - PFAS',
        'modules': ['module_b', 'module_c', 'module_p'],
        'price': 475.00
    },
    'RES-005': {
        'name': 'Comprehensive Home Safety Screen',
        'description': 'Full panel including PFAS',
        'category': 'Residential - Premium',
        'modules': ['module_a', 'module_b', 'module_c', 'module_p'],
        'price': 595.00
    },
    'RES-006': {
        'name': 'Ultimate Water Safety Suite',
        'description': 'Complete testing - all modules',
        'category': 'Residential - Premium',
        'modules': ['module_a', 'module_b', 'module_c', 'module_d', 'module_p'],
        'price': 795.00
    },
    'RE-001': {
        'name': 'Real Estate Well Water Package',
        'description': 'Well water testing for property transactions',
        'category': 'Real Estate',
        'modules': ['module_a', 'module_b', 'module_c', 'module_d'],
        'price': 399.00
    },
    'RE-002': {
        'name': 'Conventional Loan Testing Package',
        'description': 'Standard loan requirement testing',
        'category': 'Real Estate',
        'modules': ['module_a', 'module_b', 'module_c'],
        'price': 275.00
    },
    'COM-001': {
        'name': 'Food & Beverage Water Quality',
        'description': 'Process water for F&B operations',
        'category': 'Commercial',
        'modules': ['module_a', 'module_b', 'module_c'],
        'price': 325.00
    },
    'COM-002': {
        'name': 'Agricultural Irrigation Package',
        'description': 'Irrigation water quality assessment',
        'category': 'Commercial',
        'modules': ['module_a', 'module_b', 'module_c'],
        'price': 295.00
    },
}

LABOR_COST = 7.46
ASSEMBLY_TIME_MINUTES = 7


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_modules_from_bundle(bundle_sku: str) -> List[str]:
    """Get list of modules from a bundle SKU"""
    if bundle_sku in BUNDLE_DEFINITIONS:
        return BUNDLE_DEFINITIONS[bundle_sku]['modules']
    return []

def calculate_package_weight(selected_modules: List[str], bottle_count: int) -> Tuple[float, int]:
    package_count = max(1, math.ceil(bottle_count / 2))
    base_weight = COMPONENT_LIBRARY['base']['weight_lbs']
    module_weight = sum(COMPONENT_LIBRARY[m].get('weight_lbs', 0) for m in selected_modules if m in COMPONENT_LIBRARY)
    total_weight = (base_weight + module_weight) * package_count
    return round(total_weight, 2), package_count

def get_fedex_service_type(is_compliance: bool) -> str:
    return "FEDEX_2_DAY" if is_compliance else "FEDEX_GROUND"

def count_bottles(selected_modules: List[str], sharing_active: bool) -> int:
    bottles = 0
    for module_key in selected_modules:
        if module_key == 'module_a':
            bottles += 1
        elif module_key == 'module_b':
            bottles += 1
        elif module_key == 'module_c':
            if not sharing_active:
                bottles += 1
        elif module_key == 'module_d':
            bottles += 1
        elif module_key == 'module_p':
            bottles += 2
    return bottles

def calculate_material_cost(selected_modules: List[str], sharing_active: bool, package_count: int) -> float:
    material_cost = COMPONENT_LIBRARY['base']['cost'] * package_count
    for module_key in selected_modules:
        if module_key == 'module_c' and sharing_active:
            material_cost += COMPONENT_LIBRARY[module_key]['cost_shared']
        elif module_key in COMPONENT_LIBRARY:
            material_cost += COMPONENT_LIBRARY[module_key]['cost']
    return round(material_cost, 2)

def estimate_shipping_cost(is_compliance: bool, package_count: int) -> float:
    cost_per_package = 50.00 if is_compliance else 8.00
    return cost_per_package * package_count

def generate_pick_list(selected_modules: List[str], bottle_count: int, 
                       package_count: int, sharing_active: bool,
                       bundle_sku: str = None) -> Dict:
    """Generate pick list with part numbers"""
    
    has_pfas = 'module_p' in selected_modules
    
    pick_list = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'bundle_sku': bundle_sku,
        'bundle_name': BUNDLE_DEFINITIONS.get(bundle_sku, {}).get('name', 'Custom Order') if bundle_sku else 'Custom Order',
        'package_count': package_count,
        'bottle_count': bottle_count,
        'assembly_time_estimate': ASSEMBLY_TIME_MINUTES * package_count,
        'has_pfas': has_pfas,
        'sharing_active': sharing_active,
        'selected_modules': [COMPONENT_LIBRARY[m]['short_name'] for m in selected_modules if m in COMPONENT_LIBRARY],
        'items': [],
        'special_notes': []
    }
    
    # Shipping Box
    pick_list['items'].append({'part': '1300-00058', 'description': 'Shipping Box', 'qty': package_count})
    
    # Bottles based on modules
    if 'module_a' in selected_modules or 'module_c' in selected_modules:
        note = 'SHARED by MOD-A and MOD-C' if sharing_active else None
        pick_list['items'].append({'part': '1300-00007', 'description': 'Bottle: Anions + Gen Chem', 'qty': 1, 'note': note})
    
    if 'module_b' in selected_modules:
        pick_list['items'].append({'part': '1300-00008', 'description': 'Bottle: Metals', 'qty': 1})
    
    if 'module_d' in selected_modules:
        pick_list['items'].append({'part': '1300-00009', 'description': 'Bottle: Nutrients', 'qty': 1})
    
    if 'module_p' in selected_modules:
        pick_list['items'].append({'part': '1300-00010', 'description': 'Bottle: PFAS', 'qty': 2, 'note': 'Always 2 for PFAS'})
    
    # Gloves
    if has_pfas:
        pick_list['items'].append({'part': '1300-00019', 'description': 'Gloves (PFAS-free)', 'qty': package_count * 2, 'note': 'PFAS order - NO nitrile'})
    else:
        pick_list['items'].append({'part': '1300-00018', 'description': 'Gloves (Nitrile)', 'qty': package_count * 2})
    
    # Packaging
    non_pfas_bottles = bottle_count - (2 if has_pfas else 0)
    if non_pfas_bottles > 0:
        pick_list['items'].append({'part': '1300-00027', 'description': 'Packaging (Generic)', 'qty': non_pfas_bottles})
    if has_pfas:
        pick_list['items'].append({'part': '1300-00028', 'description': 'Packaging (PFAS)', 'qty': 2})
    
    # Documents
    pick_list['items'].append({'part': '1300-00029', 'description': 'Collection Instructions', 'qty': package_count})
    pick_list['items'].append({'part': '1300-00030', 'description': 'COC Form', 'qty': 1})
    
    # Special notes
    if bundle_sku:
        pick_list['special_notes'].append(f"📦 BUNDLE ORDER: {bundle_sku} - {pick_list['bundle_name']}")
    
    if package_count > 1:
        pick_list['special_notes'].append(f"⚠️ MULTI-PACKAGE: {package_count} boxes needed (max 2 bottles per box)")
    
    if has_pfas:
        pick_list['special_notes'].append("🧪 PFAS ORDER: Use PFAS-free gloves (1300-00019) and PFAS packaging (1300-00028)")
    
    if sharing_active:
        pick_list['special_notes'].append("✅ A+C SHARING: MOD-A and MOD-C share bottle 1300-00007")
    
    return pick_list

def format_pick_list_display(pick_list: Dict) -> str:
    output = []
    output.append(f"{'='*50}")
    output.append(f"KELP KIT ASSEMBLY PICK LIST")
    output.append(f"{'='*50}")
    output.append(f"Generated: {pick_list['timestamp']}")
    if pick_list['bundle_sku']:
        output.append(f"Bundle: {pick_list['bundle_sku']} - {pick_list['bundle_name']}")
    else:
        output.append(f"Order Type: Custom")
    output.append(f"Modules: {', '.join(pick_list['selected_modules'])}")
    output.append(f"")
    output.append(f"📦 PACKAGES: {pick_list['package_count']}")
    output.append(f"🧪 BOTTLES: {pick_list['bottle_count']}")
    output.append(f"⏱️  EST. TIME: {pick_list['assembly_time_estimate']} minutes")
    output.append(f"")
    
    if pick_list['special_notes']:
        output.append(f"{'─'*50}")
        output.append(f"SPECIAL NOTES:")
        for note in pick_list['special_notes']:
            output.append(f"  {note}")
        output.append(f"")
    
    output.append(f"{'─'*50}")
    output.append(f"PICK LIST ITEMS:")
    output.append(f"{'Part Number':<14} {'Description':<32} {'Qty':>5}")
    output.append(f"{'─'*14} {'─'*32} {'─'*5}")
    
    for item in pick_list['items']:
        line = f"☐ {item['part']:<12} {item['description']:<32} {item['qty']:>5}"
        output.append(line)
        if item.get('note'):
            output.append(f"   → {item['note']}")
    
    output.append(f"")
    output.append(f"{'='*50}")
    output.append(f"Assembled By: _________________ Date: ___________")
    output.append(f"Verified By:  _________________ Date: ___________")
    output.append(f"{'='*50}")
    
    return "\n".join(output)

def generate_pick_list_pdf(pick_list: Dict, order_id: str = None, customer_name: str = None) -> bytes:
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
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=6, 
                                  alignment=TA_CENTER, textColor=colors.HexColor('#0066B2'))
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=11, 
                                     spaceAfter=6, alignment=TA_CENTER)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=12, 
                                    spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#0066B2'))
    
    elements = []
    
    # Header
    elements.append(Paragraph("KELP LABORATORY SERVICES", title_style))
    elements.append(Paragraph("Kit Assembly Pick List", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Order info line
    info_parts = [f"Generated: {pick_list['timestamp']}"]
    if order_id:
        info_parts.append(f"Order: {order_id}")
    if customer_name:
        info_parts.append(f"Customer: {customer_name}")
    elements.append(Paragraph(" | ".join(info_parts), subtitle_style))
    
    if pick_list['bundle_sku']:
        elements.append(Paragraph(f"<b>Bundle: {pick_list['bundle_sku']} - {pick_list['bundle_name']}</b>", subtitle_style))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary
    elements.append(Paragraph("Order Summary", section_style))
    summary_data = [
        ['Modules:', ', '.join(pick_list['selected_modules'])],
        ['Total Bottles:', str(pick_list['bottle_count'])],
        ['Packages:', str(pick_list['package_count'])],
        ['A+C Sharing:', 'Yes' if pick_list['sharing_active'] else 'No'],
        ['PFAS Included:', 'Yes ⚠️' if pick_list['has_pfas'] else 'No'],
        ['Est. Assembly:', f"{pick_list['assembly_time_estimate']} minutes"],
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
    
    pick_table = Table(pick_data, colWidths=[0.4*inch, 1.1*inch, 3.5*inch, 0.5*inch])
    pick_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066B2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
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

def calculate_total_shipping_cost(fedex_api: FedExAPI, destination: Dict, 
                                  weight_per_package: float, package_count: int,
                                  service_type: str, is_compliance: bool) -> Optional[Dict]:
    total_cost = 0
    last_rate = None
    
    for _ in range(package_count):
        rate = fedex_api.calculate_shipping_rate(destination, weight_per_package, service_type, is_compliance)
        if rate:
            total_cost += rate['total_charge']
            last_rate = rate
        else:
            return None
    
    if last_rate:
        return {
            'total_charge': round(total_cost, 2),
            'service_name': last_rate['service_name'],
            'transit_time': last_rate.get('transit_time', 'N/A'),
            'delivery_date': last_rate.get('delivery_date', 'N/A'),
            'package_count': package_count,
            'cost_per_package': round(total_cost / package_count, 2),
            'demo_mode': last_rate.get('demo_mode', False)
        }
    return None


# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .module-card { background: white; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #0066B2; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1rem; }
    .module-shared { border-left: 4px solid #00A86B; background: linear-gradient(90deg, rgba(0,168,107,0.05) 0%, white 100%); }
    .module-pfas { border-left: 4px solid #FF6B35; background: linear-gradient(90deg, rgba(255,107,53,0.05) 0%, white 100%); }
    .bundle-card { background: white; padding: 1rem; border-radius: 8px; border: 2px solid #0066B2; margin: 0.5rem 0; cursor: pointer; }
    .bundle-card:hover { background: #f0f8ff; }
    .bundle-card.selected { background: #e6f3ff; border-color: #00A86B; }
    .shipping-card { background: white; padding: 1.5rem; border-radius: 8px; border: 2px solid #0066B2; margin: 1rem 0; }
    .rate-display { font-size: 1.5rem; font-weight: bold; color: #00A86B; padding: 1rem; background: #f0f8f5; border-radius: 4px; text-align: center; margin-top: 1rem; }
    .multi-package-warning { background: #FFF3CD; border-left: 4px solid #FFA500; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
    .pick-list { background: #f8f9fa; padding: 1.5rem; border-radius: 8px; border: 1px solid #dee2e6; font-family: 'Courier New', monospace; font-size: 0.85rem; white-space: pre-wrap; max-height: 500px; overflow-y: auto; }
    .labor-note { background: #E7F3FF; border-left: 3px solid #0066B2; padding: 0.75rem; margin-top: 1rem; border-radius: 4px; font-size: 0.9rem; color: #0066B2; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE
# ============================================================================

if 'modules_selected' not in st.session_state:
    st.session_state.modules_selected = {}
if 'selected_bundle' not in st.session_state:
    st.session_state.selected_bundle = None
if 'order_type' not in st.session_state:
    st.session_state.order_type = 'bundle'  # 'bundle' or 'custom'
if 'shipping_address' not in st.session_state:
    st.session_state.shipping_address = None
if 'shipping_rate' not in st.session_state:
    st.session_state.shipping_rate = None
if 'order_history' not in st.session_state:
    st.session_state.order_history = []
if 'fedex_api' not in st.session_state:
    st.session_state.fedex_api = FedExAPI()
if 'show_costs' not in st.session_state:
    st.session_state.show_costs = False


# ============================================================================
# HEADER
# ============================================================================

st.title("🧪 KELP Smart Kit Builder Pro")
st.markdown("""
**Intelligent Water Testing Kit Configuration System**  
*With Multi-Package Support, Bundle Selection & Direct Cost Pricing*

---

### ✨ Key Features:
- 📦 **Pre-configured Bundles** - RES, RE, COM packages ready to ship
- 🎯 **Custom Orders** - Build your own module combination
- 🔗 **Smart Bottle Sharing** - Module C FREE when ordered with Module A
- 📦 **Multi-Package Support** - Automatic splitting for orders >2 bottles
- 🖨️ **PDF Pick Lists** - Professional assembly sheets with part numbers
""")

st.divider()

# Cost toggle
col_toggle1, col_toggle2 = st.columns([3, 1])
with col_toggle2:
    st.session_state.show_costs = st.toggle("Show Cost Details", value=st.session_state.show_costs)


# ============================================================================
# SIDEBAR - SHIPPING
# ============================================================================

with st.sidebar:
    st.header("📍 Shipping Configuration")
    
    if st.button("🔄 Reset All", width="stretch"):
        st.session_state.modules_selected = {}
        st.session_state.selected_bundle = None
        st.session_state.order_type = 'bundle'
        st.session_state.shipping_address = None
        st.session_state.shipping_rate = None
        st.rerun()
    
    st.divider()
    
    st.subheader("Destination Address")
    contact_name = st.text_input("Contact Name", placeholder="John Smith")
    street = st.text_input("Street Address", placeholder="123 Main Street")
    street2 = st.text_input("Address Line 2", placeholder="Suite 100")
    
    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("City", placeholder="San Francisco")
    with col2:
        state = st.text_input("State", placeholder="CA", max_chars=2)
    
    col3, col4 = st.columns(2)
    with col3:
        zip_code = st.text_input("ZIP Code", placeholder="94102")
    with col4:
        phone = st.text_input("Phone", placeholder="4155551234")
    
    if st.button("💾 Save Address", type="primary", width="stretch"):
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
        st.markdown("**Current Address:**")
        addr = st.session_state.shipping_address
        st.caption(f"{addr['city']}, {addr['stateOrProvinceCode']} {addr['postalCode']}")
        if st.button("🗑️ Clear Address", width="stretch"):
            st.session_state.shipping_address = None
            st.session_state.shipping_rate = None
            st.rerun()


# ============================================================================
# STEP 1: ORDER TYPE SELECTION
# ============================================================================

st.header("1️⃣ Select Order Type")

order_type = st.radio(
    "How would you like to order?",
    options=['bundle', 'custom'],
    format_func=lambda x: "📦 Pre-configured Bundle (RES, RE, COM)" if x == 'bundle' else "🔧 Custom Module Selection",
    horizontal=True,
    key='order_type_radio'
)
st.session_state.order_type = order_type

st.divider()


# ============================================================================
# BUNDLE SELECTION
# ============================================================================

if st.session_state.order_type == 'bundle':
    st.subheader("📦 Select a Bundle")
    
    # Group bundles by category
    categories = {}
    for sku, bundle in BUNDLE_DEFINITIONS.items():
        cat = bundle['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((sku, bundle))
    
    # Display bundles by category
    for category, bundles in categories.items():
        st.markdown(f"**{category}**")
        
        cols = st.columns(len(bundles) if len(bundles) <= 3 else 3)
        for i, (sku, bundle) in enumerate(bundles):
            with cols[i % 3]:
                is_selected = st.session_state.selected_bundle == sku
                
                # Module short names
                module_names = [COMPONENT_LIBRARY[m]['short_name'] for m in bundle['modules']]
                has_pfas = 'module_p' in bundle['modules']
                
                if st.button(
                    f"{'✅ ' if is_selected else ''}{sku}\n{bundle['name']}\n{', '.join(module_names)}\n${bundle['price']:.0f}",
                    key=f"bundle_{sku}",
                    type="primary" if is_selected else "secondary",
                    width="stretch"
                ):
                    st.session_state.selected_bundle = sku
                    # Auto-select modules from bundle
                    st.session_state.modules_selected = {m: True for m in bundle['modules']}
                    st.session_state.shipping_rate = None
                    st.rerun()
                
                if has_pfas:
                    st.caption("⚠️ Includes PFAS")
        
        st.markdown("")
    
    # Show selected bundle details
    if st.session_state.selected_bundle:
        bundle = BUNDLE_DEFINITIONS[st.session_state.selected_bundle]
        st.success(f"**Selected: {st.session_state.selected_bundle} - {bundle['name']}**")
        st.markdown(f"_{bundle['description']}_")
        
        # List included modules
        st.markdown("**Included Modules:**")
        for mod_key in bundle['modules']:
            mod = COMPONENT_LIBRARY[mod_key]
            st.markdown(f"- {mod['short_name']}: {mod['name']} (Part: {mod['bottle']})")


# ============================================================================
# CUSTOM MODULE SELECTION
# ============================================================================

else:
    st.subheader("🔧 Custom Module Selection")
    st.markdown("Select individual test modules:")
    
    modules_to_show = ['module_a', 'module_b', 'module_c', 'module_d', 'module_p']
    
    sharing_active = (st.session_state.modules_selected.get('module_a', False) and 
                     st.session_state.modules_selected.get('module_c', False))
    
    # Module A
    with st.expander("✅ Module A: General Chemistry" if st.session_state.modules_selected.get('module_a') else "Module A: General Chemistry"):
        module_a = st.checkbox("Select Module A", key="module_a", value=st.session_state.modules_selected.get('module_a', False))
        st.session_state.modules_selected['module_a'] = module_a
        st.markdown(f"**Part:** 1300-00007 | **Bottle:** 250mL HDPE unacidified")
        st.markdown(f"**Tests:** {', '.join(COMPONENT_LIBRARY['module_a']['tests'])}")
        st.markdown(f"**Cost:** ${COMPONENT_LIBRARY['module_a']['cost']:.2f}")
    
    # Module B
    with st.expander("✅ Module B: Metals" if st.session_state.modules_selected.get('module_b') else "Module B: Metals (ICP-MS)"):
        module_b = st.checkbox("Select Module B", key="module_b", value=st.session_state.modules_selected.get('module_b', False))
        st.session_state.modules_selected['module_b'] = module_b
        st.markdown(f"**Part:** 1300-00008 | **Bottle:** 250mL HDPE pre-acidified (HNO₃)")
        st.markdown(f"**Tests:** EPA 200.8 Metals Panel")
        st.markdown(f"**Cost:** ${COMPONENT_LIBRARY['module_b']['cost']:.2f}")
    
    # Module C
    c_title = "✅ Module C: Anions 🎁 FREE" if (st.session_state.modules_selected.get('module_c') and sharing_active) else \
              "✅ Module C: Anions" if st.session_state.modules_selected.get('module_c') else "Module C: Anions/Nutrients"
    with st.expander(c_title, expanded=sharing_active):
        module_c = st.checkbox("Select Module C", key="module_c", value=st.session_state.modules_selected.get('module_c', False))
        st.session_state.modules_selected['module_c'] = module_c
        if sharing_active:
            st.success("✅ **Smart Sharing!** Uses same bottle as Module A - FREE!")
        st.markdown(f"**Part:** 1300-00007 (shared with A) | **Bottle:** 250mL HDPE")
        st.markdown(f"**Tests:** {', '.join(COMPONENT_LIBRARY['module_c']['tests'])}")
        st.markdown(f"**Cost:** {'$0.00 (FREE!)' if sharing_active else f'${COMPONENT_LIBRARY[\"module_c\"][\"cost\"]:.2f}'}")
    
    # Module D
    with st.expander("✅ Module D: Nutrients" if st.session_state.modules_selected.get('module_d') else "Module D: Nutrients (IC)"):
        module_d = st.checkbox("Select Module D", key="module_d", value=st.session_state.modules_selected.get('module_d', False))
        st.session_state.modules_selected['module_d'] = module_d
        st.markdown(f"**Part:** 1300-00009 | **Bottle:** 250mL PP pre-acidified (H₂SO₄)")
        st.markdown(f"**Tests:** EPA 300.1 Nutrients")
        st.markdown(f"**Cost:** ${COMPONENT_LIBRARY['module_d']['cost']:.2f}")
    
    # Module P
    with st.expander("✅ Module P: PFAS ⚠️" if st.session_state.modules_selected.get('module_p') else "Module P: PFAS Testing ⚠️"):
        module_p = st.checkbox("Select Module P", key="module_p", value=st.session_state.modules_selected.get('module_p', False))
        st.session_state.modules_selected['module_p'] = module_p
        if module_p:
            st.warning("⚠️ **PFAS Special Handling** - Use PFAS-free gloves (1300-00019)")
        st.markdown(f"**Part:** 1300-00010 | **Bottles:** 2× 250mL PP PFAS-certified")
        st.markdown(f"**Tests:** EPA 537.1/1633A PFAS Panel")
        st.markdown(f"**Cost:** ${COMPONENT_LIBRARY['module_p']['cost']:.2f}")
    
    # Clear bundle selection when in custom mode
    st.session_state.selected_bundle = None

st.divider()


# ============================================================================
# SHIPPING OPTIONS
# ============================================================================

st.subheader("📦 Shipping Options")

compliance = st.checkbox(
    "**Compliance Shipping** (2-Day with cooler & ice packs)",
    key="compliance_shipping",
    value=st.session_state.modules_selected.get('compliance_shipping', False)
)
st.session_state.modules_selected['compliance_shipping'] = compliance

if compliance:
    st.info("📦 Includes insulated cooler and ice packs (+5 lbs per package)")

st.divider()


# ============================================================================
# CALCULATIONS
# ============================================================================

# Get selected modules
if st.session_state.order_type == 'bundle' and st.session_state.selected_bundle:
    selected_modules = BUNDLE_DEFINITIONS[st.session_state.selected_bundle]['modules']
else:
    modules_to_show = ['module_a', 'module_b', 'module_c', 'module_d', 'module_p']
    selected_modules = [k for k in modules_to_show if st.session_state.modules_selected.get(k, False)]

if selected_modules:
    sharing_a_c = ('module_a' in selected_modules and 'module_c' in selected_modules)
    bottle_count = count_bottles(selected_modules, sharing_a_c)
    package_weight, package_count = calculate_package_weight(selected_modules, bottle_count)
    is_compliance = st.session_state.modules_selected.get('compliance_shipping', False)
    
    if is_compliance:
        display_weight = package_weight + (5.0 * package_count)
        package_weight_for_api = display_weight
    else:
        display_weight = package_weight
        package_weight_for_api = package_weight


# ============================================================================
# STEP 2: SHIPPING RATE
# ============================================================================

st.header("2️⃣ Calculate Shipping Rate")

if selected_modules:
    # Package info
    if package_count > 1:
        st.markdown(f"""
        <div class="multi-package-warning">
            <h4 style="margin-top: 0;">⚠️ Multiple Packages Required</h4>
            <p><strong>{package_count} packages</strong> needed for {bottle_count} bottles (max 2 per box)</p>
        </div>
        """, unsafe_allow_html=True)
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Bottles", bottle_count)
    with col_info2:
        st.metric("Packages", package_count)
    with col_info3:
        st.metric("Weight", f"{display_weight} lbs")
    
    has_address = st.session_state.shipping_address and 'city' in st.session_state.shipping_address
    
    if has_address:
        if st.button(f"🔄 Get FedEx Rate ({package_count} pkg)", type="primary", width="stretch"):
            with st.spinner("Contacting FedEx..."):
                service_type = get_fedex_service_type(is_compliance)
                weight_per_pkg = package_weight_for_api / package_count
                
                rate = calculate_total_shipping_cost(
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
                <p><strong>Service:</strong> {rate['service_name']} | <strong>Packages:</strong> {rate.get('package_count', 1)}</p>
                <div class="rate-display">Shipping: ${rate['total_charge']:.2f}</div>
                {f'<p style="text-align:center; color:#999; font-size:0.9rem;">Demo Mode</p>' if rate.get('demo_mode') else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("💡 Enter shipping address in sidebar to get FedEx rates")
        estimated = estimate_shipping_cost(is_compliance, package_count)
        st.caption(f"Estimated: ${estimated:.2f}")

else:
    st.warning("⚠️ Select a bundle or modules first")

st.divider()


# ============================================================================
# STEP 3: COST SUMMARY
# ============================================================================

st.header("3️⃣ Cost Summary")

if selected_modules:
    material_cost = calculate_material_cost(selected_modules, sharing_a_c, package_count)
    
    if st.session_state.shipping_rate:
        shipping_cost = st.session_state.shipping_rate['total_charge']
    else:
        shipping_cost = estimate_shipping_cost(is_compliance, package_count)
    
    # For bundles, use bundle price; for custom, calculate
    if st.session_state.order_type == 'bundle' and st.session_state.selected_bundle:
        bundle_price = BUNDLE_DEFINITIONS[st.session_state.selected_bundle]['price']
        customer_price = bundle_price + shipping_cost
        price_label = f"Bundle ({st.session_state.selected_bundle})"
    else:
        customer_price = material_cost + shipping_cost
        price_label = "Custom Order"
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("Modules", len(selected_modules))
    with col_s2:
        st.metric("Bottles", bottle_count)
    with col_s3:
        st.metric("Packages", package_count)
    
    st.markdown(f"""
    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #0066B2 0%, #3399CC 100%); 
                border-radius: 8px; color: white; margin: 1rem 0;">
        <div style="font-size: 0.9rem; opacity: 0.9;">{price_label.upper()}</div>
        <div style="font-size: 2.5rem; font-weight: bold;">${customer_price:.2f}</div>
        <div style="font-size: 0.8rem; opacity: 0.8;">includes shipping</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.show_costs:
        if st.session_state.order_type == 'bundle' and st.session_state.selected_bundle:
            st.caption(f"• Bundle Price: ${bundle_price:.2f}")
        else:
            st.caption(f"• Material: ${material_cost:.2f}")
        st.caption(f"• Shipping: ${shipping_cost:.2f}")
    
    st.markdown(f"""
    <div class="labor-note">
        <strong>ℹ️ Assembly:</strong> ~{ASSEMBLY_TIME_MINUTES * package_count} min ({package_count} pkg × {ASSEMBLY_TIME_MINUTES} min)
    </div>
    """, unsafe_allow_html=True)
    
    if sharing_a_c:
        st.success("✅ **Smart Sharing Active** - Module C uses same bottle as A")

st.divider()


# ============================================================================
# STEP 4: PICK LIST
# ============================================================================

st.header("4️⃣ Generate Pick List")

if selected_modules:
    col_p1, col_p2 = st.columns([2, 1])
    
    with col_p1:
        if st.button("📋 Generate Pick List", type="primary", width="stretch"):
            pick_list = generate_pick_list(
                selected_modules=selected_modules,
                bottle_count=bottle_count,
                package_count=package_count,
                sharing_active=sharing_a_c,
                bundle_sku=st.session_state.selected_bundle
            )
            
            st.session_state.current_pick_list = pick_list
            st.success("✅ Pick list generated!")
    
    # Display pick list if generated
    if 'current_pick_list' in st.session_state:
        pick_list = st.session_state.current_pick_list
        pick_list_text = format_pick_list_display(pick_list)
        
        st.markdown(f"<div class='pick-list'>{pick_list_text}</div>", unsafe_allow_html=True)
        
        # Download buttons
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            st.download_button(
                "📥 Download TXT",
                data=pick_list_text,
                file_name=f"KELP_PickList_{pick_list['bundle_sku'] or 'CUSTOM'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                width="stretch"
            )
        
        with col_dl2:
            # PDF generation
            order_id = st.text_input("Order ID:", placeholder="ORD-001", key="pdf_order_id")
            customer = st.text_input("Customer:", placeholder="John Smith", key="pdf_customer")
            
            if st.button("📄 Generate PDF", width="stretch"):
                pdf_bytes = generate_pick_list_pdf(pick_list, order_id, customer)
                if pdf_bytes:
                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"KELP_PickList_{pick_list['bundle_sku'] or 'CUSTOM'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        width="stretch"
                    )
                else:
                    st.error("Install reportlab: `pip install reportlab`")

else:
    st.warning("⚠️ Select modules first")

st.divider()


# ============================================================================
# STEP 5: LABELS & COMPLETE
# ============================================================================

st.header("5️⃣ Generate Labels & Complete Order")

if selected_modules and st.session_state.shipping_rate:
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        if st.button("📄 Generate FedEx Labels", type="primary", width="stretch"):
            with st.spinner(f"Generating {package_count} label(s)..."):
                labels = []
                for i in range(1, package_count + 1):
                    label = st.session_state.fedex_api.generate_label(
                        st.session_state.shipping_address,
                        package_weight_for_api / package_count,
                        get_fedex_service_type(is_compliance),
                        i, package_count
                    )
                    if label:
                        labels.append(label)
                
                if labels:
                    st.success(f"✅ {len(labels)} label(s) generated!")
                    for label in labels:
                        st.code(f"Tracking: {label['tracking_number']}")
    
    with col_b2:
        if st.button("💾 Save Order & Reset", width="stretch"):
            order = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'bundle': st.session_state.selected_bundle,
                'modules': [COMPONENT_LIBRARY[m]['short_name'] for m in selected_modules],
                'bottles': bottle_count,
                'packages': package_count,
                'price': customer_price,
            }
            st.session_state.order_history.append(order)
            
            # Reset
            st.session_state.modules_selected = {}
            st.session_state.selected_bundle = None
            st.session_state.shipping_rate = None
            if 'current_pick_list' in st.session_state:
                del st.session_state.current_pick_list
            
            st.success("✅ Order saved!")
            st.balloons()
            st.rerun()

else:
    missing = []
    if not selected_modules:
        missing.append("modules")
    if not st.session_state.shipping_rate:
        missing.append("shipping rate")
    st.info(f"💡 Complete: {', '.join(missing)}")


# ============================================================================
# ORDER HISTORY
# ============================================================================

if st.session_state.order_history:
    st.divider()
    st.header("📊 Order History")
    df = pd.DataFrame(st.session_state.order_history)
    st.dataframe(df, width="stretch")


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
---
**KELP Kit Builder Pro v5.0** | Bundles + Custom Orders | PDF Pick Lists | Feb 2026

**Part Numbers:** 1300-00007 (Anions/GenChem), 1300-00008 (Metals), 1300-00009 (Nutrients), 1300-00010 (PFAS)  
**Packaging:** 1300-00058 (Box), 1300-00027 (Generic), 1300-00028 (PFAS) | **Gloves:** 1300-00018 (Nitrile), 1300-00019 (PFAS-free)

**Bundles:** RES-001, RES-002, RES-004, RES-005, RES-006, RE-001, RE-002, COM-001, COM-002
---
""")
