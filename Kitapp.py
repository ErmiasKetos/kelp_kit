#!/usr/bin/env python3
"""
KELP Smart Kit Builder - COMPLETE Enhanced Streamlit Application
With FedEx API Integration for Dynamic Shipping & Label Generation

Features:
- Real-time FedEx rate calculation based on destination
- Automatic shipping label generation  
- Address validation
- Tracking number assignment
- Smart bottle sharing (A+C modules)
- Pick list generation
- Order history export
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import requests
from typing import Dict, Optional, Tuple, List
import base64

# Page configuration
st.set_page_config(
    page_title="KELP Kit Builder Pro",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# FEDEX API INTEGRATION CLASS
# ============================================================================

class FedExAPI:
    """
    Complete FedEx API Integration
    Handles authentication, rate calculation, label generation, and address validation
    """
    
    def __init__(self):
        # Get credentials from Streamlit secrets (or set empty for demo mode)
        try:
            self.api_key = st.secrets.get("FEDEX_API_KEY", "")
            self.secret_key = st.secrets.get("FEDEX_SECRET_KEY", "")
            self.account_number = st.secrets.get("FEDEX_ACCOUNT_NUMBER", "")
            self.meter_number = st.secrets.get("FEDEX_METER_NUMBER", "")
        except:
            # If secrets file doesn't exist at all
            self.api_key = ""
            self.secret_key = ""
            self.account_number = ""
            self.meter_number = ""
        
        # Demo mode if no credentials
        self.demo_mode = not all([self.api_key, self.secret_key, self.account_number, self.meter_number])
        
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
            st.sidebar.info("ℹ️ **FedEx Demo Mode**\n\nUsing estimated rates. Add credentials to `.streamlit/secrets.toml` for live FedEx integration.")
    
    def authenticate(self) -> bool:
        """Authenticate with FedEx and get OAuth token"""
        if self.demo_mode:
            return True
            
        try:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            
            response = requests.post(
                self.auth_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.auth_failed = False
                return True
            elif response.status_code == 403:
                # Invalid credentials - switch to demo mode
                st.warning("⚠️ **FedEx credentials invalid** - Switching to Demo Mode\n\nPlease check your API credentials in `.streamlit/secrets.toml`")
                self.demo_mode = True
                self.auth_failed = True
                return False
            else:
                st.warning(f"⚠️ **FedEx authentication failed** ({response.status_code}) - Using Demo Mode\n\nUsing estimated rates instead of live FedEx rates.")
                self.demo_mode = True
                self.auth_failed = True
                return False
                
        except Exception as e:
            st.warning(f"⚠️ **Cannot connect to FedEx** - Using Demo Mode\n\nError: {str(e)}\n\nUsing estimated rates.")
            self.demo_mode = True
            self.auth_failed = True
            return False
    
    def validate_address(self, address: Dict) -> Tuple[bool, Optional[Dict]]:
        """Validate address with FedEx"""
        if self.demo_mode:
            return True, address
            
        if not self.access_token:
            if not self.authenticate():
                return True, address  # Proceed anyway
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "addressesToValidate": [{
                    "address": address
                }]
            }
            
            response = requests.post(
                self.address_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("output", {}).get("resolvedAddresses"):
                    validated = data["output"]["resolvedAddresses"][0]
                    return True, validated.get("resolvedAddress", address)
            
            return True, address  # Use original if validation fails
            
        except Exception as e:
            st.warning(f"⚠️ Address validation unavailable: {str(e)}")
            return True, address
    
    def calculate_shipping_rate(
        self,
        destination: Dict,
        weight_lbs: float,
        service_type: str = "FEDEX_GROUND",
        is_compliance: bool = False
    ) -> Optional[Dict]:
        """Calculate real-time shipping rate from FedEx"""
        
        # Adjust weight for compliance (cooler + ice)
        if is_compliance:
            weight_lbs += 5.0
        
        # Demo mode: return estimated rates
        if self.demo_mode:
            return self._get_demo_rate(destination, weight_lbs, service_type, is_compliance)
        
        # Real FedEx API call
        if not self.access_token:
            if not self.authenticate():
                return self._get_demo_rate(destination, weight_lbs, service_type, is_compliance)
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
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
                    }]
                }
            }
            
            response = requests.post(
                self.rate_url,
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("output", {}).get("rateReplyDetails"):
                    rate_detail = data["output"]["rateReplyDetails"][0]
                    
                    # Extract total charge
                    total_charge = 0
                    for charge in rate_detail.get("ratedShipmentDetails", []):
                        if charge.get("rateType") == "ACCOUNT":
                            total_charge = float(charge.get("totalNetCharge", 0))
                            break
                    
                    return {
                        "service_type": rate_detail.get("serviceType"),
                        "service_name": rate_detail.get("serviceName", service_type),
                        "total_charge": total_charge,
                        "currency": "USD",
                        "delivery_date": rate_detail.get("deliveryTimestamp"),
                        "transit_time": rate_detail.get("transitTime", "N/A")
                    }
            
            # Fallback to demo rate if API fails
            return self._get_demo_rate(destination, weight_lbs, service_type, is_compliance)
            
        except Exception as e:
            st.warning(f"⚠️ Using estimated rate: {str(e)}")
            return self._get_demo_rate(destination, weight_lbs, service_type, is_compliance)
    
    def _get_demo_rate(self, destination: Dict, weight_lbs: float, service_type: str, is_compliance: bool) -> Dict:
        """Generate estimated shipping rate (demo mode or fallback)"""
        
        # Base rate by weight
        if weight_lbs <= 3:
            base_rate = 8.00
        elif weight_lbs <= 5:
            base_rate = 12.00
        elif weight_lbs <= 10:
            base_rate = 18.00
        else:
            base_rate = 25.00
        
        # Adjust for service type
        if "2_DAY" in service_type or is_compliance:
            base_rate *= 3.5  # 2-day is ~3.5x ground
        
        # Adjust for destination (rough estimates)
        state = destination.get("stateOrProvinceCode", "CA")
        
        # Distance multipliers
        west_coast = ["CA", "OR", "WA", "NV", "AZ"]
        mountain = ["UT", "CO", "NM", "ID", "MT", "WY"]
        
        if state in west_coast:
            multiplier = 1.0
        elif state in mountain:
            multiplier = 1.3
        else:
            multiplier = 1.6  # East coast / central
        
        total_charge = base_rate * multiplier
        
        # Transit time estimate
        if "2_DAY" in service_type:
            transit = "2 business days"
        elif state == "CA":
            transit = "1-2 business days"
        elif state in west_coast:
            transit = "2-3 business days"
        elif state in mountain:
            transit = "3-4 business days"
        else:
            transit = "4-5 business days"
        
        return {
            "service_type": service_type,
            "service_name": "FedEx Ground (Estimated)" if "GROUND" in service_type else "FedEx 2-Day (Estimated)",
            "total_charge": round(total_charge, 2),
            "currency": "USD",
            "delivery_date": None,
            "transit_time": transit
        }
    
    def generate_shipping_label(
        self,
        order_id: str,
        destination: Dict,
        weight_lbs: float,
        service_type: str = "FEDEX_GROUND",
        is_compliance: bool = False,
        reference_id: str = ""
    ) -> Optional[Dict]:
        """Generate FedEx shipping label with tracking"""
        
        # Adjust weight
        if is_compliance:
            weight_lbs += 5.0
        
        # Demo mode: return mock label
        if self.demo_mode:
            return {
                "tracking_number": f"DEMO{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "label_url": "https://www.fedex.com/content/dam/fedex/us-united-states/shipping/images/2022/Q3/sample-fedex-express-shipping-label-domestic.png",
                "master_tracking_number": f"DEMO{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "service_type": service_type,
                "shipment_date": datetime.now().strftime("%Y-%m-%d"),
                "demo_mode": True
            }
        
        # Real FedEx API call
        if not self.access_token:
            if not self.authenticate():
                return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "labelResponseOptions": "URL_ONLY",
                "requestedShipment": {
                    "shipper": {
                        "contact": {
                            "personName": st.secrets.get("LAB_CONTACT", "Lab Manager"),
                            "phoneNumber": st.secrets.get("LAB_PHONE", "408-555-1234"),
                            "companyName": st.secrets.get("LAB_NAME", "KETOS Environmental Lab Platform")
                        },
                        "address": self.origin
                    },
                    "recipients": [{
                        "contact": {
                            "personName": destination.get("contact_name", ""),
                            "phoneNumber": destination.get("phone", ""),
                            "companyName": destination.get("company", "")
                        },
                        "address": {
                            "streetLines": destination["streetLines"],
                            "city": destination["city"],
                            "stateOrProvinceCode": destination["stateOrProvinceCode"],
                            "postalCode": destination["postalCode"],
                            "countryCode": destination.get("countryCode", "US")
                        }
                    }],
                    "shipDatestamp": datetime.now().strftime("%Y-%m-%d"),
                    "serviceType": service_type,
                    "packagingType": "YOUR_PACKAGING",
                    "pickupType": "USE_SCHEDULED_PICKUP",
                    "blockInsightVisibility": False,
                    "shippingChargesPayment": {"paymentType": "SENDER"},
                    "labelSpecification": {
                        "imageType": "PDF",
                        "labelStockType": "PAPER_4X6"
                    },
                    "requestedPackageLineItems": [{
                        "weight": {
                            "units": "LB",
                            "value": weight_lbs
                        },
                        "dimensions": {
                            "length": 12,
                            "width": 10,
                            "height": 8,
                            "units": "IN"
                        },
                        "customerReferences": [{
                            "customerReferenceType": "CUSTOMER_REFERENCE",
                            "value": f"KELP-{order_id}"
                        }]
                    }]
                },
                "accountNumber": {"value": self.account_number}
            }
            
            response = requests.post(
                self.ship_url,
                json=payload,
                headers=headers,
                timeout=20
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("output", {}).get("transactionShipments"):
                    shipment = data["output"]["transactionShipments"][0]
                    package = shipment.get("pieceResponses", [{}])[0]
                    
                    return {
                        "tracking_number": package.get("trackingNumber"),
                        "label_url": package.get("packageDocuments", [{}])[0].get("url"),
                        "master_tracking_number": shipment.get("masterTrackingNumber"),
                        "service_type": shipment.get("serviceType"),
                        "shipment_date": shipment.get("shipDatestamp")
                    }
            
            st.error(f"❌ Label generation failed: {response.status_code}")
            return None
            
        except Exception as e:
            st.error(f"❌ Label generation error: {str(e)}")
            return None

# ============================================================================
# COMPONENT LIBRARY & CONSTANTS
# ============================================================================

COMPONENT_LIBRARY = {
    'base': {
        'name': 'BASE COMPONENTS',
        'description': 'Included in every kit',
        'cost': 9.50,
        'weight_lbs': 1.5,
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
        'weight_lbs': 0.3,
        'items': [
            {'item': '250mL HDPE unacidified (for Gen Chem + Anions)', 'qty': 1, 'cost': 2.50, 'pn': 'Bottle_HDPE_Unacid', 'location': 'Shelf B1'},
        ],
        'color': '#4472C4',
        'tests': ['Alkalinity', 'Total Hardness', 'Calcium Hardness', 'Turbidity', 'TDS'],
        'preservation': 'Unacidified',
        'can_share': True,
        'shares_with': 'Module C (Anions)'
    },
    'module_b': {
        'name': 'MODULE B: Metals (EPA 200.8)',
        'description': 'Lead, Copper, Arsenic, Chromium, Zinc, Iron, Manganese',
        'cost': 5.00,
        'weight_lbs': 0.4,
        'items': [
            {'item': '250mL HDPE acidified (HNO₃) - For Metals only', 'qty': 1, 'cost': 5.00, 'pn': 'Bottle_HDPE_HNO3', 'location': 'Shelf B2'},
        ],
        'color': '#70AD47',
        'tests': ['Lead (Pb)', 'Copper (Cu)', 'Arsenic (As)', 'Chromium (Cr)', 'Zinc (Zn)', 'Iron (Fe)', 'Manganese (Mn)'],
        'preservation': 'Acidified with HNO₃',
        'can_share': False
    },
    'module_c': {
        'name': 'MODULE C: Anions (EPA 300.1)',
        'description': 'Chloride, Sulfate, Nitrate, Fluoride',
        'cost': 1.50,
        'weight_lbs': 0.3,
        'items': [
            {'item': '250mL HDPE unacidified (for Anions + Gen Chem)', 'qty': 1, 'cost': 1.50, 'pn': 'Bottle_HDPE_Unacid', 'location': 'Shelf B1'},
        ],
        'color': '#FFC000',
        'tests': ['Chloride (Cl⁻)', 'Sulfate (SO₄²⁻)', 'Nitrate (NO₃⁻)', 'Fluoride (F⁻)'],
        'preservation': 'Unacidified',
        'can_share': True,
        'shares_with': 'Module A (Gen Chem)'
    },
    'module_d': {
        'name': 'MODULE D: Nutrients',
        'description': 'Ammonia, TKN, Nitrite, Phosphate',
        'cost': 4.00,
        'weight_lbs': 0.5,
        'items': [
            {'item': '250mL PP acidified (H₂SO₄) - For Nutrients', 'qty': 1, 'cost': 4.00, 'pn': 'Bottle_PP_H2SO4', 'location': 'Shelf B4'},
        ],
        'color': '#5B9BD5',
        'tests': ['Ammonia (NH₃)', 'Total Kjeldahl Nitrogen (TKN)', 'Nitrite (NO₂⁻)', 'Phosphate (PO₄³⁻)'],
        'preservation': 'Acidified with H₂SO₄',
        'can_share': False
    },
    'module_p': {
        'name': 'MODULE P: PFAS (EPA 537.1 / 1633)',
        'description': 'PFAS panels (3, 14, 18, 25, or 40-compound)',
        'cost': 15.50,
        'weight_lbs': 0.8,
        'items': [
            {'item': '250mL PP PFAS-certified bottle', 'qty': 2, 'cost': 10.00, 'pn': 'Bottle_PP_PFAS', 'location': 'Shelf C1'},
            {'item': 'PP caps w/ PE liners', 'qty': 2, 'cost': 3.00, 'pn': 'Cap_PFAS', 'location': 'Shelf C2'},
            {'item': 'PFAS-free labels', 'qty': 2, 'cost': 1.00, 'pn': 'Label_PFAS', 'location': 'Shelf C3'},
            {'item': 'PFAS-free gloves (UPGRADE)', 'qty': 1, 'cost': 1.50, 'pn': 'PPE_PFAS', 'location': 'Shelf E1'},
        ],
        'color': '#E7E6E6',
        'tests': ['PFAS-3', 'PFAS-14', 'PFAS-18', 'PFAS-25', 'PFAS-40'],
        'special_warning': '⚠️ PFAS KIT - Use ONLY PFAS-free materials!',
        'preservation': 'PFAS-certified (unacidified)',
        'can_share': False
    },
    'module_m': {
        'name': 'MODULE M: Microbiology',
        'description': 'Total Coliform, E. coli',
        'cost': 2.50,
        'weight_lbs': 0.2,
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

LABOR_COST = 7.46  # 7 minutes at $63.94/hour
MARKUP_FACTOR = 1.4  # 40% markup = 28.6% profit margin

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_package_weight(selected_modules: List[str]) -> float:
    """Calculate total package weight in pounds"""
    weight = COMPONENT_LIBRARY['base']['weight_lbs']
    
    for module_key in selected_modules:
        if module_key in COMPONENT_LIBRARY:
            weight += COMPONENT_LIBRARY[module_key].get('weight_lbs', 0)
    
    return round(weight, 2)


def get_fedex_service_type(is_compliance: bool) -> str:
    """Get FedEx service type code"""
    return "FEDEX_2_DAY" if is_compliance else "FEDEX_GROUND"


def count_bottles(selected_modules: List[str], sharing_active: bool) -> int:
    """Count total number of bottles"""
    bottles = 0
    
    for module_key in selected_modules:
        if module_key == 'module_a':
            bottles += 1
        elif module_key == 'module_b':
            bottles += 1
        elif module_key == 'module_c':
            if not sharing_active:  # Only count if NOT sharing
                bottles += 1
        elif module_key == 'module_d':
            bottles += 1
        elif module_key == 'module_p':
            bottles += 2  # PFAS always needs 2 bottles
        elif module_key == 'module_m':
            bottles += 1
    
    return bottles


def generate_pick_list(
    order_id: str,
    customer_name: str,
    project_name: str,
    selected_modules: List[str],
    sharing_active: bool,
    is_compliance: bool
) -> pd.DataFrame:
    """Generate pick list dataframe"""
    
    items = []
    
    # Add base components (skip standard gloves if PFAS selected)
    has_pfas = 'module_p' in selected_modules
    for item in COMPONENT_LIBRARY['base']['items']:
        if has_pfas and item['item'] == 'Nitrile Gloves (pairs)':
            continue  # Skip standard gloves, PFAS kit has upgraded gloves
        items.append(item.copy())
    
    # Add module-specific items
    for module_key in selected_modules:
        if module_key in COMPONENT_LIBRARY:
            module = COMPONENT_LIBRARY[module_key]
            
            # Skip Module C bottle if sharing with Module A
            if module_key == 'module_c' and sharing_active:
                items.append({
                    'item': '⚠️ SHARED BOTTLE: Anions use SAME bottle as Gen Chem',
                    'qty': 0,
                    'cost': 0,
                    'pn': 'N/A',
                    'location': 'N/A'
                })
                continue
            
            # Add all items for this module
            for item in module.get('items', []):
                items.append(item.copy())
    
    # Add compliance shipping items
    if is_compliance:
        items.extend([
            {'item': 'Cooler Bag (12L insulated)', 'qty': 1, 'cost': 8.00, 'pn': 'Cool_01', 'location': 'Shelf F1'},
            {'item': 'Ice Packs (4×)', 'qty': 4, 'cost': 4.00, 'pn': 'Ice_01', 'location': 'Freezer'},
        ])
    
    # Create dataframe
    df = pd.DataFrame(items)
    df.insert(0, 'Checked', '☐')
    
    return df


# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1F4E78;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .shipping-card {
        background-color: #E7F3FF;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #4472C4;
        margin: 1rem 0;
    }
    .rate-display {
        background-color: #D9E1F2;
        padding: 1rem;
        border-radius: 8px;
        font-size: 1.2rem;
        font-weight: bold;
        text-align: center;
        margin-top: 1rem;
    }
    .success-box {
        background-color: #E2F0D9;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #70AD47;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #FFF2CC;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #FFC000;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INITIALIZE SESSION STATE
# ============================================================================

if 'order_number' not in st.session_state:
    st.session_state.order_number = f"KELP-{datetime.now().strftime('%Y%m%d')}-001"
if 'modules_selected' not in st.session_state:
    st.session_state.modules_selected = {'base': True}
if 'shipping_address' not in st.session_state:
    st.session_state.shipping_address = {}
if 'shipping_rate' not in st.session_state:
    st.session_state.shipping_rate = None
if 'shipping_label' not in st.session_state:
    st.session_state.shipping_label = None
if 'fedex_api' not in st.session_state:
    st.session_state.fedex_api = FedExAPI()
if 'order_history' not in st.session_state:
    st.session_state.order_history = []

# ============================================================================
# HEADER
# ============================================================================

st.markdown('<div class="main-header">🧪 KELP Smart Kit Builder Pro</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size: 1.2rem; color: #4472C4; margin-bottom: 2rem;">With Real-Time FedEx Shipping & Label Generation</div>', unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.header("📋 Order Information")
    order_number = st.text_input("Order Number", value=st.session_state.order_number)
    customer_name = st.text_input("Customer Name", placeholder="ABC Water District")
    project_name = st.text_input("Project Name", placeholder="Monthly Monitoring")
    
    st.divider()
    
    st.header("📍 Shipping Address")
    st.caption("Enter destination for real-time rate calculation")
    
    company = st.text_input("Company Name", placeholder="ABC Water District")
    contact = st.text_input("Contact Person", placeholder="John Smith")
    phone = st.text_input("Phone", placeholder="555-123-4567")
    address1 = st.text_input("Street Address", placeholder="123 Main St")
    address2 = st.text_input("Address Line 2", placeholder="Suite 100")
    city = st.text_input("City", placeholder="San Francisco")
    
    col1, col2 = st.columns(2)
    with col1:
        state = st.text_input("State", placeholder="CA", max_chars=2)
    with col2:
        zipcode = st.text_input("ZIP Code", placeholder="94102")
    
    # Store address in session state
    if all([address1, city, state, zipcode]):
        st.session_state.shipping_address = {
            "company": company,
            "contact_name": contact,
            "phone": phone,
            "streetLines": [address1] + ([address2] if address2 else []),
            "city": city,
            "stateOrProvinceCode": state.upper(),
            "postalCode": zipcode,
            "countryCode": "US"
        }
    
    st.divider()
    
    st.header("⚙️ Settings")
    show_costs = st.checkbox("Show Internal Costs", value=True)
    show_pick_list = st.checkbox("Show Pick List", value=False)
    
    st.divider()
    
    # Reset button in sidebar
    if st.button("🔄 Reset All", type="secondary", use_container_width=True):
        st.session_state.modules_selected = {'base': True}
        st.session_state.shipping_rate = None
        st.session_state.shipping_label = None
        st.session_state.shipping_address = {}
        st.session_state.order_number = f"KELP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        st.success("✅ All fields reset!")
        st.rerun()

# ============================================================================
# MAIN CONTENT - MODULE SELECTION
# ============================================================================

st.header("1️⃣ Select Test Modules")
modules_to_show = ['module_a', 'module_b', 'module_c', 'module_d', 'module_p', 'module_m']

# Create two columns for layout
col_modules, col_summary = st.columns([2, 1])

with col_modules:
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
                st.markdown(f"**Tests:** {module['description']}")
                if 'tests' in module:
                    st.caption(f"📊 {', '.join(module['tests'])}")
                
                if 'preservation' in module:
                    st.caption(f"🧪 **Preservation:** {module['preservation']}")
                
                if module.get('can_share', False):
                    st.success(f"✅ Can share bottle with {module.get('shares_with')}")

st.divider()

# ============================================================================
# SHIPPING OPTIONS
# ============================================================================

st.header("2️⃣ Select Shipping Type")

col_std, col_comp = st.columns(2)

with col_std:
    if st.button("📦 Standard Ground", key="ship_standard",
                 type="primary" if not st.session_state.modules_selected.get('compliance_shipping', False) else "secondary",
                 use_container_width=True):
        st.session_state.modules_selected['compliance_shipping'] = False
        st.session_state.shipping_rate = None  # Reset rate to trigger recalculation
    st.caption("FedEx Ground (3-5 days)")

with col_comp:
    if st.button("❄️ Compliance 2-Day", key="ship_compliance",
                 type="primary" if st.session_state.modules_selected.get('compliance_shipping', False) else "secondary",
                 use_container_width=True):
        st.session_state.modules_selected['compliance_shipping'] = True
        st.session_state.shipping_rate = None  # Reset rate
    st.caption("FedEx 2-Day with cooler & ice")

st.divider()

# ============================================================================
# CALCULATE SHIPPING RATE
# ============================================================================

st.header("3️⃣ Calculate Shipping Cost")

# Get selected modules
selected_modules = [k for k in modules_to_show if st.session_state.modules_selected.get(k, False)]

if selected_modules:
    
    # Calculate package weight
    package_weight = calculate_package_weight(selected_modules)
    is_compliance = st.session_state.modules_selected.get('compliance_shipping', False)
    
    display_weight = package_weight + 5.0 if is_compliance else package_weight
    st.info(f"📦 Estimated package weight: **{display_weight} lbs**" + 
            (" (includes cooler & ice)" if is_compliance else ""))
    
    # Check if address is provided for FedEx rate calculation
    if st.session_state.shipping_address:
        if st.button("🔄 Get Real-Time Shipping Rate from FedEx", type="primary"):
            with st.spinner("Contacting FedEx API..."):
                service_type = get_fedex_service_type(is_compliance)
                
                rate = st.session_state.fedex_api.calculate_shipping_rate(
                    destination=st.session_state.shipping_address,
                    weight_lbs=package_weight,
                    service_type=service_type,
                    is_compliance=is_compliance
                )
                
                if rate:
                    st.session_state.shipping_rate = rate
                    st.success("✅ Rate calculated successfully!")
        
        # Display rate if available
        if st.session_state.shipping_rate:
            rate = st.session_state.shipping_rate
            
            st.markdown(f"""
            <div class="shipping-card">
                <h3>📍 Shipping Details</h3>
                <p><strong>Service:</strong> {rate['service_name']}</p>
                <p><strong>Destination:</strong> {st.session_state.shipping_address['city']}, {st.session_state.shipping_address['stateOrProvinceCode']} {st.session_state.shipping_address['postalCode']}</p>
                <p><strong>Transit Time:</strong> {rate.get('transit_time', 'N/A')}</p>
                <div class="rate-display">
                    Shipping Cost: ${rate['total_charge']:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("💡 Enter shipping address in the sidebar to get real-time FedEx rates")

else:
    st.warning("⚠️ Please select at least one test module")

st.divider()

# ============================================================================
# COST SUMMARY (in col_summary from earlier)
# ============================================================================

with col_summary:
    st.header("💰 Cost Summary")
    
    # Calculate costs with smart sharing
    material_cost = COMPONENT_LIBRARY['base']['cost']
    
    sharing_a_c = (st.session_state.modules_selected.get('module_a', False) and 
                   st.session_state.modules_selected.get('module_c', False))
    
    for module_key in modules_to_show:
        if st.session_state.modules_selected.get(module_key, False):
            # Skip Module C cost if sharing with Module A
            if module_key == 'module_c' and sharing_a_c:
                continue
            else:
                material_cost += COMPONENT_LIBRARY[module_key]['cost']
    
    # Use FedEx rate if available, otherwise estimate
    if st.session_state.shipping_rate:
        shipping_cost = st.session_state.shipping_rate['total_charge']
        shipping_label = "FedEx (Actual)"
    else:
        # Fallback to estimate
        if st.session_state.modules_selected.get('compliance_shipping', False):
            shipping_cost = 50.00
            shipping_label = "Estimated"
        else:
            shipping_cost = 8.00
            shipping_label = "Estimated"
    
    total_cost = material_cost + LABOR_COST + shipping_cost
    customer_price = total_cost * MARKUP_FACTOR
    margin = customer_price - total_cost
    margin_pct = (margin / customer_price) * 100 if customer_price > 0 else 0
    
    # Calculate bottle count
    bottle_count = count_bottles(selected_modules, sharing_a_c)
    
    # Display metrics
    st.metric("Modules Selected", len(selected_modules))
    st.metric("Bottles Required", bottle_count)
    st.metric("Customer Price", f"${customer_price:.2f}")
    
    if show_costs:
        st.markdown("---")
        st.caption(f"Material: ${material_cost:.2f}")
        st.caption(f"Labor: ${LABOR_COST:.2f}")
        st.caption(f"Shipping ({shipping_label}): ${shipping_cost:.2f}")
        st.caption(f"**Total Cost:** ${total_cost:.2f}")
    
    # Show smart sharing indicator
    if sharing_a_c:
        st.success("✅ Smart Sharing: Module C FREE!")
        st.caption("Anions use same bottle as Gen Chem")

# ============================================================================
# GENERATE SHIPPING LABEL
# ============================================================================

st.header("4️⃣ Generate Shipping Label")

if st.session_state.shipping_address and selected_modules and st.session_state.shipping_rate:
    
    if st.button("📄 Generate FedEx Shipping Label", type="primary", use_container_width=True):
        with st.spinner("Generating shipping label..."):
            
            service_type = get_fedex_service_type(
                st.session_state.modules_selected.get('compliance_shipping', False)
            )
            
            label_data = st.session_state.fedex_api.generate_shipping_label(
                order_id=order_number,
                destination=st.session_state.shipping_address,
                weight_lbs=package_weight,
                service_type=service_type,
                is_compliance=st.session_state.modules_selected.get('compliance_shipping', False),
                reference_id=customer_name or ""
            )
            
            if label_data:
                st.session_state.shipping_label = label_data
                st.success("✅ Shipping label generated successfully!")
    
    # Display label info if available
    if st.session_state.shipping_label:
        label = st.session_state.shipping_label
        
        demo_text = " (DEMO MODE - Not a real shipment)" if label.get('demo_mode', False) else ""
        
        st.markdown(f"""
        <div class="success-box">
            <h3>✅ Shipping Label Ready{demo_text}</h3>
            <p><strong>Tracking Number:</strong> {label['tracking_number']}</p>
            <p><strong>Service:</strong> {label['service_type']}</p>
            <p><strong>Ship Date:</strong> {label.get('shipment_date', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.link_button(
                "🔗 View Shipping Label (PDF)",
                label['label_url'],
                use_container_width=True
            )
        
        with col2:
            tracking_url = f"https://www.fedex.com/fedextrack/?trknbr={label['tracking_number']}"
            st.link_button(
                "🔍 Track Shipment",
                tracking_url,
                use_container_width=True
            )
        
        # Order completed summary
        st.divider()
        st.header("✅ Order Complete")
        
        st.markdown(f"""
        **Order Number:** {order_number}  
        **Customer:** {customer_name or 'N/A'}  
        **Project:** {project_name or 'N/A'}  
        **Modules:** {', '.join([COMPONENT_LIBRARY[m]['name'].split(':')[1].strip() for m in selected_modules])}  
        **Tracking:** {label['tracking_number']}  
        **Total:** ${customer_price:.2f}
        """)
        
        # Save to order history
        order_record = {
            'order_number': order_number,
            'customer': customer_name,
            'project': project_name,
            'modules': selected_modules,
            'tracking': label['tracking_number'],
            'price': customer_price,
            'timestamp': datetime.now().isoformat()
        }
        
        col_save, col_reset = st.columns(2)
        
        with col_save:
            if st.button("💾 Save Order & New", type="primary", use_container_width=True):
                st.session_state.order_history.append(order_record)
                
                # Reset session state
                st.session_state.modules_selected = {'base': True}
                st.session_state.shipping_rate = None
                st.session_state.shipping_label = None
                
                # Generate new order number
                st.session_state.order_number = f"KELP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                st.success("✅ Order saved!")
                st.rerun()
        
        with col_reset:
            if st.button("🔄 Reset (Don't Save)", type="secondary", use_container_width=True):
                # Reset without saving
                st.session_state.modules_selected = {'base': True}
                st.session_state.shipping_rate = None
                st.session_state.shipping_label = None
                
                # Generate new order number
                st.session_state.order_number = f"KELP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                st.info("🔄 Order reset - starting fresh")
                st.rerun()

else:
    st.info("ℹ️ Complete steps 1-3 above before generating shipping label")

# ============================================================================
# PICK LIST SECTION
# ============================================================================

if show_pick_list and selected_modules:
    st.divider()
    st.header("📋 Assembly Pick List")
    
    pick_list_df = generate_pick_list(
        order_id=order_number,
        customer_name=customer_name,
        project_name=project_name,
        selected_modules=selected_modules,
        sharing_active=sharing_a_c,
        is_compliance=st.session_state.modules_selected.get('compliance_shipping', False)
    )
    
    st.dataframe(pick_list_df, use_container_width=True, hide_index=True)
    
    # Download button for pick list
    csv = pick_list_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Pick List (CSV)",
        data=csv,
        file_name=f"pick_list_{order_number}.csv",
        mime="text/csv"
    )
    
    # Show special warnings
    if 'module_p' in selected_modules:
        st.markdown("""
        <div class="warning-box">
            <h4>⚠️ PFAS KIT WARNING</h4>
            <p>Use ONLY PFAS-free materials! No fluorinated plastics, tapes, or gloves.</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# ORDER HISTORY
# ============================================================================

if st.session_state.order_history:
    st.divider()
    st.header("📊 Order History")
    
    history_df = pd.DataFrame(st.session_state.order_history)
    st.dataframe(history_df, use_container_width=True, hide_index=True)
    
    # Download order history
    history_csv = history_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Order History (CSV)",
        data=history_csv,
        file_name=f"order_history_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("KELP Smart Kit Builder Pro v2.0 | FedEx API Integration | Real-Time Rates & Labels")
st.caption("💡 Tip: Configure FedEx credentials in .streamlit/secrets.toml for live rates and labels")
