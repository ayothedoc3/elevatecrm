#!/usr/bin/env python3
"""
Backend API Testing for Elevate CRM - Phase 1 Affiliate System
Tests Marketing Materials, Affiliate Portal, and Attribution Engine
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://affilinker-8.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin123"
AFFILIATE_EMAIL = "sarah@affiliate.com"
AFFILIATE_PASSWORD = "affiliate123"
TENANT_SLUG = "demo"

class Phase1AffiliateSystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.affiliate_token = None
        self.admin_user_data = None
        self.affiliate_user_data = None
        self.test_results = []
        
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
    
    def authenticate_affiliate(self):
        """Login as affiliate via portal"""
        try:
            login_data = {
                "email": AFFILIATE_EMAIL,
                "password": AFFILIATE_PASSWORD,
                "tenant_slug": TENANT_SLUG
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/affiliate-portal/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.affiliate_token = data["access_token"]
                self.affiliate_user_data = data["affiliate"]
                self.log_test("Affiliate Portal Authentication", True, f"Logged in as {self.affiliate_user_data['email']}")
                return True
            else:
                self.log_test("Affiliate Portal Authentication", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Affiliate Portal Authentication", False, error=e)
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
    
    # ==================== MARKETING MATERIALS API TESTS ====================
    
    def test_materials_create_url(self):
        """Test POST /api/materials/url - Create URL-based material"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            material_data = {
                "name": "Test Marketing Banner",
                "description": "Test banner for affiliate marketing",
                "category": "banners",
                "material_type": "url",
                "url": "https://example.com/banner.jpg",
                "tags": ["test", "banner"]
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/materials/url",
                json=material_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                if data.get("name") == material_data["name"] and data.get("url") == material_data["url"]:
                    self.log_test("POST /materials/url", True, f"Created material: {data['name']}")
                    return True
                else:
                    self.log_test("POST /materials/url", False, "Response data doesn't match input")
                    return False
            else:
                self.log_test("POST /materials/url", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /materials/url", False, error=e)
            return False
    
    def test_materials_list(self):
        """Test GET /api/materials - List all materials"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/materials", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                materials = data.get("materials", [])
                total = data.get("total", 0)
                self.log_test("GET /materials", True, f"Found {total} materials")
                return True
            else:
                self.log_test("GET /materials", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /materials", False, error=e)
            return False
    
    def test_materials_categories(self):
        """Test GET /api/materials/categories - Get category counts"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/materials/categories", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                categories = data.get("categories", [])
                self.log_test("GET /materials/categories", True, f"Found {len(categories)} categories")
                return True
            else:
                self.log_test("GET /materials/categories", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /materials/categories", False, error=e)
            return False
    
    # ==================== AFFILIATE PORTAL API TESTS ====================
    
    def test_affiliate_portal_register(self):
        """Test POST /api/affiliate-portal/register - Register new affiliate"""
        try:
            register_data = {
                "name": "Test New Affiliate",
                "email": "testnew@affiliate.com",
                "password": "testpass123",
                "company": "Test Marketing Co",
                "tenant_slug": TENANT_SLUG
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/affiliate-portal/register",
                json=register_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                data = response.json()
                if data.get("success") and "pending approval" in data.get("message", "").lower():
                    self.log_test("POST /affiliate-portal/register", True, "Registration successful, pending approval")
                    return True
                else:
                    self.log_test("POST /affiliate-portal/register", False, "Unexpected response format")
                    return False
            else:
                self.log_test("POST /affiliate-portal/register", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /affiliate-portal/register", False, error=e)
            return False
    
    def test_affiliate_portal_me(self):
        """Test GET /api/affiliate-portal/me - Get affiliate profile"""
        try:
            headers = {"Authorization": f"Bearer {self.affiliate_token}"}
            response = self.session.get(f"{BACKEND_URL}/affiliate-portal/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("email") == AFFILIATE_EMAIL:
                    self.log_test("GET /affiliate-portal/me", True, f"Profile: {data['name']} ({data['email']})")
                    return True
                else:
                    self.log_test("GET /affiliate-portal/me", False, "Profile data mismatch")
                    return False
            else:
                self.log_test("GET /affiliate-portal/me", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliate-portal/me", False, error=e)
            return False
    
    def test_affiliate_portal_dashboard(self):
        """Test GET /api/affiliate-portal/dashboard - Get affiliate dashboard stats"""
        try:
            headers = {"Authorization": f"Bearer {self.affiliate_token}"}
            response = self.session.get(f"{BACKEND_URL}/affiliate-portal/dashboard", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get("stats", {})
                affiliate = data.get("affiliate", {})
                
                total_earnings = affiliate.get("total_earnings", 0)
                total_clicks = stats.get("total_clicks", 0)
                total_conversions = stats.get("total_conversions", 0)
                conversion_rate = stats.get("conversion_rate", 0)
                
                details = f"Earnings: ${total_earnings}, Clicks: {total_clicks}, Conversions: {total_conversions}, Rate: {conversion_rate}%"
                self.log_test("GET /affiliate-portal/dashboard", True, details)
                return True
            else:
                self.log_test("GET /affiliate-portal/dashboard", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliate-portal/dashboard", False, error=e)
            return False
    
    def test_affiliate_portal_links(self):
        """Test GET /api/affiliate-portal/links - Get affiliate's referral links"""
        try:
            headers = {"Authorization": f"Bearer {self.affiliate_token}"}
            response = self.session.get(f"{BACKEND_URL}/affiliate-portal/links", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                links = data.get("links", [])
                self.log_test("GET /affiliate-portal/links", True, f"Found {len(links)} referral links")
                
                # Store first link for attribution testing
                if links:
                    self.test_referral_code = links[0].get("referral_code")
                    print(f"   Sample referral code: {self.test_referral_code}")
                
                return True
            else:
                self.log_test("GET /affiliate-portal/links", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliate-portal/links", False, error=e)
            return False
    
    def test_affiliate_portal_create_link(self):
        """Test POST /api/affiliate-portal/links - Generate new referral link"""
        try:
            # First get available programs
            headers = {"Authorization": f"Bearer {self.affiliate_token}"}
            programs_response = self.session.get(f"{BACKEND_URL}/affiliate-portal/programs", headers=headers)
            
            if programs_response.status_code != 200:
                self.log_test("POST /affiliate-portal/links (Get Programs)", False, "Failed to get programs")
                return False
            
            programs_data = programs_response.json()
            programs = programs_data.get("programs", [])
            
            if not programs:
                self.log_test("POST /affiliate-portal/links", False, "No programs available")
                return False
            
            # Create link for first program
            link_data = {
                "program_id": programs[0]["id"],
                "landing_page_url": "/demo",
                "custom_slug": None
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/affiliate-portal/links",
                json=link_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                if data.get("referral_code") and data.get("program_id") == link_data["program_id"]:
                    self.log_test("POST /affiliate-portal/links", True, f"Created link: {data['referral_code']}")
                    return True
                else:
                    self.log_test("POST /affiliate-portal/links", False, "Invalid response data")
                    return False
            else:
                self.log_test("POST /affiliate-portal/links", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /affiliate-portal/links", False, error=e)
            return False
    
    def test_affiliate_portal_programs(self):
        """Test GET /api/affiliate-portal/programs - Get available programs"""
        try:
            headers = {"Authorization": f"Bearer {self.affiliate_token}"}
            response = self.session.get(f"{BACKEND_URL}/affiliate-portal/programs", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                programs = data.get("programs", [])
                
                if len(programs) >= 2:
                    program_names = [p["name"] for p in programs]
                    self.log_test("GET /affiliate-portal/programs", True, f"Found {len(programs)} programs: {', '.join(program_names[:2])}")
                    return True
                else:
                    self.log_test("GET /affiliate-portal/programs", False, f"Expected at least 2 programs, got {len(programs)}")
                    return False
            else:
                self.log_test("GET /affiliate-portal/programs", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliate-portal/programs", False, error=e)
            return False
    
    def test_affiliate_portal_commissions(self):
        """Test GET /api/affiliate-portal/commissions - Get affiliate commissions"""
        try:
            headers = {"Authorization": f"Bearer {self.affiliate_token}"}
            response = self.session.get(f"{BACKEND_URL}/affiliate-portal/commissions", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                commissions = data.get("commissions", [])
                total = data.get("total", 0)
                self.log_test("GET /affiliate-portal/commissions", True, f"Found {total} commissions")
                return True
            else:
                self.log_test("GET /affiliate-portal/commissions", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliate-portal/commissions", False, error=e)
            return False
    
    def test_affiliate_portal_materials(self):
        """Test GET /api/affiliate-portal/materials - Get marketing materials (affiliate view)"""
        try:
            headers = {"Authorization": f"Bearer {self.affiliate_token}"}
            response = self.session.get(f"{BACKEND_URL}/affiliate-portal/materials", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                materials = data.get("materials", [])
                total = data.get("total", 0)
                self.log_test("GET /affiliate-portal/materials", True, f"Found {total} marketing materials")
                return True
            else:
                self.log_test("GET /affiliate-portal/materials", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliate-portal/materials", False, error=e)
            return False
    
    # ==================== ATTRIBUTION ENGINE TESTS ====================
    
    def test_attribution_engine_redirect(self):
        """Test GET /api/ref/{referral_code} - Test click tracking redirect"""
        try:
            # Get a referral code from affiliate links
            if not hasattr(self, 'test_referral_code'):
                # Get links first
                headers = {"Authorization": f"Bearer {self.affiliate_token}"}
                response = self.session.get(f"{BACKEND_URL}/affiliate-portal/links", headers=headers)
                if response.status_code == 200:
                    links = response.json().get("links", [])
                    if links:
                        self.test_referral_code = links[0].get("referral_code")
                    else:
                        self.log_test("Attribution Engine - Get Referral Code", False, "No referral links found")
                        return False
                else:
                    self.log_test("Attribution Engine - Get Referral Code", False, "Failed to get links")
                    return False
            
            # Test the public redirect endpoint
            response = self.session.get(
                f"{BACKEND_URL}/ref/{self.test_referral_code}",
                allow_redirects=False  # Don't follow redirects
            )
            
            if response.status_code == 302:
                location = response.headers.get("Location", "")
                if self.test_referral_code in location:
                    self.log_test("GET /ref/{referral_code}", True, f"Redirect to: {location}")
                    return True
                else:
                    self.log_test("GET /ref/{referral_code}", False, f"Invalid redirect: {location}")
                    return False
            else:
                self.log_test("GET /ref/{referral_code}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /ref/{referral_code}", False, error=e)
            return False
    
    def test_attribution_click_count_increment(self):
        """Verify click count increments after visiting referral link"""
        try:
            if not hasattr(self, 'test_referral_code'):
                self.log_test("Attribution Click Count", False, "No referral code available")
                return False
            
            # Get initial click count
            headers = {"Authorization": f"Bearer {self.affiliate_token}"}
            response = self.session.get(f"{BACKEND_URL}/affiliate-portal/links", headers=headers)
            
            if response.status_code != 200:
                self.log_test("Attribution Click Count - Get Initial", False, "Failed to get links")
                return False
            
            links = response.json().get("links", [])
            initial_link = next((l for l in links if l.get("referral_code") == self.test_referral_code), None)
            
            if not initial_link:
                self.log_test("Attribution Click Count", False, "Referral link not found")
                return False
            
            initial_count = initial_link.get("click_count", 0)
            
            # Click the link
            click_response = self.session.get(
                f"{BACKEND_URL}/ref/{self.test_referral_code}",
                allow_redirects=False
            )
            
            if click_response.status_code != 302:
                self.log_test("Attribution Click Count - Click Link", False, "Link click failed")
                return False
            
            # Get updated click count
            response = self.session.get(f"{BACKEND_URL}/affiliate-portal/links", headers=headers)
            
            if response.status_code == 200:
                links = response.json().get("links", [])
                updated_link = next((l for l in links if l.get("referral_code") == self.test_referral_code), None)
                
                if updated_link:
                    updated_count = updated_link.get("click_count", 0)
                    if updated_count > initial_count:
                        self.log_test("Attribution Click Count Increment", True, f"Count increased from {initial_count} to {updated_count}")
                        return True
                    else:
                        self.log_test("Attribution Click Count Increment", False, f"Count did not increase: {initial_count} -> {updated_count}")
                        return False
                else:
                    self.log_test("Attribution Click Count Increment", False, "Updated link not found")
                    return False
            else:
                self.log_test("Attribution Click Count Increment", False, "Failed to get updated links")
                return False
                
        except Exception as e:
            self.log_test("Attribution Click Count Increment", False, error=e)
            return False
    
    def test_affiliate_events_collection(self):
        """Check affiliate_events collection for new click event"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/affiliates/events", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                total = data.get("total", 0)
                
                # Look for recent click events
                click_events = [e for e in events if e.get("event_type") == "affiliate_link_clicked"]
                
                self.log_test("Affiliate Events Collection", True, f"Found {total} total events, {len(click_events)} click events")
                return True
            else:
                self.log_test("Affiliate Events Collection", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Affiliate Events Collection", False, error=e)
            return False
    
    def run_all_tests(self):
        """Run all Phase 1 Affiliate System tests"""
        print("🚀 Starting Phase 1 Affiliate System API Tests")
        print("=" * 70)
        print("Testing: Marketing Materials + Affiliate Portal + Attribution Engine")
        print("=" * 70)
        
        # Authentication is required for all tests
        if not self.authenticate_admin():
            print("❌ Admin authentication failed. Cannot proceed with admin tests.")
            return False
        
        if not self.authenticate_affiliate():
            print("❌ Affiliate authentication failed. Cannot proceed with affiliate tests.")
            return False
        
        # Test basic health
        self.test_health_check()
        
        print("\n📋 MARKETING MATERIALS API TESTS")
        print("-" * 50)
        self.test_materials_create_url()
        self.test_materials_list()
        self.test_materials_categories()
        
        print("\n🏢 AFFILIATE PORTAL API TESTS")
        print("-" * 50)
        self.test_affiliate_portal_register()
        self.test_affiliate_portal_me()
        self.test_affiliate_portal_dashboard()
        self.test_affiliate_portal_links()
        self.test_affiliate_portal_create_link()
        self.test_affiliate_portal_programs()
        self.test_affiliate_portal_commissions()
        self.test_affiliate_portal_materials()
        
        print("\n🔗 ATTRIBUTION ENGINE TESTS")
        print("-" * 50)
        self.test_attribution_engine_redirect()
        self.test_attribution_click_count_increment()
        self.test_affiliate_events_collection()
        
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
    tester = Phase1AffiliateSystemTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()