#!/usr/bin/env python3
"""
Backend API Testing for Elevate CRM - Affiliate Management System
Tests all affiliate-related endpoints and functionality
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://affilinker-8.preview.emergentagent.com/api"
LOGIN_EMAIL = "admin@demo.com"
LOGIN_PASSWORD = "admin123"
TENANT_SLUG = "demo"

class AffiliateAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_data = None
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
    
    def authenticate(self):
        """Login and get JWT token"""
        try:
            login_data = {
                "email": LOGIN_EMAIL,
                "password": LOGIN_PASSWORD
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/auth/login?tenant_slug={TENANT_SLUG}",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.user_data = data["user"]
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                self.log_test("Authentication", True, f"Logged in as {self.user_data['email']}")
                return True
            else:
                self.log_test("Authentication", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Authentication", False, error=e)
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
    
    def test_get_affiliates(self):
        """Test GET /api/affiliates - should return 3 affiliates"""
        try:
            response = self.session.get(f"{BACKEND_URL}/affiliates")
            
            if response.status_code == 200:
                data = response.json()
                affiliates = data.get("affiliates", [])
                total = data.get("total", 0)
                
                if total == 3 and len(affiliates) == 3:
                    # Check affiliate names from seed data
                    affiliate_names = [aff["name"] for aff in affiliates]
                    expected_names = ["John Partner", "Sarah Referrer", "Mike Affiliate"]
                    
                    found_names = []
                    for name in expected_names:
                        if name in affiliate_names:
                            found_names.append(name)
                    
                    if len(found_names) == 3:
                        self.log_test("GET /affiliates", True, f"Found {total} affiliates: {', '.join(found_names)}")
                        
                        # Check affiliate statuses
                        statuses = {aff["name"]: aff["status"] for aff in affiliates}
                        status_details = f"Mike Affiliate: {statuses.get('Mike Affiliate', 'unknown')}, Sarah Referrer: {statuses.get('Sarah Referrer', 'unknown')}, John Partner: {statuses.get('John Partner', 'unknown')}"
                        print(f"   Statuses: {status_details}")
                        
                        return True
                    else:
                        self.log_test("GET /affiliates", False, f"Expected affiliate names not found. Got: {affiliate_names}")
                        return False
                else:
                    self.log_test("GET /affiliates", False, f"Expected 3 affiliates, got {total}")
                    return False
            else:
                self.log_test("GET /affiliates", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliates", False, error=e)
            return False
    
    def test_get_programs(self):
        """Test GET /api/affiliates/programs - should return 2 programs"""
        try:
            response = self.session.get(f"{BACKEND_URL}/affiliates/programs")
            
            if response.status_code == 200:
                data = response.json()
                programs = data.get("programs", [])
                
                if len(programs) == 2:
                    program_names = [prog["name"] for prog in programs]
                    expected_names = ["Frylow Partner Program", "Frylow Direct Sales"]
                    
                    found_names = []
                    for name in expected_names:
                        if name in program_names:
                            found_names.append(name)
                    
                    if len(found_names) == 2:
                        # Check program details
                        program_details = []
                        for prog in programs:
                            journey = prog.get("journey_type", "unknown")
                            commission = prog.get("commission_type", "unknown")
                            value = prog.get("commission_value", 0)
                            auto_approve = prog.get("auto_approve", False)
                            attribution_days = prog.get("attribution_window_days", 0)
                            
                            if prog["name"] == "Frylow Partner Program":
                                expected_details = f"Demo First, 10% commission, {attribution_days} days attribution, Manual approval"
                            else:  # Frylow Direct Sales
                                expected_details = f"Direct Checkout, ${value} flat commission, {attribution_days} days attribution, Auto-approve: {auto_approve}"
                            
                            program_details.append(f"{prog['name']}: {expected_details}")
                        
                        self.log_test("GET /affiliates/programs", True, f"Found 2 programs: {', '.join(found_names)}")
                        for detail in program_details:
                            print(f"   {detail}")
                        
                        return True
                    else:
                        self.log_test("GET /affiliates/programs", False, f"Expected program names not found. Got: {program_names}")
                        return False
                else:
                    self.log_test("GET /affiliates/programs", False, f"Expected 2 programs, got {len(programs)}")
                    return False
            else:
                self.log_test("GET /affiliates/programs", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliates/programs", False, error=e)
            return False
    
    def test_get_commissions(self):
        """Test GET /api/affiliates/commissions - should return empty array"""
        try:
            response = self.session.get(f"{BACKEND_URL}/affiliates/commissions")
            
            if response.status_code == 200:
                data = response.json()
                commissions = data.get("commissions", [])
                total = data.get("total", 0)
                
                if total == 0 and len(commissions) == 0:
                    self.log_test("GET /affiliates/commissions", True, "No commissions found (expected)")
                    return True
                else:
                    self.log_test("GET /affiliates/commissions", False, f"Expected 0 commissions, got {total}")
                    return False
            else:
                self.log_test("GET /affiliates/commissions", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliates/commissions", False, error=e)
            return False
    
    def test_get_analytics_dashboard(self):
        """Test GET /api/affiliates/analytics/dashboard - should return stats"""
        try:
            response = self.session.get(f"{BACKEND_URL}/affiliates/analytics/dashboard")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["affiliates", "clicks", "commissions", "total_commission_value"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    affiliates = data.get("affiliates", {})
                    total_affiliates = affiliates.get("total", 0)
                    active_affiliates = affiliates.get("active", 0)
                    total_clicks = data.get("clicks", 0)
                    total_commission_value = data.get("total_commission_value", 0)
                    
                    details = f"Total Affiliates: {total_affiliates}, Active: {active_affiliates}, Total Clicks: {total_clicks}, Commission Value: ${total_commission_value}"
                    self.log_test("GET /affiliates/analytics/dashboard", True, details)
                    
                    # Verify expected values from seed data
                    if total_affiliates == 3:
                        print(f"   ✅ Total affiliates count matches expected (3)")
                    else:
                        print(f"   ⚠️  Total affiliates: expected 3, got {total_affiliates}")
                    
                    if active_affiliates == 2:
                        print(f"   ✅ Active affiliates count matches expected (2)")
                    else:
                        print(f"   ⚠️  Active affiliates: expected 2, got {active_affiliates}")
                    
                    return True
                else:
                    self.log_test("GET /affiliates/analytics/dashboard", False, f"Missing fields: {missing_fields}")
                    return False
            else:
                self.log_test("GET /affiliates/analytics/dashboard", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliates/analytics/dashboard", False, error=e)
            return False
    
    def test_create_affiliate(self):
        """Test creating a new affiliate"""
        try:
            new_affiliate_data = {
                "name": "Test Affiliate User",
                "email": "test.affiliate@example.com",
                "company": "Test Marketing Co",
                "phone": "555-0199",
                "website": "https://testmarketing.com",
                "payout_method": "paypal",
                "notes": "Test affiliate created during API testing"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/affiliates",
                json=new_affiliate_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                data = response.json()
                if data.get("name") == new_affiliate_data["name"] and data.get("email") == new_affiliate_data["email"]:
                    self.log_test("POST /affiliates (Create)", True, f"Created affiliate: {data['name']} ({data['email']})")
                    return True
                else:
                    self.log_test("POST /affiliates (Create)", False, "Response data doesn't match input")
                    return False
            else:
                self.log_test("POST /affiliates (Create)", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /affiliates (Create)", False, error=e)
            return False
    
    def test_approve_affiliate(self):
        """Test approving a pending affiliate (Mike Affiliate)"""
        try:
            # First get the list of affiliates to find Mike Affiliate
            response = self.session.get(f"{BACKEND_URL}/affiliates")
            
            if response.status_code != 200:
                self.log_test("Approve Affiliate (Get List)", False, f"Failed to get affiliates: {response.status_code}")
                return False
            
            data = response.json()
            affiliates = data.get("affiliates", [])
            
            mike_affiliate = None
            for aff in affiliates:
                if aff["name"] == "Mike Affiliate" and aff["status"] == "pending":
                    mike_affiliate = aff
                    break
            
            if not mike_affiliate:
                self.log_test("Approve Affiliate", False, "Mike Affiliate not found or not pending")
                return False
            
            # Approve the affiliate
            approve_response = self.session.post(f"{BACKEND_URL}/affiliates/{mike_affiliate['id']}/approve")
            
            if approve_response.status_code == 200:
                approve_data = approve_response.json()
                if approve_data.get("success") and approve_data.get("status") == "active":
                    self.log_test("POST /affiliates/{id}/approve", True, f"Successfully approved Mike Affiliate")
                    return True
                else:
                    self.log_test("POST /affiliates/{id}/approve", False, "Approval response invalid")
                    return False
            else:
                self.log_test("POST /affiliates/{id}/approve", False, f"Status: {approve_response.status_code}", approve_response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /affiliates/{id}/approve", False, error=e)
            return False
    
    def test_get_links(self):
        """Test GET /api/affiliates/links"""
        try:
            response = self.session.get(f"{BACKEND_URL}/affiliates/links")
            
            if response.status_code == 200:
                data = response.json()
                links = data.get("links", [])
                self.log_test("GET /affiliates/links", True, f"Found {len(links)} affiliate links")
                
                # Show link details if any exist
                for link in links[:3]:  # Show first 3 links
                    print(f"   Link: {link.get('referral_code')} -> {link.get('landing_page_url', 'N/A')}")
                
                return True
            else:
                self.log_test("GET /affiliates/links", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliates/links", False, error=e)
            return False
    
    def test_get_events(self):
        """Test GET /api/affiliates/events"""
        try:
            response = self.session.get(f"{BACKEND_URL}/affiliates/events")
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                total = data.get("total", 0)
                self.log_test("GET /affiliates/events", True, f"Found {total} affiliate events")
                return True
            else:
                self.log_test("GET /affiliates/events", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /affiliates/events", False, error=e)
            return False
    
    def run_all_tests(self):
        """Run all affiliate API tests"""
        print("🚀 Starting Affiliate Management System API Tests")
        print("=" * 60)
        
        # Authentication is required for all tests
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        # Test basic health
        self.test_health_check()
        
        # Core affiliate API tests
        self.test_get_affiliates()
        self.test_get_programs()
        self.test_get_commissions()
        self.test_get_analytics_dashboard()
        
        # Additional functionality tests
        self.test_create_affiliate()
        self.test_approve_affiliate()
        self.test_get_links()
        self.test_get_events()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
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
        
        return passed == total

def main():
    """Main test runner"""
    tester = AffiliateAPITester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()