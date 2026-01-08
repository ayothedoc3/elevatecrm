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
BACKEND_URL = "https://elev8crm.preview.emergentagent.com/api"
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
        self.test_task_id = None
        
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
    
    # ==================== TASK MANAGEMENT TESTS ====================
    
    def test_create_task(self):
        """Test POST /api/elev8/tasks - Create a task"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            task_data = {
                "title": "Follow up with Test Restaurant Group",
                "description": "Schedule discovery call to discuss Frylow implementation",
                "task_type": "call",
                "priority": "high",
                "due_date": "2024-12-31T10:00:00Z",
                "deal_id": self.test_deal_id if self.test_deal_id else None,
                "assigned_to": self.admin_user_data["id"]  # Assign to current user
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/elev8/tasks",
                json=task_data,
                headers=headers
            )
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                self.test_task_id = data.get("id")
                self.log_test("POST /elev8/tasks", True, f"Created task: {data.get('title')} (ID: {self.test_task_id})")
                return True
            else:
                self.log_test("POST /elev8/tasks", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/tasks", False, error=e)
            return False
    
    def test_list_tasks(self):
        """Test GET /api/elev8/tasks - List tasks with filtering"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/tasks", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                tasks = data.get("tasks", [])
                total = data.get("total", 0)
                
                self.log_test("GET /elev8/tasks", True, f"Retrieved {total} tasks")
                return True
            else:
                self.log_test("GET /elev8/tasks", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/tasks", False, error=e)
            return False
    
    def test_get_task(self):
        """Test GET /api/elev8/tasks/{task_id} - Get specific task"""
        if not hasattr(self, 'test_task_id') or not self.test_task_id:
            self.log_test("GET /elev8/tasks/{id}", False, "No test task ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/tasks/{self.test_task_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("GET /elev8/tasks/{id}", True, f"Retrieved task: {data.get('title')}")
                return True
            else:
                self.log_test("GET /elev8/tasks/{id}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/tasks/{id}", False, error=e)
            return False
    
    def test_update_task(self):
        """Test PUT /api/elev8/tasks/{task_id} - Update a task"""
        if not hasattr(self, 'test_task_id') or not self.test_task_id:
            self.log_test("PUT /elev8/tasks/{id}", False, "No test task ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            update_data = {
                "priority": "urgent",
                "description": "Updated: High priority follow-up call needed ASAP"
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/elev8/tasks/{self.test_task_id}",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("PUT /elev8/tasks/{id}", True, f"Updated task priority to: {data.get('priority')}")
                return True
            else:
                self.log_test("PUT /elev8/tasks/{id}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("PUT /elev8/tasks/{id}", False, error=e)
            return False
    
    def test_complete_task(self):
        """Test POST /api/elev8/tasks/{task_id}/complete - Complete a task"""
        if not hasattr(self, 'test_task_id') or not self.test_task_id:
            self.log_test("POST /elev8/tasks/{id}/complete", False, "No test task ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(
                f"{BACKEND_URL}/elev8/tasks/{self.test_task_id}/complete",
                json={"notes": "Task completed successfully - call scheduled for next week"},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /elev8/tasks/{id}/complete", True, f"Task completed at: {data.get('completed_at')}")
                return True
            else:
                self.log_test("POST /elev8/tasks/{id}/complete", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/tasks/{id}/complete", False, error=e)
            return False
    
    def test_get_my_tasks(self):
        """Test GET /api/elev8/tasks/my-tasks - Get current user's tasks"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/tasks/my-tasks", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                overdue = len(data.get("overdue", []))
                due_today = len(data.get("due_today", []))
                upcoming = len(data.get("upcoming", []))
                total = data.get("total_pending", 0)
                
                self.log_test("GET /elev8/tasks/my-tasks", True, 
                            f"My tasks - Overdue: {overdue}, Due today: {due_today}, Upcoming: {upcoming}, Total: {total}")
                return True
            else:
                self.log_test("GET /elev8/tasks/my-tasks", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/tasks/my-tasks", False, error=e)
            return False
    
    # ==================== SLA MANAGEMENT TESTS ====================
    
    def test_get_sla_config(self):
        """Test GET /api/elev8/sla/config - Get SLA configuration"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/sla/config", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                configs = data.get("sla_configs", [])
                self.log_test("GET /elev8/sla/config", True, f"Retrieved {len(configs)} SLA configurations")
                return True
            else:
                self.log_test("GET /elev8/sla/config", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/sla/config", False, error=e)
            return False
    
    def test_create_sla_config(self):
        """Test POST /api/elev8/sla/config - Create SLA config (admin only)"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            sla_data = {
                "name": "High Priority Lead Response",
                "source": "referral",
                "max_hours": 2,
                "escalation_hours": 1,
                "applies_to": "leads"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/elev8/sla/config",
                json=sla_data,
                headers=headers
            )
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                self.log_test("POST /elev8/sla/config", True, f"Created SLA config: {data.get('name')}")
                return True
            else:
                self.log_test("POST /elev8/sla/config", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/sla/config", False, error=e)
            return False
    
    def test_get_sla_status_deals(self):
        """Test GET /api/elev8/sla/status?entity_type=deals - Get SLA status for deals"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/sla/status?entity_type=deals", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get("total_count", 0)
                compliant = data.get("compliant_count", 0)
                at_risk = data.get("at_risk_count", 0)
                breached = data.get("breached_count", 0)
                
                self.log_test("GET /elev8/sla/status (deals)", True, 
                            f"Deal SLA status - Total: {total}, Compliant: {compliant}, At Risk: {at_risk}, Breached: {breached}")
                return True
            else:
                self.log_test("GET /elev8/sla/status (deals)", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/sla/status (deals)", False, error=e)
            return False
    
    def test_get_sla_status_leads(self):
        """Test GET /api/elev8/sla/status?entity_type=leads - Get SLA status for leads"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/sla/status?entity_type=leads", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get("total_count", 0)
                compliant = data.get("compliant_count", 0)
                at_risk = data.get("at_risk_count", 0)
                breached = data.get("breached_count", 0)
                
                self.log_test("GET /elev8/sla/status (leads)", True, 
                            f"Lead SLA status - Total: {total}, Compliant: {compliant}, At Risk: {at_risk}, Breached: {breached}")
                return True
            else:
                self.log_test("GET /elev8/sla/status (leads)", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/sla/status (leads)", False, error=e)
            return False
    
    # ==================== PARTNER CONFIGURATION TESTS ====================
    
    def test_get_partner_config(self):
        """Test GET /api/elev8/partners/{partner_id}/config - Get partner config"""
        if not self.test_partner_id:
            self.log_test("GET /elev8/partners/{id}/config", False, "No test partner ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/partners/{self.test_partner_id}/config", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                partner_name = data.get("partner_name")
                pipeline_config = data.get("pipeline_config", {})
                field_config = data.get("field_config", {})
                kpi_config = data.get("kpi_config", {})
                
                self.log_test("GET /elev8/partners/{id}/config", True, 
                            f"Retrieved config for partner: {partner_name}")
                return True
            else:
                self.log_test("GET /elev8/partners/{id}/config", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/partners/{id}/config", False, error=e)
            return False
    
    def test_update_partner_config(self):
        """Test PUT /api/elev8/partners/{partner_id}/config - Update partner config (admin only)"""
        if not self.test_partner_id:
            self.log_test("PUT /elev8/partners/{id}/config", False, "No test partner ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            config_data = {
                "kpi_config": {
                    "target_win_rate": 30.0,
                    "target_deal_size": 7500.0,
                    "target_cycle_days": 35,
                    "target_qualification_rate": 35.0
                },
                "field_config": {
                    "required_at_qualification": ["economic_units", "urgency", "decision_role"],
                    "required_at_discovery": ["spiced_situation", "spiced_pain", "spiced_impact"]
                }
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/elev8/partners/{self.test_partner_id}/config",
                json=config_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("PUT /elev8/partners/{id}/config", True, "Partner configuration updated successfully")
                return True
            else:
                self.log_test("PUT /elev8/partners/{id}/config", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("PUT /elev8/partners/{id}/config", False, error=e)
            return False
    
    def test_get_partner_kpis(self):
        """Test GET /api/elev8/partners/{partner_id}/kpis - Get partner-specific KPIs"""
        if not self.test_partner_id:
            self.log_test("GET /elev8/partners/{id}/kpis", False, "No test partner ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/partners/{self.test_partner_id}/kpis", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                metrics = data.get("metrics", {})
                targets = data.get("targets", {})
                performance = data.get("performance", {})
                
                self.log_test("GET /elev8/partners/{id}/kpis", True, 
                            f"Partner KPIs - Win Rate: {metrics.get('win_rate', 0)}%, Pipeline: ${metrics.get('pipeline_value', 0)}")
                return True
            else:
                self.log_test("GET /elev8/partners/{id}/kpis", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/partners/{id}/kpis", False, error=e)
            return False
    
    def test_check_partner_compliance(self):
        """Test GET /api/elev8/partners/{partner_id}/compliance-check - Check partner compliance"""
        if not self.test_partner_id:
            self.log_test("GET /elev8/partners/{id}/compliance-check", False, "No test partner ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/partners/{self.test_partner_id}/compliance-check", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                is_compliant = data.get("is_compliant", True)
                checks = data.get("checks", [])
                
                self.log_test("GET /elev8/partners/{id}/compliance-check", True, 
                            f"Partner compliance - Compliant: {is_compliant}, Checks: {len(checks)}")
                return True
            else:
                self.log_test("GET /elev8/partners/{id}/compliance-check", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/partners/{id}/compliance-check", False, error=e)
            return False
    
    def test_get_fields_by_stage(self):
        """Test GET /api/elev8/config/fields-by-stage?stage=Discovery - Get required fields by stage"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/config/fields-by-stage?stage=Discovery", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                stage = data.get("stage")
                required_fields = data.get("required_fields", [])
                
                self.log_test("GET /elev8/config/fields-by-stage", True, 
                            f"Stage '{stage}' requires {len(required_fields)} fields: {', '.join(required_fields[:3])}")
                return True
            else:
                self.log_test("GET /elev8/config/fields-by-stage", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/config/fields-by-stage", False, error=e)
            return False
    
    # ==================== HANDOFF TO DELIVERY TESTS ====================
    
    def test_get_handoff_status(self):
        """Test GET /api/elev8/deals/{deal_id}/handoff-status - Get handoff status"""
        if not self.test_deal_id:
            self.log_test("GET /elev8/deals/{id}/handoff-status", False, "No test deal ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/deals/{self.test_deal_id}/handoff-status", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                deal_name = data.get("deal_name")
                readiness_percentage = data.get("readiness_percentage", 0)
                has_spiced = data.get("has_spiced", False)
                can_complete = data.get("can_complete", False)
                
                self.log_test("GET /elev8/deals/{id}/handoff-status", True, 
                            f"Deal '{deal_name}' handoff readiness: {readiness_percentage}%, SPICED: {has_spiced}")
                return True
            else:
                self.log_test("GET /elev8/deals/{id}/handoff-status", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/deals/{id}/handoff-status", False, error=e)
            return False
    
    def test_initiate_handoff_validation(self):
        """Test POST /api/elev8/deals/{deal_id}/handoff/initiate - Should require won deal"""
        if not self.test_deal_id:
            self.log_test("POST /elev8/deals/{id}/handoff/initiate (validation)", False, "No test deal ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            handoff_data = {
                "delivery_owner_id": self.admin_user_data["id"],
                "kickoff_date": "2024-12-31T09:00:00Z",
                "notes": "Test handoff initiation"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/elev8/deals/{self.test_deal_id}/handoff/initiate",
                json=handoff_data,
                headers=headers
            )
            
            # Should fail because deal is not won
            if response.status_code == 400:
                error_data = response.json()
                if "Closed Won" in error_data.get("detail", ""):
                    self.log_test("POST /elev8/deals/{id}/handoff/initiate (validation)", True, 
                                "Correctly validated that handoff requires Closed Won deal")
                    return True
                else:
                    self.log_test("POST /elev8/deals/{id}/handoff/initiate (validation)", False, 
                                f"Wrong validation error: {error_data.get('detail')}")
                    return False
            else:
                self.log_test("POST /elev8/deals/{id}/handoff/initiate (validation)", False, 
                            f"Expected 400 validation error, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("POST /elev8/deals/{id}/handoff/initiate (validation)", False, error=e)
            return False
    
    def test_update_handoff_artifact(self):
        """Test PUT /api/elev8/deals/{deal_id}/handoff/artifact - Update handoff artifact"""
        if not self.test_deal_id:
            self.log_test("PUT /elev8/deals/{id}/handoff/artifact", False, "No test deal ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            artifact_data = {
                "title": "Test Gap Analysis Document",
                "content": "Comprehensive gap analysis completed for customer requirements",
                "completed": True
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/elev8/deals/{self.test_deal_id}/handoff/artifact?artifact_type=gap_analysis",
                json=artifact_data,
                headers=headers
            )
            
            # This should fail because handoff not initiated yet
            if response.status_code == 404:
                self.log_test("PUT /elev8/deals/{id}/handoff/artifact", True, 
                            "Correctly validated that handoff must be initiated first")
                return True
            elif response.status_code == 200:
                data = response.json()
                self.log_test("PUT /elev8/deals/{id}/handoff/artifact", True, 
                            f"Updated artifact: {data.get('artifact', {}).get('title')}")
                return True
            else:
                self.log_test("PUT /elev8/deals/{id}/handoff/artifact", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("PUT /elev8/deals/{id}/handoff/artifact", False, error=e)
            return False
    
    def test_list_handoffs(self):
        """Test GET /api/elev8/handoffs - List all handoffs"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/elev8/handoffs", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                handoffs = data.get("handoffs", [])
                total = data.get("total", 0)
                
                self.log_test("GET /elev8/handoffs", True, f"Retrieved {total} handoffs")
                return True
            else:
                self.log_test("GET /elev8/handoffs", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /elev8/handoffs", False, error=e)
            return False

    def run_all_tests(self):
        """Run all Elev8 CRM tests including remaining features"""
        print("🚀 Starting Comprehensive Elev8 CRM API Tests")
        print("=" * 80)
        print("Testing: Task Management + SLA Management + Partner Configuration + Handoff to Delivery")
        print("=" * 80)
        
        # Authentication is required for all tests
        if not self.authenticate_admin():
            print("❌ Admin authentication failed. Cannot proceed with tests.")
            return False
        
        # Test basic health
        self.test_health_check()
        
        print("\n🏗️ PIPELINE SETUP TESTS")
        print("-" * 50)
        self.test_setup_elev8_pipelines()
        self.test_get_elev8_pipelines()
        
        print("\n🤝 PARTNER MANAGEMENT TESTS")
        print("-" * 50)
        self.test_list_partners()
        self.test_create_partner()
        self.test_get_partner_with_products()
        
        print("\n📦 PRODUCT MANAGEMENT TESTS")
        print("-" * 50)
        self.test_list_products()
        self.test_list_products_by_partner()
        self.test_create_product()
        
        print("\n🎯 LEAD MANAGEMENT WITH SCORING TESTS")
        print("-" * 50)
        self.test_list_leads()
        self.test_create_lead_partnership_sales()
        self.test_create_lead_partner_sales()
        self.test_get_lead_with_score_and_tier()
        self.test_update_lead_recalculate_score()
        self.test_get_lead_scoring_stats()
        
        print("\n🔥 LEAD QUALIFICATION FLOW TESTS (CRITICAL)")
        print("-" * 50)
        self.test_qualify_lead_validation()
        self.test_qualify_lead_success()
        self.test_record_touchpoint()
        
        print("\n🏢 COMPANY MANAGEMENT TESTS")
        print("-" * 50)
        self.test_list_companies()
        self.test_create_company()
        
        print("\n📊 LEAD SCORING VALIDATION TESTS")
        print("-" * 50)
        self.test_lead_scoring_tiers()
        
        print("\n✅ TASK MANAGEMENT TESTS")
        print("-" * 50)
        self.test_create_task()
        self.test_list_tasks()
        self.test_get_task()
        self.test_update_task()
        self.test_complete_task()
        self.test_get_my_tasks()
        
        print("\n⏰ SLA MANAGEMENT TESTS")
        print("-" * 50)
        self.test_get_sla_config()
        self.test_create_sla_config()
        self.test_get_sla_status_deals()
        self.test_get_sla_status_leads()
        
        print("\n🔧 PARTNER CONFIGURATION TESTS")
        print("-" * 50)
        self.test_get_partner_config()
        self.test_update_partner_config()
        self.test_get_partner_kpis()
        self.test_check_partner_compliance()
        self.test_get_fields_by_stage()
        
        print("\n🚚 HANDOFF TO DELIVERY TESTS")
        print("-" * 50)
        self.test_get_handoff_status()
        self.test_initiate_handoff_validation()
        self.test_update_handoff_artifact()
        self.test_list_handoffs()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)
        
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
    tester = Elev8CRMTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()