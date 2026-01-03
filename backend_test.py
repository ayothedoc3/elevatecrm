#!/usr/bin/env python3
"""
Backend API Testing for Elevate CRM - Elev8 CRM Entity Model
Tests Elev8 CRM APIs: Lead Scoring, Dual Pipelines, Partner Management, Lead Qualification Flow
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://elevate-pages.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin123"
TENANT_SLUG = "demo"

class Elev8CRMTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.admin_user_data = None
        self.test_results = []
        
        # Test data storage
        self.test_partner_id = None
        self.test_product_id = None
        self.test_lead_id = None
        self.test_company_id = None
        self.test_contact_id = None
        self.test_deal_id = None
        
    def log_test(self, test_name, success, details="", error=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "error": str(error) if error else None,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")
        print()
    
    def authenticate_admin(self):
        """Login as admin and get JWT token"""
        try:
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/auth/login?tenant_slug={TENANT_SLUG}",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                self.admin_user_data = data["user"]
                self.log_test("Admin Authentication", True, f"Logged in as {self.admin_user_data['email']}")
                return True
            else:
                self.log_test("Admin Authentication", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Admin Authentication", False, error=e)
            return False
    
    def test_health_check(self):
        """Test basic health endpoint"""
        try:
            response = self.session.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status')}")
                return True
            else:
                self.log_test("Health Check", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, error=e)
            return False
    
    # ==================== PIPELINE SETUP TESTS ====================
    
    def test_setup_elev8_pipelines(self):
        """Test POST /api/elev8/setup/pipelines - Create dual pipeline structure"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(f"{BACKEND_URL}/elev8/setup/pipelines", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Should return existing pipelines or create new ones
                if data.get("created") == False and "already exist" in data.get("message", ""):
                    self.log_test("POST /elev8/setup/pipelines", True, "Pipelines already exist (expected)")
                elif data.get("created") == True:
                    self.log_test("POST /elev8/setup/pipelines", True, "Pipelines created successfully")
                else:
                    self.log_test("POST /elev8/setup/pipelines", True, "Pipeline setup completed")
                return True
            else:
                self.log_test("POST /elev8/setup/pipelines", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/setup/pipelines", False, error=e)
            return False
    
    def test_get_elev8_pipelines(self):
        """Test GET /api/elev8/pipelines/elev8 - Get both Qualification and Sales pipelines"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/pipelines/elev8", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                qual_pipeline = data.get("qualification")
                sales_pipeline = data.get("sales")
                
                if qual_pipeline and sales_pipeline:
                    qual_stages = len(qual_pipeline.get("stages", []))
                    sales_stages = len(sales_pipeline.get("stages", []))
                    self.log_test("GET /elev8/pipelines/elev8", True, 
                                f"Retrieved dual pipelines: Qualification ({qual_stages} stages), Sales ({sales_stages} stages)")
                    return True
                else:
                    self.log_test("GET /elev8/pipelines/elev8", False, "Missing qualification or sales pipeline")
                    return False
            else:
                self.log_test("GET /elev8/pipelines/elev8", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/pipelines/elev8", False, error=e)
            return False
    
    # ==================== PARTNER MANAGEMENT TESTS ====================
    
    def test_list_partners(self):
        """Test GET /api/elev8/partners - List partners"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/partners", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                partners = data.get("partners", [])
                total = data.get("total", 0)
                
                # Look for Frylow partner
                frylow_partner = None
                for partner in partners:
                    if "frylow" in partner.get("name", "").lower():
                        frylow_partner = partner
                        break
                
                if frylow_partner:
                    self.log_test("GET /elev8/partners", True, f"Found {total} partners including 'Frylow' partner")
                else:
                    self.log_test("GET /elev8/partners", True, f"Retrieved {total} partners (no Frylow partner found)")
                return True
            else:
                self.log_test("GET /elev8/partners", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/partners", False, error=e)
            return False
    
    def test_create_partner(self):
        """Test POST /api/elev8/partners - Create a new partner"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            partner_data = {
                "name": "Test Partner Solutions",
                "partner_type": "channel",
                "status": "active",
                "description": "Test partner for Elev8 CRM testing",
                "territory": "North America",
                "primary_contact_name": "John Partner",
                "primary_contact_email": "john@testpartner.com",
                "primary_contact_phone": "555-0123"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/elev8/partners",
                json=partner_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                self.test_partner_id = data.get("id")
                self.log_test("POST /elev8/partners", True, f"Created partner: {data.get('name')} (ID: {self.test_partner_id})")
                return True
            else:
                self.log_test("POST /elev8/partners", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/partners", False, error=e)
            return False
    
    def test_get_partner_with_products(self):
        """Test GET /api/elev8/partners/{id} - Get partner with products"""
        if not self.test_partner_id:
            self.log_test("GET /elev8/partners/{id}", False, "No test partner ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/partners/{self.test_partner_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get("products", [])
                active_deals = data.get("active_deals", 0)
                won_deals = data.get("won_deals", 0)
                
                self.log_test("GET /elev8/partners/{id}", True, 
                            f"Retrieved partner with {len(products)} products, {active_deals} active deals, {won_deals} won deals")
                return True
            else:
                self.log_test("GET /elev8/partners/{id}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/partners/{id}", False, error=e)
            return False
    
    # ==================== PRODUCT MANAGEMENT TESTS ====================
    
    def test_list_products(self):
        """Test GET /api/elev8/products - List products"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/products", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get("products", [])
                total = data.get("total", 0)
                
                self.log_test("GET /elev8/products", True, f"Retrieved {total} products")
                return True
            else:
                self.log_test("GET /elev8/products", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/products", False, error=e)
            return False
    
    def test_list_products_by_partner(self):
        """Test GET /api/elev8/products?partner_id={id} - List products by partner"""
        if not self.test_partner_id:
            self.log_test("GET /elev8/products?partner_id", False, "No test partner ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/products?partner_id={self.test_partner_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get("products", [])
                
                self.log_test("GET /elev8/products?partner_id", True, f"Retrieved {len(products)} products for partner")
                return True
            else:
                self.log_test("GET /elev8/products?partner_id", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/products?partner_id", False, error=e)
            return False
    
    def test_create_product(self):
        """Test POST /api/elev8/products - Create product (requires partner_id)"""
        if not self.test_partner_id:
            self.log_test("POST /elev8/products", False, "No test partner ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            product_data = {
                "name": "Test CRM Solution",
                "partner_id": self.test_partner_id,
                "description": "Advanced CRM solution for testing",
                "category": "Software",
                "sku": "TEST-CRM-001",
                "base_price": 299.99,
                "currency": "USD",
                "pricing_model": "recurring",
                "economic_unit_label": "licenses",
                "usage_volume_label": "users",
                "is_active": True
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/elev8/products",
                json=product_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                self.test_product_id = data.get("id")
                self.log_test("POST /elev8/products", True, f"Created product: {data.get('name')} (ID: {self.test_product_id})")
                return True
            else:
                self.log_test("POST /elev8/products", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/products", False, error=e)
            return False
    
    # ==================== LEAD MANAGEMENT WITH SCORING TESTS ====================
    
    def test_list_leads(self):
        """Test GET /api/elev8/leads - List leads"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/leads", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                leads = data.get("leads", [])
                total = data.get("total", 0)
                
                self.log_test("GET /elev8/leads", True, f"Retrieved {total} leads")
                return True
            else:
                self.log_test("GET /elev8/leads", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/leads", False, error=e)
            return False
    
    def test_create_lead_partnership_sales(self):
        """Test POST /api/elev8/leads - Create lead with partnership_sales motion"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            lead_data = {
                "first_name": "Sarah",
                "last_name": "Business",
                "email": "sarah.business@testcompany.com",
                "phone": "555-0199",
                "company_name": "Test Restaurant Group",
                "title": "Operations Manager",
                "sales_motion_type": "partnership_sales",
                "source": "referral",
                "source_detail": "Partner referral from existing customer",
                "economic_units": 25,
                "usage_volume": 50,
                "urgency": 4,
                "trigger_event": "Expanding to new locations",
                "primary_motivation": "cost_reduction",
                "decision_role": "decision_maker",
                "decision_process_clarity": 3,
                "notes": "High-potential lead for partnership sales motion"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/elev8/leads",
                json=lead_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                self.test_lead_id = data.get("id")
                score = data.get("lead_score", 0)
                tier = data.get("tier", "")
                
                self.log_test("POST /elev8/leads (partnership_sales)", True, 
                            f"Created lead: {data.get('first_name')} {data.get('last_name')} (Score: {score}, Tier: {tier})")
                return True
            else:
                self.log_test("POST /elev8/leads (partnership_sales)", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/leads (partnership_sales)", False, error=e)
            return False
    
    def test_create_lead_partner_sales(self):
        """Test POST /api/elev8/leads - Create lead with partner_sales motion (requires partner_id and product_id)"""
        if not self.test_partner_id or not self.test_product_id:
            self.log_test("POST /elev8/leads (partner_sales)", False, "Missing partner_id or product_id")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            lead_data = {
                "first_name": "Mike",
                "last_name": "Technology",
                "email": "mike.tech@techcorp.com",
                "phone": "555-0188",
                "company_name": "Tech Corp Solutions",
                "title": "CTO",
                "sales_motion_type": "partner_sales",
                "partner_id": self.test_partner_id,
                "product_id": self.test_product_id,
                "source": "inbound_demo",
                "economic_units": 15,
                "usage_volume": 100,
                "urgency": 5,
                "trigger_event": "System modernization project",
                "primary_motivation": "efficiency",
                "decision_role": "economic_buyer",
                "decision_process_clarity": 4,
                "notes": "Partner sales motion with specific product interest"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/elev8/leads",
                json=lead_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                score = data.get("lead_score", 0)
                tier = data.get("tier", "")
                
                self.log_test("POST /elev8/leads (partner_sales)", True, 
                            f"Created partner sales lead: {data.get('first_name')} {data.get('last_name')} (Score: {score}, Tier: {tier})")
                return True
            else:
                self.log_test("POST /elev8/leads (partner_sales)", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/leads (partner_sales)", False, error=e)
            return False
    
    def test_get_lead_with_score_and_tier(self):
        """Test GET /api/elev8/leads/{id} - Get lead with calculated score and tier"""
        if not self.test_lead_id:
            self.log_test("GET /elev8/leads/{id}", False, "No test lead ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/leads/{self.test_lead_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                score = data.get("lead_score", 0)
                tier = data.get("tier", "")
                status = data.get("status", "")
                
                self.log_test("GET /elev8/leads/{id}", True, 
                            f"Retrieved lead with score: {score}, tier: {tier}, status: {status}")
                return True
            else:
                self.log_test("GET /elev8/leads/{id}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/leads/{id}", False, error=e)
            return False
    
    def test_update_lead_recalculate_score(self):
        """Test PUT /api/elev8/leads/{id} - Update lead (should recalculate score)"""
        if not self.test_lead_id:
            self.log_test("PUT /elev8/leads/{id}", False, "No test lead ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            update_data = {
                "urgency": 5,
                "economic_units": 50,
                "primary_motivation": "revenue_growth",
                "decision_process_clarity": 5
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/elev8/leads/{self.test_lead_id}",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                new_score = data.get("lead_score", 0)
                new_tier = data.get("tier", "")
                
                self.log_test("PUT /elev8/leads/{id}", True, 
                            f"Updated lead - new score: {new_score}, new tier: {new_tier}")
                return True
            else:
                self.log_test("PUT /elev8/leads/{id}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("PUT /elev8/leads/{id}", False, error=e)
            return False
    
    def test_get_lead_scoring_stats(self):
        """Test GET /api/elev8/leads/scoring/stats - Get tier distribution statistics"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/leads/scoring/stats", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                tier_distribution = data.get("tier_distribution", {})
                total_leads = data.get("total_leads", 0)
                
                tier_counts = {tier: info.get("count", 0) for tier, info in tier_distribution.items()}
                self.log_test("GET /elev8/leads/scoring/stats", True, 
                            f"Tier distribution - Total: {total_leads}, A: {tier_counts.get('A', 0)}, B: {tier_counts.get('B', 0)}, C: {tier_counts.get('C', 0)}, D: {tier_counts.get('D', 0)}")
                return True
            else:
                self.log_test("GET /elev8/leads/scoring/stats", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/leads/scoring/stats", False, error=e)
            return False
    
    # ==================== LEAD QUALIFICATION FLOW TESTS (CRITICAL) ====================
    
    def test_qualify_lead_validation(self):
        """Test POST /api/elev8/leads/{id}/qualify - Should validate required fields"""
        if not self.test_lead_id:
            self.log_test("POST /elev8/leads/{id}/qualify (validation)", False, "No test lead ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # First, create a lead without required qualification fields
            incomplete_lead_data = {
                "first_name": "Incomplete",
                "last_name": "Lead",
                "email": "incomplete@test.com",
                "sales_motion_type": "partnership_sales"
                # Missing: economic_units, usage_volume, urgency, decision_role
            }
            
            create_response = self.session.post(
                f"{BACKEND_URL}/elev8/leads",
                json=incomplete_lead_data,
                headers=headers
            )
            
            if create_response.status_code == 201:
                incomplete_lead = create_response.json()
                incomplete_lead_id = incomplete_lead.get("id")
                
                # Try to qualify the incomplete lead
                qualify_response = self.session.post(
                    f"{BACKEND_URL}/elev8/leads/{incomplete_lead_id}/qualify",
                    headers=headers
                )
                
                if qualify_response.status_code == 400:
                    error_data = qualify_response.json()
                    if "Missing required fields" in error_data.get("detail", ""):
                        self.log_test("POST /elev8/leads/{id}/qualify (validation)", True, 
                                    "Correctly validated required fields for qualification")
                        return True
                    else:
                        self.log_test("POST /elev8/leads/{id}/qualify (validation)", False, 
                                    f"Wrong validation error: {error_data.get('detail')}")
                        return False
                else:
                    self.log_test("POST /elev8/leads/{id}/qualify (validation)", False, 
                                f"Expected 400 validation error, got {qualify_response.status_code}")
                    return False
            else:
                self.log_test("POST /elev8/leads/{id}/qualify (validation)", False, 
                            f"Failed to create incomplete lead: {create_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/leads/{id}/qualify (validation)", False, error=e)
            return False
    
    def test_qualify_lead_success(self):
        """Test POST /api/elev8/leads/{id}/qualify - Should create Company, Contact, and Deal"""
        if not self.test_lead_id:
            self.log_test("POST /elev8/leads/{id}/qualify (success)", False, "No test lead ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(f"{BACKEND_URL}/elev8/leads/{self.test_lead_id}/qualify", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                deal_id = data.get("deal_id")
                contact_id = data.get("contact_id")
                company_id = data.get("company_id")
                
                if deal_id and contact_id:
                    self.test_deal_id = deal_id
                    self.test_contact_id = contact_id
                    self.test_company_id = company_id
                    
                    self.log_test("POST /elev8/leads/{id}/qualify (success)", True, 
                                f"Lead qualified successfully - Deal: {deal_id}, Contact: {contact_id}, Company: {company_id}")
                    return True
                else:
                    self.log_test("POST /elev8/leads/{id}/qualify (success)", False, 
                                "Missing deal_id or contact_id in response")
                    return False
            else:
                self.log_test("POST /elev8/leads/{id}/qualify (success)", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/leads/{id}/qualify (success)", False, error=e)
            return False
    
    def test_record_touchpoint(self):
        """Test POST /api/elev8/leads/{id}/touchpoint - Record touchpoint"""
        if not self.test_lead_id:
            self.log_test("POST /elev8/leads/{id}/touchpoint", False, "No test lead ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(f"{BACKEND_URL}/elev8/leads/{self.test_lead_id}/touchpoint", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /elev8/leads/{id}/touchpoint", True, "Touchpoint recorded successfully")
                return True
            else:
                self.log_test("POST /elev8/leads/{id}/touchpoint", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/leads/{id}/touchpoint", False, error=e)
            return False
    
    # ==================== COMPANY MANAGEMENT TESTS ====================
    
    def test_list_companies(self):
        """Test GET /api/elev8/companies - List companies"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/companies", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                companies = data.get("companies", [])
                total = data.get("total", 0)
                
                self.log_test("GET /elev8/companies", True, f"Retrieved {total} companies")
                return True
            else:
                self.log_test("GET /elev8/companies", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/companies", False, error=e)
            return False
    
    def test_create_company(self):
        """Test POST /api/elev8/companies - Create company"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            company_data = {
                "name": "Test Enterprise Corp",
                "industry": "Technology",
                "website": "https://testenterprise.com",
                "phone": "555-0100",
                "address_line1": "123 Business Ave",
                "city": "Business City",
                "state": "CA",
                "postal_code": "90210",
                "country": "USA",
                "employee_count": 500,
                "annual_revenue": 10000000,
                "notes": "Test company for Elev8 CRM testing"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/elev8/companies",
                json=company_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                company_id = data.get("id")
                self.log_test("POST /elev8/companies", True, f"Created company: {data.get('name')} (ID: {company_id})")
                return True
            else:
                self.log_test("POST /elev8/companies", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/companies", False, error=e)
            return False
    
    # ==================== LEAD SCORING VALIDATION TESTS ====================
    
    def test_lead_scoring_tiers(self):
        """Test lead scoring validation - Create leads with different scoring combinations"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Test cases for different tiers
            test_cases = [
                {
                    "name": "Tier A Lead",
                    "data": {
                        "first_name": "High", "last_name": "Score",
                        "email": "high@score.com", "company_name": "High Score Corp",
                        "sales_motion_type": "partnership_sales",
                        "economic_units": 100, "usage_volume": 200, "urgency": 5,
                        "source": "referral", "primary_motivation": "revenue_growth",
                        "decision_role": "decision_maker", "decision_process_clarity": 5,
                        "trigger_event": "Major expansion project"
                    },
                    "expected_tier": "A"
                },
                {
                    "name": "Tier B Lead", 
                    "data": {
                        "first_name": "Medium", "last_name": "Score",
                        "email": "medium@score.com", "company_name": "Medium Score Inc",
                        "sales_motion_type": "partnership_sales",
                        "economic_units": 25, "usage_volume": 50, "urgency": 3,
                        "source": "inbound_demo", "primary_motivation": "efficiency",
                        "decision_role": "influencer", "decision_process_clarity": 3
                    },
                    "expected_tier": "B"
                },
                {
                    "name": "Tier C Lead",
                    "data": {
                        "first_name": "Low", "last_name": "Score", 
                        "email": "low@score.com", "company_name": "Low Score LLC",
                        "sales_motion_type": "partnership_sales",
                        "economic_units": 5, "usage_volume": 10, "urgency": 2,
                        "source": "cold_outreach", "primary_motivation": "other",
                        "decision_role": "user", "decision_process_clarity": 2
                    },
                    "expected_tier": "C"
                }
            ]
            
            results = []
            for test_case in test_cases:
                response = self.session.post(
                    f"{BACKEND_URL}/elev8/leads",
                    json=test_case["data"],
                    headers=headers
                )
                
                if response.status_code == 201:
                    data = response.json()
                    actual_tier = data.get("tier")
                    score = data.get("lead_score", 0)
                    
                    # Verify tier ranges
                    tier_valid = False
                    if actual_tier == "A" and score >= 80:
                        tier_valid = True
                    elif actual_tier == "B" and 60 <= score < 80:
                        tier_valid = True
                    elif actual_tier == "C" and 40 <= score < 60:
                        tier_valid = True
                    elif actual_tier == "D" and score < 40:
                        tier_valid = True
                    
                    results.append({
                        "name": test_case["name"],
                        "score": score,
                        "tier": actual_tier,
                        "valid": tier_valid
                    })
                else:
                    results.append({
                        "name": test_case["name"],
                        "error": f"Failed to create: {response.status_code}"
                    })
            
            # Check results
            all_valid = all(r.get("valid", False) for r in results if "error" not in r)
            if all_valid:
                tier_summary = ", ".join([f"{r['name']}: {r['score']} ({r['tier']})" for r in results if "error" not in r])
                self.log_test("Lead Scoring Tier Validation", True, f"All tiers correctly calculated: {tier_summary}")
                return True
            else:
                failed = [r for r in results if not r.get("valid", True)]
                self.log_test("Lead Scoring Tier Validation", False, f"Invalid tier calculations: {failed}")
                return False
                
        except Exception as e:
            self.log_test("Lead Scoring Tier Validation", False, error=e)
            return False
    
    def run_all_tests(self):
        """Run all Settings Module tests"""
        print("🚀 Starting Settings Module API Tests")
        print("=" * 70)
        print("Testing: Workspace Settings + AI Config + Integrations + Affiliates + Audit Logs + Providers")
        print("=" * 70)
        
        # Authentication is required for all tests
        if not self.authenticate_admin():
            print("❌ Admin authentication failed. Cannot proceed with tests.")
            return False
        
        # Test basic health
        self.test_health_check()
        
        print("\n🏢 WORKSPACE SETTINGS API TESTS")
        print("-" * 50)
        self.test_get_workspace_settings()
        self.test_update_workspace_settings()
        
        print("\n🤖 AI CONFIGURATION API TESTS")
        print("-" * 50)
        self.test_get_ai_config()
        self.test_update_ai_config()
        self.test_get_ai_usage_stats()
        self.test_get_ai_status()
        
        print("\n🔐 INTEGRATIONS API TESTS (CRITICAL SECURITY)")
        print("-" * 50)
        self.test_list_integrations()
        self.test_add_integration()
        self.test_get_specific_integration()
        self.test_toggle_integration()
        self.test_integration_connection()
        self.test_revoke_integration()
        
        print("\n📋 PROVIDERS INFO API TESTS")
        print("-" * 50)
        self.test_list_providers()
        
        print("\n💰 AFFILIATE SETTINGS API TESTS")
        print("-" * 50)
        self.test_get_affiliate_settings()
        self.test_update_affiliate_settings()
        
        print("\n📊 AUDIT LOGS API TESTS")
        print("-" * 50)
        self.test_get_audit_logs()
        
        print("\n🔒 SECURITY VERIFICATION TESTS")
        print("-" * 50)
        self.test_non_admin_access_denied()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['error'] or test['details']}")
        else:
            print("\n✅ ALL TESTS PASSED!")
        
        return passed == total

def main():
    """Main test runner"""
    tester = SettingsModuleTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()