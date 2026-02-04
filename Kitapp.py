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
    """
    Complete FedEx API Integration
    Handles authentication, rate calculation, label generation, and address validation
    
    UPDATED: Now supports multi-package rate calculation
    """
    
    def __init__(self):
        # Get credentials from Streamlit secrets (or set empty for demo mode)
        # IMPORTANT: FedEx no longer issues Meter Numbers for new integrations
        # Use OAuth with Client ID + Client Secret + Account Number only
        try:
            self.api_key = st.secrets.get("FEDEX_API_KEY", "")  # Client ID
            self.secret_key = st.secrets.get("FEDEX_SECRET_KEY", "")  # Client Secret
            self.account_number = st.secrets.get("FEDEX_ACCOUNT_NUMBER", "")
        except:
            # If secrets file doesn't exist at all
            self.api_key = ""
            self.secret_key = ""
            self.account_number = ""
        
        # Demo mode if no credentials (NO METER NUMBER REQUIRED)
        self.demo_mode = not all([self.api_key, self.secret_key, self.account_number])
        
        # API endpoints
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
        self.address_url = f"{self.base_url}/address/v1/addresses/resolve"
        
        # KELP origin address
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
            st.sidebar.info("""
            ℹ️ **FedEx Demo Mode**
            
            Using estimated rates. To enable live FedEx integration:
            
            1. Register at FedEx Developer Portal
            2. Get your Client ID & Client Secret
            3. Add to `.streamlit/secrets.toml`:
               - FEDEX_API_KEY (Client ID)
               - FEDEX_SECRET_KEY (Client Secret)  
               - FEDEX_ACCOUNT_NUMBER
            
            **Note:** Meter Number is NOT required for new integrations.
            """)
    
    def authenticate(self) -> bool:
        """Authenticate with FedEx and get OAuth token"""
        if self.demo_mode:
            return True
            
        if self.access_token:
            return True
        
        if self.auth_failed:
            return False
            
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            
            response = requests.post(self.auth_url, headers=headers, data=data, timeout=10)
            
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                return True
            else:
                self.auth_failed = True
                return False
                
        except Exception as e:
            self.auth_failed = True
            return False
    
    def calculate_shipping_rate(self, destination: Dict, weight_lbs: float, 
                                service_type: str = "FEDEX_GROUND",
                                is_compliance: bool = False) -> Optional[Dict]:
        """Calculate shipping rate for a SINGLE package"""
        
        # Demo mode - return estimated rates
        if self.demo_mode:
            base_rate = 50.0 if service_type == "FEDEX_2_DAY" else 12.0
            
            # Adjust for weight
            if weight_lbs > 5:
                base_rate += (weight_lbs - 5) * 2
            
            return {
                'total_charge': round(base_rate, 2),
                'service_name': 'FedEx 2Day' if service_type == "FEDEX_2_DAY" else 'FedEx Ground',
                'transit_time': '2 business days' if service_type == "FEDEX_2_DAY" else '3-5 business days',
                'delivery_date': (datetime.now()).strftime('%Y-%m-%d'),
                'demo_mode': True
            }
        
        # Real FedEx API call
        if not self.authenticate():
            return None
            
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            payload = {
                "accountNumber": {
                    "value": self.account_number
                },
                "requestedShipment": {
                    "shipper": {
                        "address": self.origin
                    },
                    "recipient": {
                        "address": destination
                    },
                    "pickupType": "USE_SCHEDULED_PICKUP",
                    "serviceType": service_type,
                    "packagingType": "YOUR_PACKAGING",
                    "rateRequestType": ["ACCOUNT"],
                    "requestedPackageLineItems": [
                        {
                            "weight": {
                                "units": "LB",
                                "value": weight_lbs
                            },
                            "dimensions": {
                                "length": 12,
                                "width": 10,
                                "height": 8,
                                "units": "IN"
                            }
                        }
                    ]
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
            st.error(f"Error calculating shipping rate: {str(e)}")
            return None
    
    def generate_label(self, destination: Dict, weight_lbs: float, 
                      service_type: str = "FEDEX_GROUND",
                      package_number: int = 1, total_packages: int = 1) -> Optional[Dict]:
        """Generate shipping label for ONE package"""
        
        # Demo mode
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
        
        # Real FedEx label generation would go here
        return None


# ============================================================================
# COMPONENT LIBRARY WITH PART NUMBERS
# ============================================================================

# Kit components master list with KELP part numbers
KIT_COMPONENTS = {
    "1300-00007": {"type": "Bottle with Label", "description": "For: Anions + Gen Chem"},
    "1300-00008": {"type": "Bottle with Label", "description": "For: Metals"},
    "1300-00009": {"type": "Bottle with Label", "description": "For: Nutrients"},
    "1300-00010": {"type": "Bottle with Label", "description": "For: PFAS"},
    "1300-00058": {"type": "Box (Kit)", "description": "Shipping Box (Home Water Safety Kit)"},
    "1300-00018": {"type": "Gloves", "description": "Gloves (Nitrile - Size L)"},
    "1300-00019": {"type": "Gloves PFAS Free", "description": "Gloves: (PFAS-free)"},
    "1300-00027": {"type": "Packaging", "description": "For bottle protection (Generic)"},
    "1300-00028": {"type": "Packaging for PFAS", "description": "For bottle protection (PFAS)"},
    "1300-00029": {"type": "Printed document", "description": 'Pre-printed "WATER SAMPLE COLLECTION INSTRUCTIONS"'},
    "1300-00030": {"type": "Printed document", "description": 'Pre-printed "COC with INSTRUCTIONS"'},
}

# Component library with pricing and specifications
COMPONENT_LIBRARY = {
    'base': {
        'name': 'Base Kit Components',
        'cost': 9.50,
        'weight_lbs': 1.5,
        'items': [
            {'part': '1300-00030', 'desc': 'Chain of Custody Form', 'qty_per_order': 1},
            {'part': '1300-00029', 'desc': 'Sampling Instructions', 'qty_per_pkg': 1},
            {'part': '1300-00018', 'desc': 'Nitrile Gloves (2 pairs)', 'qty_per_pkg': 2, 'pfas_alt': '1300-00019'},
            {'part': '1300-00027', 'desc': 'Bottle Protection (Generic)', 'qty_per_bottle': 1, 'pfas_alt': '1300-00028'},
            {'part': '1300-00058', 'desc': 'Shipping Box', 'qty_per_pkg': 1},
        ]
    },
    'module_a': {
        'name': 'Module A: General Chemistry',
        'cost': 2.50,
        'weight_lbs': 0.3,
        'bottle': '1300-00007',
        'bottle_desc': 'Bottle: For Anions + Gen Chem',
        'bottle_cost': 2.50,
        'tests': ['Alkalinity', 'Hardness', 'TDS', 'pH', 'Conductivity']
    },
    'module_b': {
        'name': 'Module B: Metals (ICP-MS)',
        'cost': 5.00,
        'weight_lbs': 0.4,
        'bottle': '1300-00008',
        'bottle_desc': 'Bottle: For Metals (Pre-acidified HNO₃)',
        'bottle_cost': 5.00,
        'preservation': 'Pre-acidified with HNO₃',
        'tests': ['EPA 200.8 Metals Panel']
    },
    'module_c': {
        'name': 'Module C: Anions/Nutrients',
        'cost': 1.50,
        'cost_shared': 0.00,
        'weight_lbs': 0.3,
        'bottle': '1300-00007',
        'bottle_desc': 'Bottle: For Anions + Gen Chem (SHARED with A)',
        'bottle_cost': 1.50,
        'bottle_cost_shared': 0.00,
        'tests': ['Chloride', 'Sulfate', 'Nitrate', 'Phosphate']
    },
    'module_d': {
        'name': 'Module D: Nutrients (IC)',
        'cost': 4.00,
        'weight_lbs': 0.5,
        'bottle': '1300-00009',
        'bottle_desc': 'Bottle: For Nutrients (Pre-acidified H₂SO₄)',
        'bottle_cost': 4.00,
        'preservation': 'Pre-acidified with H₂SO₄',
        'tests': ['EPA 300.1 Nutrients']
    },
    'module_p': {
        'name': 'Module P: PFAS Testing',
        'cost': 15.50,
        'weight_lbs': 0.8,
        'bottle': '1300-00010',
        'bottle_desc': 'Bottle: For PFAS (PFAS-certified)',
        'bottle_cost': 15.50,
        'bottles_needed': 2,
        'preservation': 'PFAS-free containers',
        'special_handling': True,
        'tests': ['EPA 537.1/1633A PFAS Panel']
    }
}

# Constants
LABOR_COST = 7.46  # 7 minutes at $63.94/hour (NOT included in price)
ASSEMBLY_TIME_MINUTES = 7  # Base assembly time per package


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_package_weight(selected_modules: List[str], bottle_count: int) -> Tuple[float, int]:
    """Calculate total package weight and number of packages needed."""
    package_count = max(1, math.ceil(bottle_count / 2))
    
    base_weight = COMPONENT_LIBRARY['base']['weight_lbs']
    module_weight = sum(
        COMPONENT_LIBRARY[m].get('weight_lbs', 0) 
        for m in selected_modules 
        if m in COMPONENT_LIBRARY
    )
    
    total_weight = (base_weight + module_weight) * package_count
    
    return round(total_weight, 2), package_count


def get_fedex_service_type(is_compliance: bool) -> str:
    """Get FedEx service type code based on compliance needs"""
    return "FEDEX_2_DAY" if is_compliance else "FEDEX_GROUND"


def count_bottles(selected_modules: List[str], sharing_active: bool) -> int:
    """Count total number of bottles needed"""
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


def calculate_material_cost(selected_modules: List[str], sharing_active: bool, 
                            package_count: int) -> float:
    """Calculate total material cost including base kits for all packages"""
    material_cost = COMPONENT_LIBRARY['base']['cost'] * package_count
    
    for module_key in selected_modules:
        if module_key == 'module_c' and sharing_active:
            material_cost += COMPONENT_LIBRARY[module_key]['cost_shared']
        elif module_key in COMPONENT_LIBRARY:
            material_cost += COMPONENT_LIBRARY[module_key]['cost']
    
    return round(material_cost, 2)


def estimate_shipping_cost(is_compliance: bool, package_count: int) -> float:
    """Estimate shipping cost when FedEx rate not available"""
    cost_per_package = 50.00 if is_compliance else 8.00
    return cost_per_package * package_count


def generate_pick_list(selected_modules: List[str], bottle_count: int, 
                       package_count: int, sharing_active: bool) -> Dict:
    """Generate comprehensive pick list for lab staff with part numbers"""
    
    has_pfas = 'module_p' in selected_modules
    
    pick_list = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'package_count': package_count,
        'bottle_count': bottle_count,
        'assembly_time_estimate': ASSEMBLY_TIME_MINUTES * package_count,
        'has_pfas': has_pfas,
        'sharing_active': sharing_active,
        'items': [],
        'special_notes': []
    }
    
    # Shipping Box
    pick_list['items'].append({
        'part': '1300-00058',
        'description': 'Shipping Box',
        'qty': package_count
    })
    
    # Bottles based on selected modules
    if 'module_a' in selected_modules or 'module_c' in selected_modules:
        pick_list['items'].append({
            'part': '1300-00007',
            'description': 'Bottle: For Anions + Gen Chem',
            'qty': 1,
            'note': 'SHARED by MOD-A and MOD-C' if sharing_active else None
        })
    
    if 'module_b' in selected_modules:
        pick_list['items'].append({
            'part': '1300-00008',
            'description': 'Bottle: For Metals',
            'qty': 1
        })
    
    if 'module_d' in selected_modules:
        pick_list['items'].append({
            'part': '1300-00009',
            'description': 'Bottle: For Nutrients',
            'qty': 1
        })
    
    if 'module_p' in selected_modules:
        pick_list['items'].append({
            'part': '1300-00010',
            'description': 'Bottle: For PFAS',
            'qty': 2,
            'note': 'Always 2 bottles for PFAS'
        })
    
    # Gloves - PFAS-free if PFAS included
    if has_pfas:
        pick_list['items'].append({
            'part': '1300-00019',
            'description': 'Gloves (PFAS-free)',
            'qty': package_count * 2,
            'note': 'PFAS order - do NOT use nitrile'
        })
    else:
        pick_list['items'].append({
            'part': '1300-00018',
            'description': 'Gloves (Nitrile)',
            'qty': package_count * 2
        })
    
    # Packaging - count non-PFAS bottles
    non_pfas_bottles = bottle_count - (2 if has_pfas else 0)
    if non_pfas_bottles > 0:
        pick_list['items'].append({
            'part': '1300-00027',
            'description': 'Packaging (Generic)',
            'qty': non_pfas_bottles
        })
    
    if has_pfas:
        pick_list['items'].append({
            'part': '1300-00028',
            'description': 'Packaging (PFAS)',
            'qty': 2
        })
    
    # Documents
    pick_list['items'].append({
        'part': '1300-00029',
        'description': 'Collection Instructions',
        'qty': package_count
    })
    
    pick_list['items'].append({
        'part': '1300-00030',
        'description': 'COC Form',
        'qty': 1
    })
    
    # Special notes
    if package_count > 1:
        pick_list['special_notes'].append(
            f"⚠️ MULTIPLE PACKAGES: Prepare {package_count} separate kits "
            f"({bottle_count} bottles total, max 2 bottles per package)"
        )
    
    if has_pfas:
        pick_list['special_notes'].append(
            "🧪 PFAS ORDER: Use PFAS-free gloves (1300-00019) and PFAS packaging (1300-00028)"
        )
    
    if sharing_active:
        pick_list['special_notes'].append(
            "✅ SMART SHARING: Module A and C share bottle 1300-00007 (1 bottle instead of 2)"
        )
    
    return pick_list


def format_pick_list_display(pick_list: Dict) -> str:
    """Format pick list as readable string for display"""
    output = []
    output.append(f"=== KELP KIT ASSEMBLY PICK LIST ===")
    output.append(f"Generated: {pick_list['timestamp']}")
    output.append(f"")
    output.append(f"📦 PACKAGES: {pick_list['package_count']}")
    output.append(f"🧪 BOTTLES: {pick_list['bottle_count']}")
    output.append(f"⏱️  ESTIMATED TIME: {pick_list['assembly_time_estimate']} minutes")
    output.append(f"")
    
    # Special notes
    if pick_list['special_notes']:
        output.append(f"⚠️  SPECIAL NOTES:")
        for note in pick_list['special_notes']:
            output.append(f"   {note}")
        output.append(f"")
    
    # Items with part numbers
    output.append(f"PICK LIST ITEMS:")
    output.append(f"{'Part Number':<14} {'Description':<35} {'Qty':>5}")
    output.append(f"{'-'*14} {'-'*35} {'-'*5}")
    
    for item in pick_list['items']:
        line = f"{item['part']:<14} {item['description']:<35} {item['qty']:>5}"
        output.append(f"☐ {line}")
        if item.get('note'):
            output.append(f"   → {item['note']}")
    
    output.append(f"")
    
    return "\n".join(output)


def generate_pick_list_pdf(pick_list: Dict, order_id: str = None, customer_name: str = None) -> bytes:
    """Generate a PDF pick list for kit assembly"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        return None
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18,
                                  spaceAfter=12, alignment=TA_CENTER, textColor=colors.HexColor('#0066B2'))
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=11,
                                     spaceAfter=6, alignment=TA_CENTER)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=12,
                                    spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#0066B2'))
    
    elements = []
    
    # Title
    elements.append(Paragraph("KELP LABORATORY SERVICES", title_style))
    elements.append(Paragraph("Kit Assembly Pick List", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Order info
    timestamp = pick_list['timestamp']
    order_info = f"Generated: {timestamp}"
    if order_id:
        order_info += f" | Order: {order_id}"
    if customer_name:
        order_info += f" | Customer: {customer_name}"
    elements.append(Paragraph(order_info, subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary
    elements.append(Paragraph("Order Summary", section_style))
    summary_data = [
        ['Total Bottles:', str(pick_list['bottle_count'])],
        ['Packages:', str(pick_list['package_count'])],
        ['A+C Sharing:', 'Yes' if pick_list['sharing_active'] else 'No'],
        ['PFAS Included:', 'Yes' if pick_list['has_pfas'] else 'No'],
        ['Est. Assembly:', f"{pick_list['assembly_time_estimate']} minutes"],
    ]
    
    summary_table = Table(summary_data, colWidths=[1.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Pick list items
    elements.append(Paragraph("Pick List Items", section_style))
    
    pick_data = [['☐', 'Part Number', 'Description', 'Qty']]
    for item in pick_list['items']:
        pick_data.append(['☐', item['part'], item['description'], str(item['qty'])])
    
    pick_table = Table(pick_data, colWidths=[0.4*inch, 1.2*inch, 3.2*inch, 0.5*inch])
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
    elements.append(Spacer(1, 0.3*inch))
    
    # Special notes
    if pick_list['special_notes']:
        elements.append(Paragraph("Special Instructions", section_style))
        for note in pick_list['special_notes']:
            elements.append(Paragraph(note, styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
    
    # Signature section
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("_" * 60, styles['Normal']))
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
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def calculate_total_shipping_cost(fedex_api: FedExAPI, destination: Dict, 
                                  weight_per_package: float, package_count: int,
                                  service_type: str, is_compliance: bool) -> Optional[Dict]:
    """Calculate total shipping cost for multiple packages"""
    total_cost = 0
    last_rate = None
    
    for pkg_num in range(package_count):
        rate = fedex_api.calculate_shipping_rate(
            destination=destination,
            weight_lbs=weight_per_package,
            service_type=service_type,
            is_compliance=is_compliance
        )
        
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
    .module-card {
        background: white; padding: 1.5rem; border-radius: 8px;
        border-left: 4px solid #0066B2; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .module-shared { border-left: 4px solid #00A86B; background: linear-gradient(90deg, rgba(0,168,107,0.05) 0%, white 100%); }
    .module-pfas { border-left: 4px solid #FF6B35; background: linear-gradient(90deg, rgba(255,107,53,0.05) 0%, white 100%); }
    .shipping-card { background: white; padding: 1.5rem; border-radius: 8px; border: 2px solid #0066B2; margin: 1rem 0; }
    .rate-display { font-size: 1.5rem; font-weight: bold; color: #00A86B; padding: 1rem; background: #f0f8f5; border-radius: 4px; text-align: center; margin-top: 1rem; }
    .multi-package-warning { background: #FFF3CD; border-left: 4px solid #FFA500; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
    .pick-list { background: #f8f9fa; padding: 1.5rem; border-radius: 8px; border: 1px solid #dee2e6; font-family: 'Courier New', monospace; font-size: 0.9rem; white-space: pre-wrap; max-height: 500px; overflow-y: auto; }
    .labor-note { background: #E7F3FF; border-left: 3px solid #0066B2; padding: 0.75rem; margin-top: 1rem; border-radius: 4px; font-size: 0.9rem; color: #0066B2; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'modules_selected' not in st.session_state:
    st.session_state.modules_selected = {}
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
*With Multi-Package Support & Direct Cost Pricing*

---

### ✨ Key Features:
- 🎯 **Bottle Sharing** - Module C FREE when ordered with Module A
- 📦 **Multi-Package Support** - Automatic splitting for orders >2 bottles
- 🚚 **Real-Time FedEx Rates** - Actual shipping costs per package
- 💰 **Direct Cost Pricing** - No markup, pay actual cost only
- 📋 **Automated Pick Lists** - Assembly instructions with part numbers
- 🖨️ **PDF Pick Lists** - Professional printable assembly sheets
- 🏷️ **Label Generation** - Automatic FedEx shipping labels
""")

st.divider()

# Show/hide cost details toggle
col_toggle1, col_toggle2 = st.columns([3, 1])
with col_toggle2:
    st.session_state.show_costs = st.toggle("Show Cost Details", value=st.session_state.show_costs)

modules_to_show = ['module_a', 'module_b', 'module_c', 'module_d', 'module_p']


# ============================================================================
# SIDEBAR - SHIPPING CONFIGURATION
# ============================================================================

with st.sidebar:
    st.header("📍 Shipping Configuration")
    
    if st.button("🔄 Reset All", width="stretch"):
        st.session_state.modules_selected = {}
        st.session_state.shipping_address = None
        st.session_state.shipping_rate = None
        st.rerun()
    
    st.divider()
    
    st.subheader("Destination Address")
    st.caption("Enter shipping address for real-time FedEx rates")
    
    contact_name = st.text_input("Contact Name", placeholder="John Smith")
    street = st.text_input("Street Address", placeholder="123 Main Street")
    street2 = st.text_input("Address Line 2 (optional)", placeholder="Suite 100")
    
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
            street_lines = [street]
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
            st.error("⚠️ Please fill in City, State, and ZIP Code")
    
    if st.session_state.shipping_address:
        st.divider()
        st.markdown("**Current Address:**")
        addr = st.session_state.shipping_address
        st.caption(f"{addr['city']}, {addr['stateOrProvinceCode']} {addr['postalCode']}")
        
        if st.button("🗑️ Clear Address", width="stretch"):
            st.session_state.shipping_address = None
            st.session_state.shipping_rate = None
            st.rerun()
    
    st.divider()
    
    if st.session_state.modules_selected:
        selected_count = sum(1 for k, v in st.session_state.modules_selected.items() 
                           if v and k in modules_to_show)
        
        st.markdown("**Quick Stats:**")
        st.metric("Modules Selected", selected_count)
        
        selected_modules = [k for k in modules_to_show 
                          if st.session_state.modules_selected.get(k, False)]
        if selected_modules:
            sharing_active = ('module_a' in selected_modules and 
                            'module_c' in selected_modules)
            bottles = count_bottles(selected_modules, sharing_active)
            _, packages = calculate_package_weight(selected_modules, bottles)
            
            st.metric("Bottles", bottles)
            st.metric("Packages", packages)
            
            if packages > 1:
                st.warning(f"⚠️ {packages} packages needed")


# ============================================================================
# MAIN CONTENT - MODULE SELECTION
# ============================================================================

col_modules, col_summary = st.columns([2, 1])

with col_modules:
    st.header("1️⃣ Select Test Modules")
    
    st.markdown("""
    Click on each module to expand and view details. Smart sharing automatically 
    applies when Module A and Module C are both selected.
    """)
    
    st.divider()
    
    sharing_active = (st.session_state.modules_selected.get('module_a', False) and 
                     st.session_state.modules_selected.get('module_c', False))
    
    # Module A
    with st.expander("✅ Module A: General Chemistry" if st.session_state.modules_selected.get('module_a', False) else "Module A: General Chemistry", expanded=False):
        module_a = st.checkbox("Select Module A", key="module_a", value=st.session_state.modules_selected.get('module_a', False))
        st.session_state.modules_selected['module_a'] = module_a
        
        st.markdown("---")
        col_a1, col_a2 = st.columns([1, 2])
        with col_a1:
            st.markdown("**Part Number:**")
            st.markdown("**Bottle Type:**")
            st.markdown("**Tests:**")
            st.markdown("**Cost:**")
        with col_a2:
            st.markdown("1300-00007")
            st.markdown("250mL HDPE unacidified")
            st.markdown("Alkalinity, Hardness, TDS, pH, Conductivity")
            st.markdown(f"<span style='color: #00A86B; font-weight: bold;'>${COMPONENT_LIBRARY['module_a']['cost']:.2f}</span>", unsafe_allow_html=True)
    
    # Module B
    with st.expander("✅ Module B: Metals (ICP-MS)" if st.session_state.modules_selected.get('module_b', False) else "Module B: Metals (ICP-MS)", expanded=False):
        module_b = st.checkbox("Select Module B", key="module_b", value=st.session_state.modules_selected.get('module_b', False))
        st.session_state.modules_selected['module_b'] = module_b
        
        st.markdown("---")
        col_b1, col_b2 = st.columns([1, 2])
        with col_b1:
            st.markdown("**Part Number:**")
            st.markdown("**Bottle Type:**")
            st.markdown("**Preservation:**")
            st.markdown("**Tests:**")
            st.markdown("**Cost:**")
        with col_b2:
            st.markdown("1300-00008")
            st.markdown("250mL HDPE pre-acidified")
            st.markdown("HNO₃ (Pre-Preserved) 🧪")
            st.markdown("EPA 200.8 Metals Panel")
            st.markdown(f"<span style='color: #00A86B; font-weight: bold;'>${COMPONENT_LIBRARY['module_b']['cost']:.2f}</span>", unsafe_allow_html=True)
    
    # Module C
    module_c_title = "✅ Module C: Anions/Nutrients" if st.session_state.modules_selected.get('module_c', False) else "Module C: Anions/Nutrients"
    if sharing_active:
        module_c_title += " 🎁 FREE (SHARED)"
    
    with st.expander(module_c_title, expanded=sharing_active):
        module_c = st.checkbox("Select Module C", key="module_c", value=st.session_state.modules_selected.get('module_c', False))
        st.session_state.modules_selected['module_c'] = module_c
        
        if sharing_active:
            st.success("✅ **Smart Sharing Active!** Module C uses the same bottle as Module A - FREE!")
        
        st.markdown("---")
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            st.markdown("**Part Number:**")
            st.markdown("**Bottle Type:**")
            st.markdown("**Tests:**")
            st.markdown("**Cost:**")
        with col_c2:
            st.markdown("1300-00007 (shared)")
            if sharing_active:
                st.markdown("SHARED with Module A 🔗")
            else:
                st.markdown("250mL HDPE unacidified")
            st.markdown("Chloride, Sulfate, Nitrate, Phosphate")
            if sharing_active:
                st.markdown("<span style='color: #00A86B; font-weight: bold;'>$0.00 (FREE!)</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color: #00A86B; font-weight: bold;'>${COMPONENT_LIBRARY['module_c']['cost']:.2f}</span>", unsafe_allow_html=True)
    
    # Module D
    with st.expander("✅ Module D: Nutrients (IC)" if st.session_state.modules_selected.get('module_d', False) else "Module D: Nutrients (IC)", expanded=False):
        module_d = st.checkbox("Select Module D", key="module_d", value=st.session_state.modules_selected.get('module_d', False))
        st.session_state.modules_selected['module_d'] = module_d
        
        st.markdown("---")
        col_d1, col_d2 = st.columns([1, 2])
        with col_d1:
            st.markdown("**Part Number:**")
            st.markdown("**Bottle Type:**")
            st.markdown("**Preservation:**")
            st.markdown("**Tests:**")
            st.markdown("**Cost:**")
        with col_d2:
            st.markdown("1300-00009")
            st.markdown("250mL PP pre-acidified")
            st.markdown("H₂SO₄ (Pre-Preserved) 🧪")
            st.markdown("EPA 300.1 Nutrients")
            st.markdown(f"<span style='color: #00A86B; font-weight: bold;'>${COMPONENT_LIBRARY['module_d']['cost']:.2f}</span>", unsafe_allow_html=True)
    
    # Module P
    with st.expander("✅ Module P: PFAS Testing ⚠️" if st.session_state.modules_selected.get('module_p', False) else "Module P: PFAS Testing ⚠️", expanded=False):
        module_p = st.checkbox("Select Module P", key="module_p", value=st.session_state.modules_selected.get('module_p', False))
        st.session_state.modules_selected['module_p'] = module_p
        
        if module_p:
            st.warning("⚠️ **PFAS Special Handling Required**\nUse PFAS-free gloves (1300-00019) and certified containers")
        
        st.markdown("---")
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            st.markdown("**Part Number:**")
            st.markdown("**Bottle Type:**")
            st.markdown("**Bottles Needed:**")
            st.markdown("**Tests:**")
            st.markdown("**Cost:**")
        with col_p2:
            st.markdown("1300-00010")
            st.markdown("250mL PP PFAS-certified")
            st.markdown("**2 bottles** 🧪🧪")
            st.markdown("EPA 537.1/1633A PFAS Panel")
            st.markdown(f"<span style='color: #FF6B35; font-weight: bold;'>${COMPONENT_LIBRARY['module_p']['cost']:.2f}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # Compliance shipping option
    st.subheader("📦 Shipping Options")
    
    compliance = st.checkbox(
        "**Compliance Shipping** (2-Day with cooler & ice packs)",
        key="compliance_shipping",
        value=st.session_state.modules_selected.get('compliance_shipping', False)
    )
    st.session_state.modules_selected['compliance_shipping'] = compliance
    
    if compliance:
        st.info("📦 Includes insulated cooler and ice packs for temperature-sensitive samples (+5 lbs per package)")


# ============================================================================
# CALCULATE SHIPPING RATE
# ============================================================================

st.header("2️⃣ Calculate Shipping Rate")

selected_modules = [k for k in modules_to_show if st.session_state.modules_selected.get(k, False)]

if selected_modules:
    sharing_a_c = (st.session_state.modules_selected.get('module_a', False) and 
                   st.session_state.modules_selected.get('module_c', False))
    bottle_count = count_bottles(selected_modules, sharing_a_c)
    package_weight, package_count = calculate_package_weight(selected_modules, bottle_count)
    is_compliance = st.session_state.modules_selected.get('compliance_shipping', False)
    
    if is_compliance:
        compliance_weight_per_pkg = 5.0
        total_compliance_weight = compliance_weight_per_pkg * package_count
        display_weight = package_weight + total_compliance_weight
        package_weight_for_api = display_weight
    else:
        display_weight = package_weight
        package_weight_for_api = package_weight
    
    if package_count > 1:
        st.markdown(f"""
        <div class="multi-package-warning">
            <h3 style="margin-top: 0;">⚠️ Multiple Packages Required</h3>
            <p><strong>{package_count} packages</strong> needed for {bottle_count} bottles</p>
            <p><em>KELP kit boxes can hold maximum 2 bottles per package</em></p>
        </div>
        """, unsafe_allow_html=True)
    
    st.info(f"""
    📦 **Package Details:**
    - Weight: **{display_weight} lbs**
    - Bottles: {bottle_count}
    - Packages: {package_count}
    {f'- Includes cooler & ice' if is_compliance else ''}
    """)
    
    has_address = (st.session_state.shipping_address and 
                   'city' in st.session_state.shipping_address)
    
    if has_address:
        button_text = f"🔄 Get FedEx Rate for {package_count} Package{'s' if package_count > 1 else ''}"
        
        if st.button(button_text, type="primary", width="stretch"):
            with st.spinner(f"Contacting FedEx API..."):
                service_type = get_fedex_service_type(is_compliance)
                weight_per_package = package_weight_for_api / package_count
                
                combined_rate = calculate_total_shipping_cost(
                    fedex_api=st.session_state.fedex_api,
                    destination=st.session_state.shipping_address,
                    weight_per_package=weight_per_package,
                    package_count=package_count,
                    service_type=service_type,
                    is_compliance=is_compliance
                )
                
                if combined_rate:
                    st.session_state.shipping_rate = combined_rate
                    st.success("✅ Rate calculated!")
                    st.rerun()
        
        if st.session_state.shipping_rate:
            rate = st.session_state.shipping_rate
            pkg_count = rate.get('package_count', 1)
            
            st.markdown(f"""
            <div class="shipping-card">
                <h3>📍 Shipping Details</h3>
                <p><strong>Service:</strong> {rate['service_name']}</p>
                <p><strong>Packages:</strong> {pkg_count}</p>
                <p><strong>Destination:</strong> {st.session_state.shipping_address['city']}, {st.session_state.shipping_address['stateOrProvinceCode']}</p>
                <div class="rate-display">
                    Total Shipping: ${rate['total_charge']:.2f}
                </div>
                {f'<p style="text-align: center; color: #999;">Demo Mode</p>' if rate.get('demo_mode') else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("💡 **Enter shipping address in sidebar** to get real-time FedEx rates")
        estimated_cost = estimate_shipping_cost(is_compliance, package_count)
        st.caption(f"Estimated shipping: ${estimated_cost:.2f}")

else:
    st.warning("⚠️ Please select at least one test module")

st.divider()


# ============================================================================
# COST SUMMARY (Right Column)
# ============================================================================

with col_summary:
    st.header("💰 Cost Summary")
    
    if selected_modules:
        material_cost = calculate_material_cost(selected_modules, sharing_a_c, package_count)
        
        if st.session_state.shipping_rate:
            shipping_cost = st.session_state.shipping_rate['total_charge']
        else:
            shipping_cost = estimate_shipping_cost(is_compliance, package_count)
        
        total_cost = material_cost + shipping_cost
        customer_price = total_cost
        total_labor_minutes = ASSEMBLY_TIME_MINUTES * package_count
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Modules", len(selected_modules))
            st.metric("Bottles", bottle_count)
        with col_m2:
            st.metric("Packages", package_count)
        
        st.divider()
        
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #0066B2 0%, #3399CC 100%); 
                    border-radius: 8px; color: white; margin: 1rem 0;">
            <div style="font-size: 0.9rem; opacity: 0.9;">CUSTOMER PRICE</div>
            <div style="font-size: 2.5rem; font-weight: bold;">${customer_price:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.show_costs:
            st.caption(f"• Material: ${material_cost:.2f}")
            st.caption(f"• Shipping: ${shipping_cost:.2f}")
        
        st.markdown(f"""
        <div class="labor-note">
            <strong>ℹ️ Assembly:</strong> ~{total_labor_minutes} min
            <br/><em>Labor not included in price</em>
        </div>
        """, unsafe_allow_html=True)
        
        if sharing_a_c:
            st.success("✅ **Smart Sharing Active!**")
    else:
        st.info("Select modules to see cost summary")


# ============================================================================
# GENERATE PICK LIST
# ============================================================================

st.header("3️⃣ Generate Pick List")

if selected_modules:
    col_pick1, col_pick2 = st.columns([2, 1])
    
    with col_pick1:
        if st.button("📋 Generate Assembly Pick List", type="primary", width="stretch"):
            pick_list = generate_pick_list(
                selected_modules=selected_modules,
                bottle_count=bottle_count,
                package_count=package_count,
                sharing_active=sharing_a_c
            )
            
            pick_list_text = format_pick_list_display(pick_list)
            
            st.success("✅ Pick list generated!")
            
            st.markdown(f"""
            <div class="pick-list">
{pick_list_text}
            </div>
            """, unsafe_allow_html=True)
            
            # Text download
            st.download_button(
                label="📥 Download Pick List (TXT)",
                data=pick_list_text,
                file_name=f"KELP_PickList_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                width="stretch"
            )
            
            # PDF download
            st.subheader("🖨️ Print PDF Pick List")
            order_id = st.text_input("Order ID (optional):", placeholder="ORD-2024-001")
            customer_name = st.text_input("Customer Name (optional):", placeholder="John Smith")
            
            if st.button("📄 Generate PDF", width="stretch"):
                try:
                    pdf_bytes = generate_pick_list_pdf(pick_list, order_id, customer_name)
                    if pdf_bytes:
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_bytes,
                            file_name=f"KELP_PickList_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            width="stretch"
                        )
                        st.success("✅ PDF generated!")
                    else:
                        st.error("Install reportlab: `pip install reportlab`")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            
            if package_count > 1:
                st.info(f"""
                **📦 Multi-Package Assembly Notes:**
                - Prepare {package_count} separate base kits
                - Distribute {bottle_count} bottles across packages
                - Each package needs its own shipping label
                """)

else:
    st.warning("⚠️ Select modules to generate pick list")

st.divider()


# ============================================================================
# GENERATE SHIPPING LABELS
# ============================================================================

st.header("4️⃣ Generate Shipping Labels")

if st.session_state.shipping_address and selected_modules and st.session_state.shipping_rate:
    
    if st.button("📄 Generate FedEx Shipping Labels", type="primary", width="stretch"):
        with st.spinner(f"Generating {package_count} shipping label{'s' if package_count > 1 else ''}..."):
            
            service_type = get_fedex_service_type(is_compliance)
            weight_per_package = package_weight_for_api / package_count
            
            labels = []
            for pkg_num in range(1, package_count + 1):
                label = st.session_state.fedex_api.generate_label(
                    destination=st.session_state.shipping_address,
                    weight_lbs=weight_per_package,
                    service_type=service_type,
                    package_number=pkg_num,
                    total_packages=package_count
                )
                
                if label:
                    labels.append(label)
            
            if labels:
                st.success(f"✅ Generated {len(labels)} shipping label{'s' if len(labels) > 1 else ''}!")
                
                for i, label in enumerate(labels, 1):
                    with st.expander(f"📦 Package {i} of {package_count}", expanded=(package_count == 1)):
                        st.markdown(f"**Tracking:** `{label['tracking_number']}`")
                        if label.get('demo_mode'):
                            st.info("🎭 Demo Mode - Sample tracking number")

else:
    missing = []
    if not st.session_state.shipping_address:
        missing.append("shipping address")
    if not selected_modules:
        missing.append("test modules")
    if not st.session_state.shipping_rate:
        missing.append("shipping rate")
    
    st.info(f"💡 Complete these steps first: {', '.join(missing)}")

st.divider()


# ============================================================================
# COMPLETE ORDER
# ============================================================================

st.header("5️⃣ Complete Order")

if selected_modules and st.session_state.shipping_rate:
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("💾 Save Order & Start New", type="primary", width="stretch"):
            order = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'modules': selected_modules,
                'bottles': bottle_count,
                'packages': package_count,
                'sharing_active': sharing_a_c,
                'customer_price': customer_price,
            }
            
            st.session_state.order_history.append(order)
            st.session_state.modules_selected = {}
            st.session_state.shipping_address = None
            st.session_state.shipping_rate = None
            
            st.success("✅ Order saved!")
            st.balloons()
            st.rerun()
    
    with col_btn2:
        if st.button("🔄 Reset (Don't Save)", width="stretch"):
            st.session_state.modules_selected = {}
            st.session_state.shipping_address = None
            st.session_state.shipping_rate = None
            st.rerun()

else:
    st.info("💡 Complete module selection and shipping calculation to finalize order")


# ============================================================================
# ORDER HISTORY
# ============================================================================

if st.session_state.order_history:
    st.divider()
    st.header("📊 Order History")
    
    history_df = pd.DataFrame(st.session_state.order_history)
    st.metric("Total Orders", len(history_df))
    
    with st.expander("📋 View Order Details"):
        st.dataframe(history_df, width="stretch")


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
---
**KELP Smart Kit Builder Pro v4.0** | Part Number Integration | PDF Pick Lists | February 2026  

**Part Numbers:**
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
