#!/usr/bin/env python3
"""
Backend API Testing for AI Landing Page Builder
Tests Landing Pages CRUD, AI Generation, Publishing, Version Management, and Public Access
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
TENANT_SLUG = "demo"

class AILandingPageBuilderTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.admin_user_data = None
        self.test_results = []
        self.created_page_id = None
        self.created_page_slug = None
        
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
    
    # ==================== LANDING PAGES CRUD API TESTS ====================
    
    def test_landing_pages_list(self):
        """Test GET /api/landing-pages - List all landing pages"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/landing-pages", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get("pages", [])
                total = data.get("total", 0)
                self.log_test("GET /landing-pages", True, f"Found {total} landing pages")
                return True
            else:
                self.log_test("GET /landing-pages", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /landing-pages", False, error=e)
            return False
    
    def test_landing_page_create_manual(self):
        """Test POST /api/landing-pages - Create a landing page manually"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Mock page schema for manual creation
            mock_schema = {
                "page_title": "Test Landing Page",
                "meta_description": "A test landing page for API testing",
                "sections": [
                    {
                        "type": "hero",
                        "order": 1,
                        "headline": "Welcome to Our Test Page",
                        "subheadline": "This is a test landing page created via API",
                        "body_text": "Testing the landing page creation functionality",
                        "cta_text": "Get Started",
                        "cta_url": "#signup",
                        "image_placeholder": "Hero image placeholder"
                    },
                    {
                        "type": "features",
                        "order": 2,
                        "headline": "Amazing Features",
                        "items": [
                            {"title": "Feature 1", "description": "First amazing feature", "icon": "star"},
                            {"title": "Feature 2", "description": "Second amazing feature", "icon": "check"}
                        ]
                    }
                ],
                "color_scheme": {
                    "primary": "#3B82F6",
                    "secondary": "#1E40AF",
                    "accent": "#F59E0B",
                    "background": "#FFFFFF",
                    "text": "#1F2937"
                }
            }
            
            page_data = {
                "name": "Test Landing Page - Manual Creation",
                "page_type": "generic",
                "page_schema": mock_schema
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/landing-pages",
                json=page_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                if data.get("name") == page_data["name"] and data.get("id"):
                    self.created_page_id = data["id"]
                    self.created_page_slug = data.get("slug")
                    self.log_test("POST /landing-pages (Manual)", True, f"Created page: {data['name']} (ID: {data['id']})")
                    return True
                else:
                    self.log_test("POST /landing-pages (Manual)", False, "Response data doesn't match input")
                    return False
            else:
                self.log_test("POST /landing-pages (Manual)", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /landing-pages (Manual)", False, error=e)
            return False
    
    def test_landing_page_get_specific(self):
        """Test GET /api/landing-pages/{id} - Get a specific page"""
        try:
            if not self.created_page_id:
                self.log_test("GET /landing-pages/{id}", False, "No page ID available")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/landing-pages/{self.created_page_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") == self.created_page_id and data.get("page_schema"):
                    self.log_test("GET /landing-pages/{id}", True, f"Retrieved page: {data['name']}")
                    return True
                else:
                    self.log_test("GET /landing-pages/{id}", False, "Invalid page data")
                    return False
            else:
                self.log_test("GET /landing-pages/{id}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /landing-pages/{id}", False, error=e)
            return False
    
    def test_landing_page_update(self):
        """Test PUT /api/landing-pages/{id} - Update a page"""
        try:
            if not self.created_page_id:
                self.log_test("PUT /landing-pages/{id}", False, "No page ID available")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            update_data = {
                "name": "Updated Test Landing Page",
                "seo_title": "Updated SEO Title",
                "seo_description": "Updated SEO description for testing"
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/landing-pages/{self.created_page_id}",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("PUT /landing-pages/{id}", True, "Page updated successfully")
                    return True
                else:
                    self.log_test("PUT /landing-pages/{id}", False, "Update failed")
                    return False
            else:
                self.log_test("PUT /landing-pages/{id}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("PUT /landing-pages/{id}", False, error=e)
            return False
    
    def test_landing_page_delete(self):
        """Test DELETE /api/landing-pages/{id} - Delete a page"""
        try:
            if not self.created_page_id:
                self.log_test("DELETE /landing-pages/{id}", False, "No page ID available")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.delete(f"{BACKEND_URL}/landing-pages/{self.created_page_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("DELETE /landing-pages/{id}", True, "Page deleted successfully")
                    return True
                else:
                    self.log_test("DELETE /landing-pages/{id}", False, "Delete failed")
                    return False
            else:
                self.log_test("DELETE /landing-pages/{id}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("DELETE /landing-pages/{id}", False, error=e)
            return False
    
    # ==================== AI GENERATION API TESTS ====================
    
    def test_ai_generate_landing_page(self):
        """Test POST /api/landing-pages/generate - Generate a landing page using AI"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            generation_data = {
                "page_goal": "Recruit affiliates for Frylow",
                "target_audience": "Restaurant owners and food bloggers",
                "offer_details": "10% commission, 30-day cookie, marketing materials",
                "page_type": "affiliate_recruitment",
                "cta_type": "signup",
                "tone": "professional",
                "brand_name": "Frylow",
                "ai_model": "gpt-4o",
                "product_features": [
                    "Oil savings technology",
                    "Easy installation",
                    "Real-time monitoring"
                ]
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/landing-pages/generate",
                json=generation_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("page_schema"):
                    page_schema = data["page_schema"]
                    sections = page_schema.get("sections", [])
                    self.log_test("POST /landing-pages/generate", True, f"Generated page with {len(sections)} sections using {data.get('ai_model', 'unknown')} model")
                    
                    # Store generated schema for creating a page
                    self.generated_schema = page_schema
                    return True
                else:
                    self.log_test("POST /landing-pages/generate", False, "Invalid generation response")
                    return False
            else:
                self.log_test("POST /landing-pages/generate", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /landing-pages/generate", False, error=e)
            return False
    
    def test_save_generated_page(self):
        """Test creating a page from AI-generated schema"""
        try:
            if not hasattr(self, 'generated_schema'):
                self.log_test("Save Generated Page", False, "No generated schema available")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            page_data = {
                "name": "AI Generated Frylow Affiliate Page",
                "page_type": "affiliate_recruitment",
                "page_schema": self.generated_schema
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/landing-pages",
                json=page_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                if data.get("name") == page_data["name"] and data.get("id"):
                    self.ai_generated_page_id = data["id"]
                    self.ai_generated_page_slug = data.get("slug")
                    self.log_test("Save Generated Page", True, f"Saved AI-generated page: {data['name']} (ID: {data['id']})")
                    return True
                else:
                    self.log_test("Save Generated Page", False, "Response data doesn't match input")
                    return False
            else:
                self.log_test("Save Generated Page", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Save Generated Page", False, error=e)
            return False
    
    # ==================== PUBLISHING API TESTS ====================
    
    def test_publish_page(self):
        """Test POST /api/landing-pages/{id}/publish - Publish a page"""
        try:
            page_id = getattr(self, 'ai_generated_page_id', None) or self.created_page_id
            if not page_id:
                self.log_test("POST /landing-pages/{id}/publish", False, "No page ID available")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(f"{BACKEND_URL}/landing-pages/{page_id}/publish", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("slug"):
                    self.published_slug = data["slug"]
                    self.log_test("POST /landing-pages/{id}/publish", True, f"Published page with slug: {data['slug']}")
                    return True
                else:
                    self.log_test("POST /landing-pages/{id}/publish", False, "Publish failed")
                    return False
            else:
                self.log_test("POST /landing-pages/{id}/publish", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /landing-pages/{id}/publish", False, error=e)
            return False
    
    def test_unpublish_page(self):
        """Test POST /api/landing-pages/{id}/unpublish - Unpublish a page"""
        try:
            page_id = getattr(self, 'ai_generated_page_id', None) or self.created_page_id
            if not page_id:
                self.log_test("POST /landing-pages/{id}/unpublish", False, "No page ID available")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(f"{BACKEND_URL}/landing-pages/{page_id}/unpublish", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("POST /landing-pages/{id}/unpublish", True, "Page unpublished successfully")
                    return True
                else:
                    self.log_test("POST /landing-pages/{id}/unpublish", False, "Unpublish failed")
                    return False
            else:
                self.log_test("POST /landing-pages/{id}/unpublish", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /landing-pages/{id}/unpublish", False, error=e)
            return False
    
    # ==================== VERSION MANAGEMENT TESTS ====================
    
    def test_list_page_versions(self):
        """Test GET /api/landing-pages/{id}/versions - List versions"""
        try:
            page_id = getattr(self, 'ai_generated_page_id', None) or self.created_page_id
            if not page_id:
                self.log_test("GET /landing-pages/{id}/versions", False, "No page ID available")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/landing-pages/{page_id}/versions", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                versions = data.get("versions", [])
                self.log_test("GET /landing-pages/{id}/versions", True, f"Found {len(versions)} versions")
                
                # Store version for rollback test
                if versions:
                    self.test_version_number = versions[0].get("version_number")
                return True
            else:
                self.log_test("GET /landing-pages/{id}/versions", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /landing-pages/{id}/versions", False, error=e)
            return False
    
    def test_rollback_version(self):
        """Test POST /api/landing-pages/{id}/rollback/{version_number} - Rollback"""
        try:
            page_id = getattr(self, 'ai_generated_page_id', None) or self.created_page_id
            version_number = getattr(self, 'test_version_number', 1)
            
            if not page_id:
                self.log_test("POST /landing-pages/{id}/rollback/{version}", False, "No page ID available")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(f"{BACKEND_URL}/landing-pages/{page_id}/rollback/{version_number}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    rolled_back_version = data.get("rolled_back_to_version")
                    self.log_test("POST /landing-pages/{id}/rollback/{version}", True, f"Rolled back to version {rolled_back_version}")
                    return True
                else:
                    self.log_test("POST /landing-pages/{id}/rollback/{version}", False, "Rollback failed")
                    return False
            else:
                self.log_test("POST /landing-pages/{id}/rollback/{version}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /landing-pages/{id}/rollback/{version}", False, error=e)
            return False
    
    # ==================== PUBLIC PAGE ACCESS TESTS ====================
    
    def test_public_page_access(self):
        """Test GET /api/landing-pages/public/{slug} - Access published page (no auth)"""
        try:
            # First, republish the page to ensure it's available
            page_id = getattr(self, 'ai_generated_page_id', None) or self.created_page_id
            if page_id:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                publish_response = self.session.post(f"{BACKEND_URL}/landing-pages/{page_id}/publish", headers=headers)
                if publish_response.status_code == 200:
                    publish_data = publish_response.json()
                    slug = publish_data.get("slug")
                    if slug:
                        self.published_slug = slug
            
            if not hasattr(self, 'published_slug') or not self.published_slug:
                self.log_test("GET /landing-pages/public/{slug}", False, "No published slug available")
                return False
            
            # Test public access (no auth required)
            response = self.session.get(f"{BACKEND_URL}/landing-pages/public/{self.published_slug}")
            
            if response.status_code == 200:
                data = response.json()
                page = data.get("page")
                if page and page.get("slug") == self.published_slug:
                    self.log_test("GET /landing-pages/public/{slug}", True, f"Accessed public page: {page.get('name')}")
                    return True
                else:
                    self.log_test("GET /landing-pages/public/{slug}", False, "Invalid page data")
                    return False
            else:
                self.log_test("GET /landing-pages/public/{slug}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /landing-pages/public/{slug}", False, error=e)
            return False
    
    def test_analytics_increment(self):
        """Test that view_count increases when accessing public page"""
        try:
            if not hasattr(self, 'published_slug') or not self.published_slug:
                self.log_test("Analytics View Count Increment", False, "No published slug available")
                return False
            
            # Get initial view count
            page_id = getattr(self, 'ai_generated_page_id', None) or self.created_page_id
            if not page_id:
                self.log_test("Analytics View Count Increment", False, "No page ID available")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            initial_response = self.session.get(f"{BACKEND_URL}/landing-pages/{page_id}", headers=headers)
            
            if initial_response.status_code != 200:
                self.log_test("Analytics View Count Increment", False, "Failed to get initial view count")
                return False
            
            initial_data = initial_response.json()
            initial_count = initial_data.get("view_count", 0)
            
            # Access public page to increment view count
            public_response = self.session.get(f"{BACKEND_URL}/landing-pages/public/{self.published_slug}")
            
            if public_response.status_code != 200:
                self.log_test("Analytics View Count Increment", False, "Failed to access public page")
                return False
            
            # Get updated view count
            updated_response = self.session.get(f"{BACKEND_URL}/landing-pages/{page_id}", headers=headers)
            
            if updated_response.status_code == 200:
                updated_data = updated_response.json()
                updated_count = updated_data.get("view_count", 0)
                
                if updated_count > initial_count:
                    self.log_test("Analytics View Count Increment", True, f"View count increased from {initial_count} to {updated_count}")
                    return True
                else:
                    self.log_test("Analytics View Count Increment", False, f"View count did not increase: {initial_count} -> {updated_count}")
                    return False
            else:
                self.log_test("Analytics View Count Increment", False, "Failed to get updated view count")
                return False
                
        except Exception as e:
            self.log_test("Analytics View Count Increment", False, error=e)
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