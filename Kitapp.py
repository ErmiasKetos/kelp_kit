#!/usr/bin/env python3
"""
KELP Smart Kit Builder - REDESIGNED VERSION 3.0
Clean Tabbed Interface | No Markup | User-Friendly

VERSION: 3.0 (December 2025)

IMPROVEMENTS:
- Clean tabbed interface (no long scrolling)
- Removed all markup/profit calculations
- Shows only actual costs to customer
- Step-by-step wizard flow
- Multi-package support
- Labor excluded from price
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
    page_title="KELP Kit Builder",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CONSTANTS - NO MARKUP, JUST ACTUAL COSTS
# ============================================================================

# Component costs (what customer pays - no markup shown)
COMPONENT_LIBRARY = {
    'base': {
        'name': 'Base Kit',
        'cost': 13.30,  # Actual price to customer
        'weight_lbs': 1.5,
        'items': ['COC Form', 'Labels', 'Gloves (2 pairs)', 'Bubble Wrap', 'Box', 'Instructions']
    },
    'module_a': {
        'name': 'General Chemistry',
        'cost': 3.50,  # Actual price
        'weight_lbs': 0.3,
        'bottle': '250mL HDPE unacidified',
        'tests': ['Alkalinity', 'Hardness', 'TDS', 'pH', 'Conductivity']
    },
    'module_b': {
        'name': 'Metals (ICP-MS)',
        'cost': 7.00,  # Actual price
        'weight_lbs': 0.4,
        'bottle': '250mL HDPE acidified (HNO₃)',
        'tests': ['EPA 200.8 Metals Panel']
    },
    'module_c': {
        'name': 'Anions/Nutrients',
        'cost': 2.10,  # Actual price when standalone
        'cost_shared': 0.00,  # FREE when sharing
        'weight_lbs': 0.3,
        'bottle': '250mL HDPE unacidified',
        'tests': ['Chloride', 'Sulfate', 'Nitrate', 'Phosphate']
    },
    'module_d': {
        'name': 'Nutrients (IC)',
        'cost': 5.60,  # Actual price
        'weight_lbs': 0.5,
        'bottle': '250mL PP acidified (H₂SO₄)',
        'tests': ['EPA 300.1 Nutrients']
    },
    'module_p': {
        'name': 'PFAS Testing',
        'cost': 21.70,  # Actual price
        'weight_lbs': 0.8,
        'bottle': '2× 250mL PP PFAS-certified',
        'bottles_needed': 2,
        'tests': ['EPA 537.1/1633A PFAS Panel']
    }
}

# Labor tracking (informational only, NOT charged)
ASSEMBLY_TIME_MINUTES = 7  # Per package
LABOR_COST_INTERNAL = 7.46  # For internal tracking only

# ============================================================================
# FEDEX API CLASS (Simplified)
# ============================================================================

class FedExAPI:
    """Simplified FedEx API Integration"""
    
    def __init__(self):
        try:
            self.api_key = st.secrets.get("FEDEX_API_KEY", "")
            self.secret_key = st.secrets.get("FEDEX_SECRET_KEY", "")
            self.account_number = st.secrets.get("FEDEX_ACCOUNT_NUMBER", "")
            self.meter_number = st.secrets.get("FEDEX_METER_NUMBER", "")
        except:
            self.api_key = ""
            self.secret_key = ""
            self.account_number = ""
            self.meter_number = ""
        
        self.demo_mode = not all([self.api_key, self.secret_key, self.account_number, self.meter_number])
        
        try:
            env = st.secrets.get("FEDEX_ENVIRONMENT", "production")
        except:
            env = "production"
        
        self.base_url = "https://apis-sandbox.fedex.com" if env == "sandbox" else "https://apis.fedex.com"
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
    
    def authenticate(self) -> bool:
        """Authenticate with FedEx"""
        if self.demo_mode:
            return True
        if self.access_token:
            return True
        if self.auth_failed:
            return False
        
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
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
        except:
            self.auth_failed = True
            return False
    
    def calculate_shipping_rate(self, destination: Dict, weight_lbs: float, 
                                service_type: str = "FEDEX_GROUND") -> Optional[Dict]:
        """Calculate shipping rate for a single package"""
        
        # Demo mode - return estimated rates
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
        
        # Real FedEx API call
        if not self.authenticate():
            return None
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
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
                        'demo_mode': False
                    }
            return None
        except:
            return None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def count_bottles(selected_modules: List[str], sharing_active: bool) -> int:
    """Count total bottles needed"""
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


def calculate_package_count(bottle_count: int) -> int:
    """Calculate packages needed (max 2 bottles per package)"""
    return max(1, (bottle_count + 1) // 2)


def calculate_package_weight(selected_modules: List[str], package_count: int) -> float:
    """Calculate total weight for all packages"""
    base_weight = COMPONENT_LIBRARY['base']['weight_lbs']
    module_weight = sum(
        COMPONENT_LIBRARY[m].get('weight_lbs', 0) 
        for m in selected_modules 
        if m in COMPONENT_LIBRARY
    )
    return round((base_weight + module_weight) * package_count, 2)


def calculate_total_price(selected_modules: List[str], sharing_active: bool, 
                         package_count: int, shipping_cost: float) -> Dict:
    """
    Calculate total price - NO MARKUP SHOWN
    Customer sees only final price
    """
    # Base kit cost × packages
    kit_cost = COMPONENT_LIBRARY['base']['cost'] * package_count
    
    # Module costs
    module_cost = 0
    for module_key in selected_modules:
        if module_key == 'module_c' and sharing_active:
            module_cost += COMPONENT_LIBRARY[module_key]['cost_shared']  # $0
        elif module_key in COMPONENT_LIBRARY:
            module_cost += COMPONENT_LIBRARY[module_key]['cost']
    
    total_price = kit_cost + module_cost + shipping_cost
    
    return {
        'kit_cost': kit_cost,
        'module_cost': module_cost,
        'shipping_cost': shipping_cost,
        'total_price': round(total_price, 2)
    }


def estimate_shipping(is_compliance: bool, package_count: int) -> float:
    """Estimate shipping when FedEx rate not available"""
    cost_per_package = 50.00 if is_compliance else 12.00
    return cost_per_package * package_count

# ============================================================================
# END OF PART 1
# ============================================================================
# ============================================================================
# PART 2: CLEAN TABBED INTERFACE - NO LONG SCROLLING
# ============================================================================

# Simple CSS
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: white;
        border-radius: 4px 4px 0 0;
    }
    
    .module-card {
        background: white;
        padding: 1rem;
        border-radius: 6px;
        border-left: 4px solid #0066B2;
        margin-bottom: 0.75rem;
    }
    
    .cost-box {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #0066B2;
        text-align: center;
    }
    
    .warning-box {
        background: #FFF3CD;
        border-left: 4px solid #FFA500;
        padding: 1rem;
        border-radius: 4px;
    }
    
    .success-box {
        background: #E8F5E9;
        border-left: 4px solid #00A86B;
        padding: 1rem;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'modules_selected' not in st.session_state:
    st.session_state.modules_selected = {}
if 'shipping_address' not in st.session_state:
    st.session_state.shipping_address = None
if 'shipping_rate' not in st.session_state:
    st.session_state.shipping_rate = None
if 'fedex_api' not in st.session_state:
    st.session_state.fedex_api = FedExAPI()
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

# ============================================================================
# HEADER
# ============================================================================

st.title("🧪 KELP Kit Builder")
st.markdown("**Configure your water testing kit in 3 easy steps**")

# Quick stats in header
if st.session_state.modules_selected:
    selected = [k for k in ['module_a', 'module_b', 'module_c', 'module_d', 'module_p'] 
                if st.session_state.modules_selected.get(k, False)]
    if selected:
        sharing = 'module_a' in selected and 'module_c' in selected
        bottles = count_bottles(selected, sharing)
        packages = calculate_package_count(bottles)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Modules", len(selected))
        with col2:
            st.metric("Bottles", bottles)
        with col3:
            st.metric("Packages", packages)

st.divider()

# ============================================================================
# SIDEBAR - SIMPLIFIED
# ============================================================================

with st.sidebar:
    st.header("🚚 Shipping Address")
    
    with st.form("address_form"):
        city = st.text_input("City *", placeholder="San Francisco")
        col1, col2 = st.columns(2)
        with col1:
            state = st.text_input("State *", placeholder="CA", max_chars=2)
        with col2:
            zip_code = st.text_input("ZIP *", placeholder="94102")
        
        submitted = st.form_submit_button("💾 Save Address", use_container_width=True)
        
        if submitted and city and state and zip_code:
            st.session_state.shipping_address = {
                'city': city,
                'stateOrProvinceCode': state.upper(),
                'postalCode': zip_code,
                'countryCode': 'US'
            }
            st.success("✅ Saved!")
            st.rerun()
    
    if st.session_state.shipping_address:
        st.divider()
        addr = st.session_state.shipping_address
        st.caption(f"**Current:** {addr['city']}, {addr['stateOrProvinceCode']} {addr['postalCode']}")
        
        if st.button("Clear", use_container_width=True):
            st.session_state.shipping_address = None
            st.session_state.shipping_rate = None
            st.rerun()
    
    st.divider()
    
    # Compliance option
    compliance = st.checkbox(
        "2-Day Shipping (with cooler)",
        value=st.session_state.modules_selected.get('compliance', False)
    )
    st.session_state.modules_selected['compliance'] = compliance
    
    st.divider()
    
    if st.button("🔄 Reset All", use_container_width=True):
        st.session_state.modules_selected = {}
        st.session_state.shipping_address = None
        st.session_state.shipping_rate = None
        st.rerun()

# ============================================================================
# TABBED INTERFACE - NO SCROLLING
# ============================================================================

tab1, tab2, tab3 = st.tabs(["1️⃣ Select Modules", "2️⃣ Review & Ship", "3️⃣ Pick List & Labels"])

# ============================================================================
# TAB 1: MODULE SELECTION
# ============================================================================

with tab1:
    st.subheader("Select Your Test Modules")
    
    # Module A
    col_a1, col_a2 = st.columns([1, 6])
    with col_a1:
        module_a = st.checkbox("", key="sel_a", value=st.session_state.modules_selected.get('module_a', False))
        st.session_state.modules_selected['module_a'] = module_a
    with col_a2:
        st.markdown(f"""
        **Module A: General Chemistry** - ${COMPONENT_LIBRARY['module_a']['cost']:.2f}  
        <small>250mL HDPE unacidified | Alkalinity, Hardness, TDS, pH, Conductivity</small>
        """, unsafe_allow_html=True)
    
    # Module B
    col_b1, col_b2 = st.columns([1, 6])
    with col_b1:
        module_b = st.checkbox("", key="sel_b", value=st.session_state.modules_selected.get('module_b', False))
        st.session_state.modules_selected['module_b'] = module_b
    with col_b2:
        st.markdown(f"""
        **Module B: Metals (ICP-MS)** - ${COMPONENT_LIBRARY['module_b']['cost']:.2f}  
        <small>250mL HDPE pre-acidified (HNO₃) | EPA 200.8 Metals Panel</small>
        """, unsafe_allow_html=True)
    
    # Module C (with sharing indicator)
    sharing_active = (st.session_state.modules_selected.get('module_a', False) and 
                     st.session_state.modules_selected.get('module_c', False))
    
    col_c1, col_c2 = st.columns([1, 6])
    with col_c1:
        module_c = st.checkbox("", key="sel_c", value=st.session_state.modules_selected.get('module_c', False))
        st.session_state.modules_selected['module_c'] = module_c
    with col_c2:
        if sharing_active:
            st.markdown(f"""
            **Module C: Anions/Nutrients** - ~~${COMPONENT_LIBRARY['module_c']['cost']:.2f}~~ **FREE!** ✅  
            <small>SHARED bottle with Module A | Chloride, Sulfate, Nitrate, Phosphate</small>
            """, unsafe_allow_html=True)
            st.success("✅ Smart Sharing: Uses same bottle as Module A")
        else:
            st.markdown(f"""
            **Module C: Anions/Nutrients** - ${COMPONENT_LIBRARY['module_c']['cost']:.2f}  
            <small>250mL HDPE unacidified | Chloride, Sulfate, Nitrate, Phosphate</small>
            """, unsafe_allow_html=True)
    
    # Module D
    col_d1, col_d2 = st.columns([1, 6])
    with col_d1:
        module_d = st.checkbox("", key="sel_d", value=st.session_state.modules_selected.get('module_d', False))
        st.session_state.modules_selected['module_d'] = module_d
    with col_d2:
        st.markdown(f"""
        **Module D: Nutrients (IC)** - ${COMPONENT_LIBRARY['module_d']['cost']:.2f}  
        <small>250mL PP pre-acidified (H₂SO₄) | EPA 300.1 Nutrients</small>
        """, unsafe_allow_html=True)
    
    # Module P
    col_p1, col_p2 = st.columns([1, 6])
    with col_p1:
        module_p = st.checkbox("", key="sel_p", value=st.session_state.modules_selected.get('module_p', False))
        st.session_state.modules_selected['module_p'] = module_p
    with col_p2:
        st.markdown(f"""
        **Module P: PFAS Testing** - ${COMPONENT_LIBRARY['module_p']['cost']:.2f}  
        <small>2× 250mL PP PFAS-certified | EPA 537.1/1633A PFAS Panel</small>
        """, unsafe_allow_html=True)
        if module_p:
            st.warning("⚠️ Special handling required: PFAS-free containers")
    
    st.divider()
    
    # Continue button
    selected = [k for k in ['module_a', 'module_b', 'module_c', 'module_d', 'module_p'] 
                if st.session_state.modules_selected.get(k, False)]
    
    if selected:
        if st.button("➡️ Continue to Review", type="primary", use_container_width=True):
            st.session_state.active_tab = 1
            st.rerun()
    else:
        st.info("👆 Select at least one module to continue")

# ============================================================================
# TAB 2: REVIEW & SHIPPING
# ============================================================================

with tab2:
    selected = [k for k in ['module_a', 'module_b', 'module_c', 'module_d', 'module_p'] 
                if st.session_state.modules_selected.get(k, False)]
    
    if not selected:
        st.warning("⬅️ Go to Tab 1 to select modules first")
    else:
        st.subheader("Review Your Order")
        
        # Calculate everything
        sharing = 'module_a' in selected and 'module_c' in selected
        bottles = count_bottles(selected, sharing)
        packages = calculate_package_count(bottles)
        is_compliance = st.session_state.modules_selected.get('compliance', False)
        weight = calculate_package_weight(selected, packages)
        
        if is_compliance:
            weight += 5.0 * packages
        
        # Multi-package warning
        if packages > 1:
            st.markdown(f"""
            <div class="warning-box">
                <strong>⚠️ Multiple Packages Required</strong><br/>
                {packages} packages needed for {bottles} bottles (max 2 bottles per package)
            </div>
            """, unsafe_allow_html=True)
        
        # Calculate shipping
        has_address = st.session_state.shipping_address is not None
        
        if has_address and not st.session_state.shipping_rate:
            if st.button("🔄 Calculate Shipping Rate", type="primary", use_container_width=True):
                with st.spinner("Getting FedEx rate..."):
                    service = "FEDEX_2_DAY" if is_compliance else "FEDEX_GROUND"
                    weight_per_pkg = weight / packages
                    
                    total_shipping = 0
                    for _ in range(packages):
                        rate = st.session_state.fedex_api.calculate_shipping_rate(
                            st.session_state.shipping_address, weight_per_pkg, service
                        )
                        if rate:
                            total_shipping += rate['total_charge']
                    
                    if total_shipping > 0:
                        st.session_state.shipping_rate = {
                            'total_charge': total_shipping,
                            'package_count': packages,
                            'service_name': 'FedEx 2Day' if is_compliance else 'FedEx Ground'
                        }
                        st.rerun()
        
        # Get shipping cost
        if st.session_state.shipping_rate:
            shipping_cost = st.session_state.shipping_rate['total_charge']
        else:
            shipping_cost = estimate_shipping(is_compliance, packages)
        
        # Calculate final price
        price_breakdown = calculate_total_price(selected, sharing, packages, shipping_cost)
        
        # Display price
        st.markdown("### Your Total")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Itemized list
            st.write(f"**Kit & Supplies:** ${price_breakdown['kit_cost']:.2f}")
            if packages > 1:
                st.caption(f"  (Base kit ${COMPONENT_LIBRARY['base']['cost']:.2f} × {packages} packages)")
            
            st.write(f"**Test Modules:** ${price_breakdown['module_cost']:.2f}")
            for mod in selected:
                mod_name = COMPONENT_LIBRARY[mod]['name']
                if mod == 'module_c' and sharing:
                    st.caption(f"  • {mod_name}: FREE (shared)")
                else:
                    st.caption(f"  • {mod_name}: ${COMPONENT_LIBRARY[mod]['cost']:.2f}")
            
            st.write(f"**Shipping:** ${price_breakdown['shipping_cost']:.2f}")
            if st.session_state.shipping_rate:
                st.caption(f"  {st.session_state.shipping_rate['service_name']} × {packages}")
            else:
                st.caption(f"  Estimated × {packages}")
            
            st.caption(f"\n*Assembly: ~{ASSEMBLY_TIME_MINUTES * packages} minutes (no charge)*")
        
        with col2:
            st.markdown(f"""
            <div class="cost-box">
                <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">TOTAL</div>
                <div style="font-size: 2.5rem; font-weight: bold; color: #0066B2;">
                    ${price_breakdown['total_price']:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # Action buttons
        if has_address and st.session_state.shipping_rate:
            if st.button("✅ Confirm Order", type="primary", use_container_width=True):
                st.success("✅ Order confirmed! Go to Tab 3 for pick list and labels.")
                st.session_state.active_tab = 2
                st.balloons()
        else:
            if not has_address:
                st.info("💡 Add shipping address in sidebar to continue")
            else:
                st.info("💡 Calculate shipping rate to continue")

# ============================================================================
# TAB 3: PICK LIST & LABELS
# ============================================================================

with tab3:
    selected = [k for k in ['module_a', 'module_b', 'module_c', 'module_d', 'module_p'] 
                if st.session_state.modules_selected.get(k, False)]
    
    if not selected or not st.session_state.shipping_rate:
        st.warning("⬅️ Complete Tabs 1 & 2 first")
    else:
        st.subheader("Pick List & Labels")
        
        sharing = 'module_a' in selected and 'module_c' in selected
        bottles = count_bottles(selected, sharing)
        packages = calculate_package_count(bottles)
        
        # Simple pick list
        st.markdown("### 📋 Assembly Instructions")
        
        st.markdown(f"""
        **Packages to prepare:** {packages}  
        **Total bottles:** {bottles}  
        **Assembly time:** ~{ASSEMBLY_TIME_MINUTES * packages} minutes
        """)
        
        st.markdown("**Base Components** (per package):")
        for item in COMPONENT_LIBRARY['base']['items']:
            st.write(f"  ☐ {item}")
        
        st.markdown("**Modules:**")
        for mod in selected:
            mod_info = COMPONENT_LIBRARY[mod]
            if mod == 'module_c' and sharing:
                st.write(f"  ☐ {mod_info['name']}: **SHARED** (use Module A bottle)")
            else:
                st.write(f"  ☐ {mod_info['name']}: {mod_info.get('bottle', 'N/A')}")
        
        if packages > 1:
            st.warning(f"⚠️ Prepare {packages} separate kits (max 2 bottles per package)")
        
        st.divider()
        
        # Labels
        st.markdown("### 🏷️ Shipping Labels")
        
        if st.session_state.shipping_address:
            st.info(f"📍 Shipping to: {st.session_state.shipping_address['city']}, {st.session_state.shipping_address['stateOrProvinceCode']}")
            st.caption(f"Service: {st.session_state.shipping_rate['service_name']}")
            st.caption(f"Packages: {packages}")
            
            if st.button("📄 Generate Labels", type="primary", use_container_width=True):
                st.success(f"✅ {packages} label(s) generated!")
                st.caption("Labels would be generated via FedEx API in production")

# ============================================================================
# END OF PART 2
# ============================================================================
