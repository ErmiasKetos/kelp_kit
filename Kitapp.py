#!/usr/bin/env python3
"""
KELP Smart Kit Builder - COMPLETE UPDATED VERSION
With Multi-Package Support and Labor Exclusion

VERSION: 2.0 (Updated December 2025)

NEW FEATURES:
- Multi-package support (max 2 bottles per package)
- Automatic package splitting for orders with >2 bottles
- Per-package shipping cost calculation
- Labor cost excluded from price (but mentioned)
- Real-time FedEx rate calculation
- Smart bottle sharing (A+C modules)
- Automatic label generation
- Pick list with multi-package notes

CRITICAL RULES:
1. KELP kit box can only hold 2 bottles maximum
2. Orders with >2 bottles split into multiple packages
3. Each package gets own FedEx rate
4. Labor cost NOT included in customer price
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import requests
from typing import Dict, Optional, Tuple, List
import base64
import math

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
    
    UPDATED: Now supports multi-package rate calculation
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
                st.error(f"""
                **FedEx Authentication Failed**
                
                Status Code: {response.status_code}
                
                **Troubleshooting:**
                1. Verify your API Key and Secret Key in `.streamlit/secrets.toml`
                2. Check that your FedEx account is active
                3. **Meter Number Issue:** If meter number is "987654321" (1-9 backwards), this is a placeholder:
                   - Call FedEx Technical Support: 1-877-339-2774
                   - Request your actual meter number
                   - Update in secrets.toml
                4. Try using sandbox environment first
                
                **Demo Mode:** App will continue with estimated rates.
                """)
                return False
                
        except Exception as e:
            self.auth_failed = True
            st.error(f"FedEx authentication error: {str(e)}\n\nContinuing in demo mode.")
            return False
    
    def calculate_shipping_rate(self, destination: Dict, weight_lbs: float, 
                                service_type: str = "FEDEX_GROUND",
                                is_compliance: bool = False) -> Optional[Dict]:
        """
        Calculate shipping rate for a SINGLE package
        
        For multi-package orders, call this function multiple times
        
        Args:
            destination: Destination address dict
            weight_lbs: Weight of THIS package in pounds
            service_type: FedEx service type code
            is_compliance: Whether this includes compliance items
        
        Returns:
            Dict with rate info or None if failed
        """
        
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
        """
        Generate shipping label for ONE package
        
        Args:
            destination: Destination address dict
            weight_lbs: Weight of this package
            service_type: FedEx service type
            package_number: Which package this is (1 of N)
            total_packages: Total number of packages in shipment
        
        Returns:
            Dict with tracking number and label URL
        """
        
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
        
        # Real FedEx label generation
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
                        "address": self.origin,
                        "contact": {
                            "personName": "KELP Lab",
                            "phoneNumber": "4085551234"
                        }
                    },
                    "recipient": {
                        "address": destination,
                        "contact": {
                            "personName": destination.get('contact_name', 'Customer'),
                            "phoneNumber": destination.get('phone', '0000000000')
                        }
                    },
                    "pickupType": "USE_SCHEDULED_PICKUP",
                    "serviceType": service_type,
                    "packagingType": "YOUR_PACKAGING",
                    "shippingChargesPayment": {
                        "paymentType": "SENDER"
                    },
                    "labelSpecification": {
                        "labelFormatType": "COMMON2D",
                        "imageType": "PDF",
                        "labelStockType": "PAPER_4X6"
                    },
                    "requestedPackageLineItems": [
                        {
                            "sequenceNumber": package_number,
                            "weight": {
                                "units": "LB",
                                "value": weight_lbs
                            }
                        }
                    ],
                    "packageCount": total_packages
                }
            }
            
            response = requests.post(self.ship_url, headers=headers, json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'output' in data:
                    package_docs = data['output']['transactionShipments'][0]['pieceResponses'][0]
                    
                    return {
                        'tracking_number': package_docs['trackingNumber'],
                        'label_url': package_docs['packageDocuments'][0]['url'],
                        'package_number': package_number,
                        'total_packages': total_packages,
                        'demo_mode': False
                    }
            
            return None
            
        except Exception as e:
            st.error(f"Error generating label: {str(e)}")
            return None

# ============================================================================
# END OF PART 1
# ============================================================================
# ============================================================================
# PART 2: COMPONENT LIBRARY AND HELPER FUNCTIONS
# ============================================================================

# Component library with pricing and specifications
COMPONENT_LIBRARY = {
    'base': {
        'name': 'Base Kit Components',
        'cost': 9.50,
        'weight_lbs': 1.5,
        'items': [
            'Chain of Custody Form',
            'Sample Labels (waterproof)',
            'Nitrile Gloves (2 pairs)',
            'Bubble Wrap',
            'Insulated Shipping Box',
            'Sampling Instructions'
        ]
    },
    'module_a': {
        'name': 'Module A: General Chemistry',
        'cost': 2.50,
        'weight_lbs': 0.3,
        'bottle': '250mL HDPE unacidified',
        'bottle_cost': 2.50,
        'tests': ['Alkalinity', 'Hardness', 'TDS', 'pH', 'Conductivity']
    },
    'module_b': {
        'name': 'Module B: Metals (ICP-MS)',
        'cost': 5.00,
        'weight_lbs': 0.4,
        'bottle': '250mL HDPE acidified (HNO₃)',
        'bottle_cost': 5.00,
        'preservation': 'Pre-acidified with HNO₃',
        'tests': ['EPA 200.8 Metals Panel']
    },
    'module_c': {
        'name': 'Module C: Anions/Nutrients',
        'cost': 1.50,  # When NOT sharing
        'cost_shared': 0.00,  # When sharing with Module A
        'weight_lbs': 0.3,
        'bottle': '250mL HDPE unacidified (SHARED with A)',
        'bottle_cost': 1.50,
        'bottle_cost_shared': 0.00,
        'tests': ['Chloride', 'Sulfate', 'Nitrate', 'Phosphate']
    },
    'module_d': {
        'name': 'Module D: Nutrients (IC)',
        'cost': 4.00,
        'weight_lbs': 0.5,
        'bottle': '250mL PP acidified (H₂SO₄)',
        'bottle_cost': 4.00,
        'preservation': 'Pre-acidified with H₂SO₄',
        'tests': ['EPA 300.1 Nutrients']
    },
    'module_p': {
        'name': 'Module P: PFAS Testing',
        'cost': 15.50,
        'weight_lbs': 0.8,
        'bottle': '2× 250mL PP PFAS-certified',
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
MARKUP_FACTOR = 1.4  # 40% markup = 28.6% profit margin

# ============================================================================
# HELPER FUNCTIONS - UPDATED FOR MULTI-PACKAGE SUPPORT
# ============================================================================

def calculate_package_weight(selected_modules: List[str], bottle_count: int) -> Tuple[float, int]:
    """
    Calculate total package weight and number of packages needed.
    
    CRITICAL: KELP kit box can only hold 2 bottles maximum.
    If order has >2 bottles, split into multiple packages.
    
    Args:
        selected_modules: List of module IDs
        bottle_count: Total number of bottles needed
    
    Returns:
        tuple: (total_weight_lbs, package_count)
    """
    # Calculate packages needed (2 bottles per package max)
    # Use ceiling division: (bottle_count + 1) // 2
    package_count = max(1, (bottle_count + 1) // 2)
    
    # Weight per package
    base_weight = COMPONENT_LIBRARY['base']['weight_lbs']
    module_weight = sum(
        COMPONENT_LIBRARY[m].get('weight_lbs', 0) 
        for m in selected_modules 
        if m in COMPONENT_LIBRARY
    )
    
    # Total weight for all packages
    # Each package gets base kit + proportional module weight
    total_weight = (base_weight + module_weight) * package_count
    
    return round(total_weight, 2), package_count


def get_fedex_service_type(is_compliance: bool) -> str:
    """Get FedEx service type code based on compliance needs"""
    return "FEDEX_2_DAY" if is_compliance else "FEDEX_GROUND"


def count_bottles(selected_modules: List[str], sharing_active: bool) -> int:
    """
    Count total number of bottles needed
    
    Args:
        selected_modules: List of module IDs
        sharing_active: Whether A+C smart sharing is active
    
    Returns:
        int: Total bottle count
    """
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
    
    return bottles


def calculate_material_cost(selected_modules: List[str], sharing_active: bool, 
                            package_count: int) -> float:
    """
    Calculate total material cost including base kits for all packages
    
    Args:
        selected_modules: List of module IDs
        sharing_active: Whether A+C sharing is active
        package_count: Number of packages needed
    
    Returns:
        float: Total material cost
    """
    # Base kit cost × number of packages
    material_cost = COMPONENT_LIBRARY['base']['cost'] * package_count
    
    # Add module costs
    for module_key in selected_modules:
        if module_key == 'module_c' and sharing_active:
            # Module C is FREE when sharing with Module A
            material_cost += COMPONENT_LIBRARY[module_key]['cost_shared']
        elif module_key in COMPONENT_LIBRARY:
            material_cost += COMPONENT_LIBRARY[module_key]['cost']
    
    return round(material_cost, 2)


def estimate_shipping_cost(is_compliance: bool, package_count: int) -> float:
    """
    Estimate shipping cost when FedEx rate not available
    
    Args:
        is_compliance: Whether compliance shipping
        package_count: Number of packages
    
    Returns:
        float: Estimated total shipping cost
    """
    cost_per_package = 50.00 if is_compliance else 8.00
    return cost_per_package * package_count


def generate_pick_list(selected_modules: List[str], bottle_count: int, 
                       package_count: int, sharing_active: bool) -> Dict:
    """
    Generate comprehensive pick list for lab staff
    
    UPDATED: Now includes multi-package instructions
    
    Args:
        selected_modules: List of module IDs
        bottle_count: Total bottles needed
        package_count: Number of packages to prepare
        sharing_active: Whether A+C sharing is active
    
    Returns:
        Dict with pick list data
    """
    pick_list = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'package_count': package_count,
        'bottle_count': bottle_count,
        'assembly_time_estimate': ASSEMBLY_TIME_MINUTES * package_count,
        'base_components': COMPONENT_LIBRARY['base']['items'].copy(),
        'modules': [],
        'special_notes': []
    }
    
    # Multi-package warning
    if package_count > 1:
        pick_list['special_notes'].append(
            f"⚠️ MULTIPLE PACKAGES: Prepare {package_count} separate kits "
            f"({bottle_count} bottles total, max 2 bottles per package)"
        )
    
    # Module-specific items
    for module_key in selected_modules:
        if module_key not in COMPONENT_LIBRARY:
            continue
            
        module = COMPONENT_LIBRARY[module_key]
        module_info = {
            'module_id': module_key,
            'name': module['name'],
            'bottle': module.get('bottle', 'N/A'),
            'tests': module.get('tests', [])
        }
        
        # Special handling for Module C (sharing)
        if module_key == 'module_c':
            if sharing_active:
                module_info['note'] = "⚠️ SHARED BOTTLE - Use same bottle as Module A (Gen Chem)"
                module_info['bottle'] = "SHARED with Module A (no separate bottle)"
                module_info['action'] = "Label bottle: 'Gen Chem + Anions'"
            else:
                module_info['action'] = "Label bottle: 'Anions/Nutrients'"
        
        # Special handling for PFAS
        if module_key == 'module_p':
            module_info['note'] = "⚠️ PFAS SPECIAL HANDLING - Use PFAS-free gloves and containers"
            module_info['bottles_needed'] = 2
            pick_list['special_notes'].append(
                "🧪 PFAS Testing: Use PFAS-certified bottles and PFAS-free gloves"
            )
        
        # Preservation notes
        if 'preservation' in module:
            module_info['preservation'] = module['preservation']
        
        pick_list['modules'].append(module_info)
    
    # Smart sharing indicator
    if sharing_active:
        pick_list['special_notes'].append(
            "✅ SMART SHARING ACTIVE: Module C uses same bottle as Module A (1 bottle instead of 2)"
        )
    
    # Package distribution note
    if package_count > 1:
        pick_list['special_notes'].append(
            f"📦 Distribute {bottle_count} bottles across {package_count} packages "
            f"(max 2 bottles per package)"
        )
    
    return pick_list


def format_pick_list_display(pick_list: Dict) -> str:
    """
    Format pick list as readable string for display
    
    Args:
        pick_list: Pick list dictionary
    
    Returns:
        str: Formatted pick list text
    """
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
    
    # Base components (per package)
    output.append(f"BASE COMPONENTS (× {pick_list['package_count']} packages):")
    for item in pick_list['base_components']:
        output.append(f"  ☐ {item}")
    output.append(f"")
    
    # Modules
    output.append(f"MODULES:")
    for module in pick_list['modules']:
        output.append(f"  ☐ {module['name']}")
        output.append(f"     Bottle: {module['bottle']}")
        
        if 'note' in module:
            output.append(f"     ⚠️  {module['note']}")
        
        if 'action' in module:
            output.append(f"     → {module['action']}")
        
        if 'preservation' in module:
            output.append(f"     Preservation: {module['preservation']}")
        
        if 'bottles_needed' in module:
            output.append(f"     Bottles needed: {module['bottles_needed']}")
        
        output.append(f"")
    
    return "\n".join(output)


def calculate_total_shipping_cost(fedex_api: FedExAPI, destination: Dict, 
                                  weight_per_package: float, package_count: int,
                                  service_type: str, is_compliance: bool) -> Optional[Dict]:
    """
    Calculate total shipping cost for multiple packages
    
    Calls FedEx API once per package and sums results
    
    Args:
        fedex_api: FedEx API instance
        destination: Destination address
        weight_per_package: Weight of each package
        package_count: Number of packages
        service_type: FedEx service type
        is_compliance: Compliance shipping flag
    
    Returns:
        Dict with combined shipping info or None
    """
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
            # If any package fails, return None
            return None
    
    # Return combined info
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
# END OF PART 2
# ============================================================================
# ============================================================================
# PART 3: CSS STYLING AND SESSION STATE
# ============================================================================

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Module cards */
    .module-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #0066B2;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .module-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transition: all 0.3s ease;
    }
    
    /* Shared module highlight */
    .module-shared {
        border-left: 4px solid #00A86B;
        background: linear-gradient(90deg, rgba(0,168,107,0.05) 0%, white 100%);
    }
    
    /* PFAS special styling */
    .module-pfas {
        border-left: 4px solid #FF6B35;
        background: linear-gradient(90deg, rgba(255,107,53,0.05) 0%, white 100%);
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    
    .badge-success {
        background-color: #00A86B;
        color: white;
    }
    
    .badge-warning {
        background-color: #FFA500;
        color: white;
    }
    
    .badge-info {
        background-color: #0066B2;
        color: white;
    }
    
    /* Shipping card */
    .shipping-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #0066B2;
        margin: 1rem 0;
    }
    
    .shipping-card h3 {
        color: #0066B2;
        margin-top: 0;
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
    
    /* Multi-package warning */
    .multi-package-warning {
        background: #FFF3CD;
        border-left: 4px solid #FFA500;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    /* Pick list styling */
    .pick-list {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        white-space: pre-wrap;
        max-height: 500px;
        overflow-y: auto;
    }
    
    /* Cost summary */
    .cost-summary {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #0066B2;
        margin: 1rem 0;
    }
    
    /* Labor note styling */
    .labor-note {
        background: #E7F3FF;
        border-left: 3px solid #0066B2;
        padding: 0.75rem;
        margin-top: 1rem;
        border-radius: 4px;
        font-size: 0.9rem;
        color: #0066B2;
    }
    
    /* Metric styling */
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #0066B2;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        font-weight: 600;
    }
    
    /* Info boxes */
    .info-box {
        background: #E7F3FF;
        border-left: 4px solid #0066B2;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    /* Success boxes */
    .success-box {
        background: #E8F5E9;
        border-left: 4px solid #00A86B;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    /* Warning boxes */
    .warning-box {
        background: #FFF3CD;
        border-left: 4px solid #FFA500;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    /* Package indicator */
    .package-indicator {
        display: inline-block;
        background: #0066B2;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    /* Bottle count display */
    .bottle-count {
        font-size: 1.2rem;
        font-weight: bold;
        color: #00A86B;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

# Initialize session state variables
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
    st.session_state.show_costs = False  # Hide internal costs by default

# ============================================================================
# HEADER AND TITLE
# ============================================================================

# Header
st.title("🧪 KELP Smart Kit Builder Pro")
st.markdown("""
**Intelligent Water Testing Kit Configuration System**  
*With Multi-Package Support & Real-Time FedEx Integration*

---

### ✨ Key Features:
- 🎯 **Smart Bottle Sharing** - Module C FREE when ordered with Module A
- 📦 **Multi-Package Support** - Automatic splitting for orders >2 bottles
- 🚚 **Real-Time FedEx Rates** - Actual shipping costs per package
- 📋 **Automated Pick Lists** - Assembly instructions for lab staff
- 🏷️ **Label Generation** - Automatic FedEx shipping labels
""")

st.divider()

# Show/hide cost details toggle (for internal use)
col_toggle1, col_toggle2 = st.columns([3, 1])
with col_toggle2:
    st.session_state.show_costs = st.toggle("Show Cost Details", value=st.session_state.show_costs)

# Define modules to show (excluding Microbiology)
modules_to_show = ['module_a', 'module_b', 'module_c', 'module_d', 'module_p']

# ============================================================================
# END OF PART 3
# ============================================================================
# ============================================================================
# PART 4: SIDEBAR - ADDRESS INPUT AND CONTROLS
# ============================================================================

with st.sidebar:
    st.header("📍 Shipping Configuration")
    
    # Reset button at top
    if st.button("🔄 Reset All", use_container_width=True):
        st.session_state.modules_selected = {}
        st.session_state.shipping_address = None
        st.session_state.shipping_rate = None
        st.rerun()
    
    st.divider()
    
    # Address input
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
    
    # Save address button
    if st.button("💾 Save Address", type="primary", use_container_width=True):
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
    
    # Show saved address
    if st.session_state.shipping_address:
        st.divider()
        st.markdown("**Current Address:**")
        addr = st.session_state.shipping_address
        st.caption(f"{addr['city']}, {addr['stateOrProvinceCode']} {addr['postalCode']}")
        
        if st.button("🗑️ Clear Address", use_container_width=True):
            st.session_state.shipping_address = None
            st.session_state.shipping_rate = None
            st.rerun()
    
    st.divider()
    
    # Quick stats
    if st.session_state.modules_selected:
        selected_count = sum(1 for k, v in st.session_state.modules_selected.items() 
                           if v and k in modules_to_show)
        
        st.markdown("**Quick Stats:**")
        st.metric("Modules Selected", selected_count)
        
        # Calculate bottles
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
# MAIN CONTENT AREA
# ============================================================================

# Create two columns for layout
col_modules, col_summary = st.columns([2, 1])

# ============================================================================
# LEFT COLUMN: MODULE SELECTION
# ============================================================================

with col_modules:
    st.header("1️⃣ Select Test Modules")
    
    st.markdown("""
    Select the water testing modules you need. Smart sharing automatically 
    applies when Module A and Module C are both selected.
    """)
    
    st.divider()
    
    # Module A: General Chemistry
    with st.container():
        col_check, col_info = st.columns([1, 5])
        with col_check:
            module_a = st.checkbox(
                "",
                key="module_a",
                value=st.session_state.modules_selected.get('module_a', False)
            )
            st.session_state.modules_selected['module_a'] = module_a
        
        with col_info:
            st.markdown(f"""
            <div class="module-card">
                <h3 style="color: #0066B2; margin-top: 0;">Module A: General Chemistry</h3>
                <p><strong>Bottle:</strong> 250mL HDPE unacidified</p>
                <p><strong>Tests:</strong> Alkalinity, Hardness, TDS, pH, Conductivity</p>
                <p><strong>Cost:</strong> <span style="color: #00A86B; font-weight: bold;">${COMPONENT_LIBRARY['module_a']['cost']:.2f}</span></p>
            </div>
            """, unsafe_allow_html=True)
    
    # Module B: Metals
    with st.container():
        col_check, col_info = st.columns([1, 5])
        with col_check:
            module_b = st.checkbox(
                "",
                key="module_b",
                value=st.session_state.modules_selected.get('module_b', False)
            )
            st.session_state.modules_selected['module_b'] = module_b
        
        with col_info:
            st.markdown(f"""
            <div class="module-card">
                <h3 style="color: #0066B2; margin-top: 0;">Module B: Metals (ICP-MS)</h3>
                <p><strong>Bottle:</strong> 250mL HDPE pre-acidified (HNO₃)</p>
                <p><strong>Tests:</strong> EPA 200.8 Metals Panel</p>
                <p><strong>Cost:</strong> <span style="color: #00A86B; font-weight: bold;">${COMPONENT_LIBRARY['module_b']['cost']:.2f}</span></p>
                <span class="badge badge-info">Pre-Preserved</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Module C: Anions/Nutrients (with smart sharing)
    sharing_active = (st.session_state.modules_selected.get('module_a', False) and 
                     st.session_state.modules_selected.get('module_c', False))
    
    with st.container():
        col_check, col_info = st.columns([1, 5])
        with col_check:
            module_c = st.checkbox(
                "",
                key="module_c",
                value=st.session_state.modules_selected.get('module_c', False)
            )
            st.session_state.modules_selected['module_c'] = module_c
        
        with col_info:
            card_class = "module-card module-shared" if sharing_active else "module-card"
            cost_display = "$0.00 (FREE!)" if sharing_active else f"${COMPONENT_LIBRARY['module_c']['cost']:.2f}"
            
            st.markdown(f"""
            <div class="{card_class}">
                <h3 style="color: #0066B2; margin-top: 0;">Module C: Anions/Nutrients</h3>
                <p><strong>Bottle:</strong> {'SHARED with Module A' if sharing_active else '250mL HDPE unacidified'}</p>
                <p><strong>Tests:</strong> Chloride, Sulfate, Nitrate, Phosphate</p>
                <p><strong>Cost:</strong> <span style="color: #00A86B; font-weight: bold;">{cost_display}</span></p>
                {f'<span class="badge badge-success">✓ Smart Sharing Active</span>' if sharing_active else ''}
            </div>
            """, unsafe_allow_html=True)
            
            if sharing_active:
                st.success("✅ **Smart Sharing:** Module C uses the same bottle as Module A - FREE!")
    
    # Module D: Nutrients
    with st.container():
        col_check, col_info = st.columns([1, 5])
        with col_check:
            module_d = st.checkbox(
                "",
                key="module_d",
                value=st.session_state.modules_selected.get('module_d', False)
            )
            st.session_state.modules_selected['module_d'] = module_d
        
        with col_info:
            st.markdown(f"""
            <div class="module-card">
                <h3 style="color: #0066B2; margin-top: 0;">Module D: Nutrients (IC)</h3>
                <p><strong>Bottle:</strong> 250mL PP pre-acidified (H₂SO₄)</p>
                <p><strong>Tests:</strong> EPA 300.1 Nutrients</p>
                <p><strong>Cost:</strong> <span style="color: #00A86B; font-weight: bold;">${COMPONENT_LIBRARY['module_d']['cost']:.2f}</span></p>
                <span class="badge badge-info">Pre-Preserved</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Module P: PFAS
    with st.container():
        col_check, col_info = st.columns([1, 5])
        with col_check:
            module_p = st.checkbox(
                "",
                key="module_p",
                value=st.session_state.modules_selected.get('module_p', False)
            )
            st.session_state.modules_selected['module_p'] = module_p
        
        with col_info:
            st.markdown(f"""
            <div class="module-card module-pfas">
                <h3 style="color: #FF6B35; margin-top: 0;">Module P: PFAS Testing</h3>
                <p><strong>Bottles:</strong> 2× 250mL PP PFAS-certified</p>
                <p><strong>Tests:</strong> EPA 537.1/1633A PFAS Panel</p>
                <p><strong>Cost:</strong> <span style="color: #00A86B; font-weight: bold;">${COMPONENT_LIBRARY['module_p']['cost']:.2f}</span></p>
                <span class="badge badge-warning">⚠️ Special Handling</span>
                <span class="badge badge-info">2 Bottles</span>
            </div>
            """, unsafe_allow_html=True)
            
            if module_p:
                st.warning("⚠️ **PFAS Special Handling:** Requires PFAS-free gloves and certified containers")
    
    st.divider()
    
    # Compliance shipping option
    st.subheader("Shipping Options")
    
    compliance = st.checkbox(
        "**Compliance Shipping** (2-Day with cooler & ice packs)",
        key="compliance_shipping",
        value=st.session_state.modules_selected.get('compliance_shipping', False)
    )
    st.session_state.modules_selected['compliance_shipping'] = compliance
    
    if compliance:
        st.info("📦 Includes insulated cooler and ice packs for temperature-sensitive samples (+5 lbs per package)")

# ============================================================================
# END OF PART 4
# ============================================================================
# ============================================================================
# PART 5: SHIPPING CALCULATION WITH MULTI-PACKAGE SUPPORT
# ============================================================================

st.header("2️⃣ Calculate Shipping Rate")

# Get selected modules
selected_modules = [k for k in modules_to_show if st.session_state.modules_selected.get(k, False)]

if selected_modules:
    
    # Calculate bottle count and sharing status
    sharing_a_c = (st.session_state.modules_selected.get('module_a', False) and 
                   st.session_state.modules_selected.get('module_c', False))
    bottle_count = count_bottles(selected_modules, sharing_a_c)
    
    # Calculate package weight and count (CRITICAL: 2 bottles max per package)
    package_weight, package_count = calculate_package_weight(selected_modules, bottle_count)
    is_compliance = st.session_state.modules_selected.get('compliance_shipping', False)
    
    # Adjust weight for compliance (cooler + ice per package)
    if is_compliance:
        compliance_weight_per_pkg = 5.0  # Cooler + ice
        total_compliance_weight = compliance_weight_per_pkg * package_count
        display_weight = package_weight + total_compliance_weight
        package_weight_for_api = display_weight
    else:
        display_weight = package_weight
        package_weight_for_api = package_weight
    
    # Display package information with multi-package warning if needed
    if package_count > 1:
        st.markdown(f"""
        <div class="multi-package-warning">
            <h3 style="margin-top: 0;">⚠️ Multiple Packages Required</h3>
            <p><strong>{package_count} packages</strong> needed for {bottle_count} bottles</p>
            <p><em>KELP kit boxes can hold maximum 2 bottles per package</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info(f"""
        📦 **Package Breakdown:**
        - Total weight: **{display_weight} lbs** ({display_weight/package_count:.1f} lbs per package)
        - Bottles per package: {bottle_count // package_count} - {(bottle_count + package_count - 1) // package_count}
        {f'- Includes cooler & ice per package' if is_compliance else ''}
        """)
    else:
        st.info(f"""
        📦 **Package Details:**
        - Weight: **{display_weight} lbs**
        - Bottles: {bottle_count}
        - Packages: 1
        {f'- Includes cooler & ice' if is_compliance else ''}
        """)
    
    # Check if address is provided for FedEx rate calculation
    has_address = (st.session_state.shipping_address and 
                   'city' in st.session_state.shipping_address and 
                   'stateOrProvinceCode' in st.session_state.shipping_address and 
                   'postalCode' in st.session_state.shipping_address)
    
    if has_address:
        # Button to calculate shipping rate
        button_text = f"🔄 Get FedEx Rate for {package_count} Package{'s' if package_count > 1 else ''}"
        
        if st.button(button_text, type="primary", use_container_width=True):
            with st.spinner(f"Contacting FedEx API for {package_count} package{'s' if package_count > 1 else ''}..."):
                service_type = get_fedex_service_type(is_compliance)
                
                # Calculate rate for EACH package using helper function
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
                    st.success(f"✅ Rate calculated for {package_count} package{'s' if package_count > 1 else ''}!")
                    st.rerun()
                else:
                    st.error("❌ Failed to calculate shipping rate. Using estimated cost.")
        
        # Display rate if available
        if st.session_state.shipping_rate:
            rate = st.session_state.shipping_rate
            pkg_count = rate.get('package_count', 1)
            
            st.markdown(f"""
            <div class="shipping-card">
                <h3>📍 Shipping Details</h3>
                <p><strong>Service:</strong> {rate['service_name']}</p>
                <p><strong>Packages:</strong> {pkg_count} package{'s' if pkg_count > 1 else ''}</p>
                <p><strong>Destination:</strong> {st.session_state.shipping_address['city']}, {st.session_state.shipping_address['stateOrProvinceCode']} {st.session_state.shipping_address['postalCode']}</p>
                <p><strong>Transit Time:</strong> {rate.get('transit_time', 'N/A')}</p>
                <p><strong>Estimated Delivery:</strong> {rate.get('delivery_date', 'N/A')}</p>
                <div class="rate-display">
                    Total Shipping Cost: ${rate['total_charge']:.2f}
                </div>
                {f'<p style="text-align: center; color: #666; margin-top: 8px; font-size: 0.9rem;">(${rate.get("cost_per_package", 0):.2f} per package × {pkg_count})</p>' if pkg_count > 1 else ''}
                {f'<p style="text-align: center; color: #999; font-size: 0.85rem; margin-top: 8px;">Demo Mode - Using Estimated Rates</p>' if rate.get('demo_mode', False) else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("💡 **Enter shipping address in sidebar** to get real-time FedEx rates")
        
        # Show estimated costs
        estimated_cost = estimate_shipping_cost(is_compliance, package_count)
        st.caption(f"Estimated shipping: ${estimated_cost:.2f} for {package_count} package{'s' if package_count > 1 else ''}")

else:
    st.warning("⚠️ Please select at least one test module")

st.divider()

# ============================================================================
# RIGHT COLUMN: COST SUMMARY (WITH LABOR EXCLUSION)
# ============================================================================

with col_summary:
    st.header("💰 Cost Summary")
    
    if selected_modules:
        # Calculate costs with smart sharing
        material_cost = calculate_material_cost(selected_modules, sharing_a_c, package_count)
        
        # Use FedEx rate if available, otherwise estimate
        if st.session_state.shipping_rate:
            shipping_cost = st.session_state.shipping_rate['total_charge']
            shipping_label = f"FedEx (Actual) × {package_count}"
        else:
            # Estimate shipping per package
            shipping_cost = estimate_shipping_cost(is_compliance, package_count)
            shipping_label = f"Estimated × {package_count}"
        
        # CRITICAL: EXCLUDE LABOR FROM PRICE
        # Labor is mentioned but NOT included in customer price
        total_cost = material_cost + shipping_cost  # NO LABOR_COST
        customer_price = total_cost * MARKUP_FACTOR
        
        # Calculate labor info (for display only)
        total_labor_minutes = ASSEMBLY_TIME_MINUTES * package_count
        labor_cost_value = LABOR_COST * package_count  # For display only
        
        # Display metrics
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Modules", len(selected_modules))
            st.metric("Bottles", bottle_count)
        with col_m2:
            if package_count > 1:
                st.metric("Packages", package_count, 
                         delta=f"max 2 bottles/pkg", 
                         delta_color="off")
            else:
                st.metric("Package", 1)
        
        st.divider()
        
        # Customer price (large display)
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #0066B2 0%, #3399CC 100%); 
                    border-radius: 8px; color: white; margin: 1rem 0;">
            <div style="font-size: 0.9rem; opacity: 0.9; margin-bottom: 0.5rem;">CUSTOMER PRICE</div>
            <div style="font-size: 2.5rem; font-weight: bold;">${customer_price:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Cost breakdown (if enabled)
        if st.session_state.show_costs:
            st.markdown("---")
            st.caption("**Cost Breakdown:**")
            st.caption(f"• Material: ${material_cost:.2f}")
            if package_count > 1:
                base_per_pkg = COMPONENT_LIBRARY['base']['cost']
                st.caption(f"  (Base kit ${base_per_pkg:.2f} × {package_count})")
            st.caption(f"• Shipping ({shipping_label}): ${shipping_cost:.2f}")
            st.caption(f"**Total Cost:** ${total_cost:.2f}")
            st.caption(f"**Markup:** 1.{int((MARKUP_FACTOR-1)*100)}× (40%)")
        
        # Labor note (ALWAYS shown, but not in price)
        st.markdown(f"""
        <div class="labor-note">
            <strong>ℹ️ Assembly Labor:</strong> ~{total_labor_minutes} minutes
            <br/>
            <em style="font-size: 0.85rem;">({ASSEMBLY_TIME_MINUTES} min × {package_count} package{'s' if package_count > 1 else ''})</em>
            <br/>
            <strong style="font-size: 0.9rem;">Labor cost not included in price</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # Smart sharing indicator
        if sharing_a_c:
            st.success("✅ **Smart Sharing Active!**")
            st.caption("Module C uses same bottle as Module A")
            st.caption(f"Customer saves: ${COMPONENT_LIBRARY['module_c']['cost']:.2f}")
    else:
        st.info("Select modules to see cost summary")

# ============================================================================
# END OF PART 5
# ============================================================================
# ============================================================================
# PART 6: PICK LIST AND LABEL GENERATION
# ============================================================================

st.header("3️⃣ Generate Pick List")

if selected_modules:
    
    if st.button("📋 Generate Assembly Pick List", type="primary", use_container_width=True):
        # Generate pick list with multi-package support
        pick_list = generate_pick_list(
            selected_modules=selected_modules,
            bottle_count=bottle_count,
            package_count=package_count,
            sharing_active=sharing_a_c
        )
        
        # Format and display
        pick_list_text = format_pick_list_display(pick_list)
        
        st.success("✅ Pick list generated!")
        
        # Display in formatted box
        st.markdown(f"""
        <div class="pick-list">
{pick_list_text}
        </div>
        """, unsafe_allow_html=True)
        
        # Download button
        st.download_button(
            label="📥 Download Pick List",
            data=pick_list_text,
            file_name=f"KELP_PickList_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )
        
        # Multi-package assembly notes
        if package_count > 1:
            st.info(f"""
            **📦 Multi-Package Assembly Notes:**
            - Prepare {package_count} separate base kits
            - Distribute {bottle_count} bottles across packages (max 2 per package)
            - Each package needs its own shipping label
            - Total assembly time: ~{ASSEMBLY_TIME_MINUTES * package_count} minutes
            """)

else:
    st.warning("⚠️ Select modules to generate pick list")

st.divider()

# ============================================================================
# GENERATE SHIPPING LABELS
# ============================================================================

st.header("4️⃣ Generate Shipping Labels")

if st.session_state.shipping_address and selected_modules and st.session_state.shipping_rate:
    
    if st.button("📄 Generate FedEx Shipping Labels", type="primary", use_container_width=True):
        with st.spinner(f"Generating {package_count} shipping label{'s' if package_count > 1 else ''}..."):
            
            service_type = get_fedex_service_type(
                st.session_state.modules_selected.get('compliance_shipping', False)
            )
            
            weight_per_package = package_weight_for_api / package_count
            
            # Generate label for EACH package
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
                
                # Display each label
                for i, label in enumerate(labels, 1):
                    with st.expander(f"📦 Package {i} of {package_count}", expanded=(package_count == 1)):
                        col_l1, col_l2 = st.columns(2)
                        
                        with col_l1:
                            st.markdown(f"""
                            **Tracking Number:**  
                            `{label['tracking_number']}`
                            
                            **Package:** {label['package_number']} of {label['total_packages']}
                            
                            **Label URL:**  
                            [{label['label_url'][:50]}...]({label['label_url']})
                            """)
                        
                        with col_l2:
                            if label.get('demo_mode', False):
                                st.info("🎭 Demo Mode - Sample tracking number")
                            else:
                                st.success("✅ Real FedEx tracking")
                            
                            st.metric("Package", f"{i} of {package_count}")
                        
                        # Download button for this label
                        st.markdown(f"""
                        <a href="{label['label_url']}" target="_blank">
                            <button style="width: 100%; padding: 0.75rem; background: #0066B2; 
                                   color: white; border: none; border-radius: 4px; cursor: pointer; 
                                   font-weight: 600;">
                                📥 Download Label for Package {i}
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("<br/>", unsafe_allow_html=True)
                
                # Multi-package shipping reminder
                if package_count > 1:
                    st.warning(f"""
                    **⚠️ Multi-Package Shipment:**
                    - Print and affix {package_count} separate labels
                    - Each package must have its own tracking number
                    - All packages should be shipped together
                    - Customer will receive {package_count} tracking numbers
                    """)
            else:
                st.error("❌ Failed to generate labels")
    
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
# ORDER COMPLETION
# ============================================================================

st.header("5️⃣ Complete Order")

if selected_modules and st.session_state.shipping_rate:
    
    # Order summary
    st.subheader("Order Summary")
    
    col_sum1, col_sum2 = st.columns(2)
    
    with col_sum1:
        st.markdown("**Selected Modules:**")
        for module_key in selected_modules:
            module_name = COMPONENT_LIBRARY[module_key]['name']
            if module_key == 'module_c' and sharing_a_c:
                st.markdown(f"- {module_name} ✅ *FREE (shared)*")
            else:
                st.markdown(f"- {module_name}")
        
        st.markdown(f"\n**Bottles:** {bottle_count}")
        st.markdown(f"**Packages:** {package_count}")
    
    with col_sum2:
        st.markdown("**Destination:**")
        addr = st.session_state.shipping_address
        st.markdown(f"{addr['city']}, {addr['stateOrProvinceCode']} {addr['postalCode']}")
        
        st.markdown(f"\n**Shipping:** {st.session_state.shipping_rate['service_name']}")
        st.markdown(f"**Total Price:** ${customer_price:.2f}")
    
    st.divider()
    
    # Order buttons
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("💾 Save Order & Start New", type="primary", use_container_width=True):
            # Save to order history
            order = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'modules': selected_modules,
                'bottles': bottle_count,
                'packages': package_count,
                'sharing_active': sharing_a_c,
                'destination': f"{addr['city']}, {addr['stateOrProvinceCode']}",
                'shipping_cost': st.session_state.shipping_rate['total_charge'],
                'material_cost': material_cost,
                'customer_price': customer_price,
                'labor_minutes': ASSEMBLY_TIME_MINUTES * package_count
            }
            
            st.session_state.order_history.append(order)
            
            # Reset for new order
            st.session_state.modules_selected = {}
            st.session_state.shipping_address = None
            st.session_state.shipping_rate = None
            
            st.success("✅ Order saved! Ready for new order.")
            st.balloons()
            st.rerun()
    
    with col_btn2:
        if st.button("🔄 Reset (Don't Save)", use_container_width=True):
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
    
    # Convert to DataFrame
    history_df = pd.DataFrame(st.session_state.order_history)
    
    # Display summary
    st.metric("Total Orders", len(history_df))
    
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        st.metric("Total Revenue", f"${history_df['customer_price'].sum():.2f}")
    with col_h2:
        st.metric("Avg Order Value", f"${history_df['customer_price'].mean():.2f}")
    with col_h3:
        st.metric("Total Packages Shipped", int(history_df['packages'].sum()))
    
    # Show table
    with st.expander("📋 View Order Details"):
        display_df = history_df[[
            'timestamp', 'bottles', 'packages', 'destination', 
            'customer_price', 'labor_minutes'
        ]].copy()
        
        display_df.columns = [
            'Timestamp', 'Bottles', 'Packages', 'Destination',
            'Price', 'Labor (min)'
        ]
        
        st.dataframe(display_df, use_container_width=True)
        
        # Export button
        csv = history_df.to_csv(index=False)
        st.download_button(
            label="📥 Export Order History (CSV)",
            data=csv,
            file_name=f"KELP_Orders_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ============================================================================
# FOOTER
# ============================================================================

st.divider()

st.markdown("""
---
**KELP Smart Kit Builder Pro v2.0** | Multi-Package Support | December 2025  
*Powered by FedEx API Integration*

**System Features:**
- ✅ Smart bottle sharing (Module A + C)
- ✅ Multi-package support (max 2 bottles/package)
- ✅ Real-time FedEx rates
- ✅ Automatic label generation
- ✅ Labor tracking (excluded from price)
- ✅ Pick list automation

**Business Rules:**
- Maximum 2 bottles per package (KELP kit box capacity)
- Orders with >2 bottles automatically split into multiple packages
- Shipping calculated per package and summed
- Base kit included in each package
- Labor cost: ${LABOR_COST:.2f} per package (~{ASSEMBLY_TIME_MINUTES} minutes)
- Labor NOT included in customer price (internal tracking only)

---
""")

# ============================================================================
# END OF PART 6 - COMPLETE APP
# ============================================================================
