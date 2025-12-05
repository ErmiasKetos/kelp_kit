#!/usr/bin/env python3
"""
KELP Smart Kit Builder - Enhanced Streamlit Application
With FedEx API Integration for Dynamic Shipping & Label Generation

New Features:
- Real-time FedEx rate calculation based on destination
- Automatic shipping label generation
- Address validation
- Tracking number assignment
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import requests
from typing import Dict, Optional, Tuple
import base64

# Page configuration
st.set_page_config(
    page_title="KELP Kit Builder",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# FEDEX API CONFIGURATION
# ============================================================================

class FedExAPI:
    """
    FedEx API Integration for rate calculation and label generation
    
    Documentation: https://developer.fedex.com/api/en-us/
    """
    
    def __init__(self):
        # FedEx API credentials (store securely in environment variables)
        self.api_key = st.secrets.get("FEDEX_API_KEY", "")
        self.secret_key = st.secrets.get("FEDEX_SECRET_KEY", "")
        self.account_number = st.secrets.get("FEDEX_ACCOUNT_NUMBER", "")
        self.meter_number = st.secrets.get("FEDEX_METER_NUMBER", "")
        
        # API endpoints
        self.base_url = "https://apis.fedex.com"
        self.auth_url = f"{self.base_url}/oauth/token"
        self.rate_url = f"{self.base_url}/rate/v1/rates/quotes"
        self.ship_url = f"{self.base_url}/ship/v1/shipments"
        
        # KELP origin address (Sunnyvale, CA)
        self.origin = {
            "streetLines": ["123 Innovation Way"],
            "city": "Sunnyvale",
            "stateOrProvinceCode": "CA",
            "postalCode": "94085",
            "countryCode": "US"
        }
        
        self.access_token = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with FedEx API and get access token
        
        Returns:
            bool: True if authentication successful
        """
        try:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            
            response = requests.post(
                self.auth_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                return True
            else:
                st.error(f"FedEx authentication failed: {response.text}")
                return False
                
        except Exception as e:
            st.error(f"FedEx authentication error: {str(e)}")
            return False
    
    def validate_address(self, address: Dict) -> Tuple[bool, Optional[Dict]]:
        """
        Validate customer address
        
        Args:
            address: Dict with streetLines, city, stateOrProvinceCode, postalCode, countryCode
            
        Returns:
            Tuple of (is_valid, validated_address)
        """
        # FedEx Address Validation API endpoint
        url = f"{self.base_url}/address/v1/addresses/resolve"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "addressesToValidate": [
                {
                    "address": address
                }
            ]
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if address is valid
                if data.get("output", {}).get("resolvedAddresses"):
                    validated = data["output"]["resolvedAddresses"][0]
                    return True, validated.get("resolvedAddress")
                else:
                    return False, None
            else:
                return False, None
                
        except Exception as e:
            st.warning(f"Address validation error: {str(e)}")
            return True, address  # Proceed with original address if validation fails
    
    def calculate_shipping_rate(
        self, 
        destination: Dict,
        weight_lbs: float,
        service_type: str = "FEDEX_GROUND",
        is_compliance: bool = False
    ) -> Optional[Dict]:
        """
        Calculate shipping rate using FedEx API
        
        Args:
            destination: Destination address dict
            weight_lbs: Package weight in pounds
            service_type: FedEx service type (FEDEX_GROUND, FEDEX_2_DAY, etc.)
            is_compliance: If True, includes cooler and ice packs
            
        Returns:
            Dict with rate information or None if error
        """
        if not self.access_token:
            if not self.authenticate():
                return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Adjust weight for compliance shipping (add cooler + ice)
        if is_compliance:
            weight_lbs += 5.0  # Cooler and ice packs add ~5 lbs
        
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
        
        try:
            response = requests.post(self.rate_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract rate details
                if data.get("output", {}).get("rateReplyDetails"):
                    rate_detail = data["output"]["rateReplyDetails"][0]
                    
                    # Get total charges
                    total_charge = 0
                    for charge in rate_detail.get("ratedShipmentDetails", []):
                        if charge.get("rateType") == "ACCOUNT":
                            total_charge = float(
                                charge.get("totalNetCharge", 0)
                            )
                            break
                    
                    return {
                        "service_type": rate_detail.get("serviceType"),
                        "service_name": rate_detail.get("serviceName"),
                        "total_charge": total_charge,
                        "currency": "USD",
                        "delivery_date": rate_detail.get("deliveryTimestamp"),
                        "transit_time": rate_detail.get("transitTime")
                    }
                else:
                    st.error("No rates returned from FedEx")
                    return None
                    
            else:
                st.error(f"FedEx rate request failed: {response.text}")
                return None
                
        except Exception as e:
            st.error(f"Shipping rate calculation error: {str(e)}")
            return None
    
    def generate_shipping_label(
        self,
        order_id: str,
        destination: Dict,
        weight_lbs: float,
        service_type: str = "FEDEX_GROUND",
        is_compliance: bool = False,
        reference_id: str = ""
    ) -> Optional[Dict]:
        """
        Generate FedEx shipping label
        
        Args:
            order_id: KELP order number
            destination: Destination address
            weight_lbs: Package weight
            service_type: FedEx service type
            is_compliance: Compliance shipping flag
            reference_id: Customer reference
            
        Returns:
            Dict with label data and tracking number
        """
        if not self.access_token:
            if not self.authenticate():
                return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Adjust weight for compliance
        if is_compliance:
            weight_lbs += 5.0
        
        payload = {
            "labelResponseOptions": "URL_ONLY",
            "requestedShipment": {
                "shipper": {
                    "contact": {
                        "personName": "KELP Environmental Lab",
                        "phoneNumber": "4085551234",
                        "companyName": "KETOS Environmental Lab Platform"
                    },
                    "address": self.origin
                },
                "recipients": [
                    {
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
                    }
                ],
                "shipDatestamp": datetime.now().strftime("%Y-%m-%d"),
                "serviceType": service_type,
                "packagingType": "YOUR_PACKAGING",
                "pickupType": "USE_SCHEDULED_PICKUP",
                "blockInsightVisibility": False,
                "shippingChargesPayment": {
                    "paymentType": "SENDER"
                },
                "labelSpecification": {
                    "imageType": "PDF",
                    "labelStockType": "PAPER_4X6"
                },
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
                        },
                        "customerReferences": [
                            {
                                "customerReferenceType": "CUSTOMER_REFERENCE",
                                "value": f"KELP-{order_id}"
                            }
                        ]
                    }
                ]
            },
            "accountNumber": {
                "value": self.account_number
            }
        }
        
        try:
            response = requests.post(self.ship_url, json=payload, headers=headers)
            
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
                else:
                    st.error("No shipment created")
                    return None
                    
            else:
                st.error(f"Label generation failed: {response.text}")
                return None
                
        except Exception as e:
            st.error(f"Label generation error: {str(e)}")
            return None


# ============================================================================
# COMPONENT LIBRARY (Same as before)
# ============================================================================

COMPONENT_LIBRARY = {
    'base': {
        'name': 'BASE COMPONENTS',
        'description': 'Included in every kit',
        'cost': 9.50,
        'weight_lbs': 1.5,  # Added weight
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
        'weight_lbs': 0.4,
        'items': [
            {'item': '250mL HDPE bottle (trace-metal)', 'qty': 1, 'cost': 3.50, 'pn': 'Bottle_02', 'location': 'Shelf B2'},
            {'item': 'HNO₃ preservative vial (2mL)', 'qty': 1, 'cost': 1.50, 'pn': 'Pres_HNO3', 'location': 'Shelf D1'},
        ],
        'color': '#70AD47',
        'tests': ['Lead (Pb)', 'Copper (Cu)', 'Arsenic (As)', 'Chromium (Cr)', 'Zinc (Zn)', 'Iron (Fe)', 'Manganese (Mn)'],
        'preservation': 'HNO₃ to pH <2',
        'can_share': False
    },
    'module_c': {
        'name': 'MODULE C: Anions (EPA 300.1)',
        'description': 'Chloride, Sulfate, Nitrate, Fluoride',
        'cost': 1.50,
        'weight_lbs': 0.3,
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
        'weight_lbs': 0.5,
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
        'weight_lbs': 0.8,
        'items': [
            {'item': '250mL PP bottle (PFAS-free cert)', 'qty': 2, 'cost': 10.00, 'pn': 'Bottle_05', 'location': 'Shelf C1'},
            {'item': 'PP caps w/ PE liners', 'qty': 2, 'cost': 3.00, 'pn': 'Cap_PFAS', 'location': 'Shelf C2'},
            {'item': 'PFAS-free labels', 'qty': 2, 'cost': 1.00, 'pn': 'Label_PFAS', 'location': 'Shelf C3'},
            {'item': 'PFAS-free gloves (UPGRADE)', 'qty': 1, 'cost': 1.50, 'pn': 'PPE_PFAS', 'location': 'Shelf E1'},
        ],
        'color': '#E7E6E6',
        'tests': ['PFAS-3', 'PFAS-14', 'PFAS-18', 'PFAS-25', 'PFAS-40'],
        'special_warning': '⚠️ PFAS KIT - Use ONLY PFAS-free materials!',
        'preservation': 'None (PFAS-free containers)',
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

LABOR_COST = 7.46
MARKUP_FACTOR = 1.4

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_package_weight(selected_modules: list) -> float:
    """Calculate total package weight in pounds"""
    weight = COMPONENT_LIBRARY['base']['weight_lbs']
    
    for module_key in selected_modules:
        if module_key in COMPONENT_LIBRARY:
            weight += COMPONENT_LIBRARY[module_key].get('weight_lbs', 0)
    
    return round(weight, 2)


def get_fedex_service_type(is_compliance: bool) -> str:
    """Get FedEx service type based on shipping option"""
    if is_compliance:
        return "FEDEX_2_DAY"
    else:
        return "FEDEX_GROUND"


# ============================================================================
# INITIALIZE SESSION STATE
# ============================================================================

if 'order_number' not in st.session_state:
    st.session_state.order_number = f"2025-{datetime.now().strftime('%m%d')}-001"
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
    }
    .success-box {
        background-color: #E2F0D9;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #70AD47;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER
# ============================================================================

st.markdown('<div class="main-header">🧪 KELP Kit Builder</div>', unsafe_allow_html=True)
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

# ============================================================================
# MAIN CONTENT
# ============================================================================

# Module Selection
st.header("1️⃣ Select Test Modules")
modules_to_show = ['module_a', 'module_b', 'module_c', 'module_d', 'module_p', 'module_m']

col1, col2 = st.columns([2, 1])

with col1:
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

# Shipping Options
st.header("2️⃣ Select Shipping Type")

col_std, col_comp = st.columns(2)

with col_std:
    if st.button("📦 Standard Ground", key="ship_standard",
                 type="primary" if not st.session_state.modules_selected.get('compliance_shipping', False) else "secondary",
                 use_container_width=True):
        st.session_state.modules_selected['compliance_shipping'] = False
        st.session_state.shipping_rate = None  # Reset rate
    st.caption("FedEx Ground (3-5 days)")

with col_comp:
    if st.button("❄️ Compliance 2-Day", key="ship_compliance",
                 type="primary" if st.session_state.modules_selected.get('compliance_shipping', False) else "secondary",
                 use_container_width=True):
        st.session_state.modules_selected['compliance_shipping'] = True
        st.session_state.shipping_rate = None  # Reset rate
    st.caption("FedEx 2-Day with cooler & ice")

st.divider()

# Calculate Shipping Rate
st.header("3️⃣ Calculate Shipping Cost")

if st.session_state.shipping_address:
    
    # Calculate selected modules
    selected_modules = [k for k in modules_to_show if st.session_state.modules_selected.get(k, False)]
    
    if selected_modules:
        # Calculate package weight
        package_weight = calculate_package_weight(selected_modules)
        is_compliance = st.session_state.modules_selected.get('compliance_shipping', False)
        
        st.info(f"📦 Estimated package weight: **{package_weight} lbs** (before cooler)" if not is_compliance else f"📦 Estimated package weight: **{package_weight + 5.0} lbs** (with cooler & ice)")
        
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
        st.warning("⚠️ Please select at least one test module")
else:
    st.warning("⚠️ Please enter shipping address in the sidebar")

st.divider()

# Cost Summary
with col2:
    st.header("💰 Cost Summary")
    
    # Calculate costs with smart sharing
    material_cost = COMPONENT_LIBRARY['base']['cost']
    selected_modules = []
    
    sharing_a_c = (st.session_state.modules_selected.get('module_a', False) and 
                   st.session_state.modules_selected.get('module_c', False))
    
    for module_key in modules_to_show:
        if st.session_state.modules_selected.get(module_key, False):
            selected_modules.append(module_key)
            
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
    
    # Display
    st.metric("Modules Selected", len(selected_modules))
    st.metric("Customer Price", f"${customer_price:.2f}")
    
    if show_costs:
        st.markdown("---")
        st.caption(f"Material: ${material_cost:.2f}")
        st.caption(f"Labor: ${LABOR_COST:.2f}")
        st.caption(f"Shipping ({shipping_label}): ${shipping_cost:.2f}")
        st.caption(f"**Total Cost:** ${total_cost:.2f}")
        st.caption(f"**Profit:** ${margin:.2f} ({margin_pct:.1f}%)")
    
    if sharing_a_c:
        st.success("✅ Smart Sharing Active - Save $1.50")

# Generate Shipping Label
st.divider()
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
        
        st.markdown(f"""
        <div class="success-box">
            <h3>✅ Shipping Label Ready</h3>
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
        
        if st.button("🎉 Complete Order & Start New", type="primary"):
            # Reset session state
            st.session_state.modules_selected = {'base': True}
            st.session_state.shipping_rate = None
            st.session_state.shipping_label = None
            st.rerun()

else:
    st.info("ℹ️ Complete steps 1-3 above before generating shipping label")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("KELP Smart Kit Builder Pro v2.0 | FedEx API Integration | Real-Time Rates & Labels")
