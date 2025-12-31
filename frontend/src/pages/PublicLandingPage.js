import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { 
  Star, Check, ChevronRight, Quote, HelpCircle, 
  ChevronDown, ChevronUp, Loader2, Sparkles
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PublicLandingPage = () => {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(null);
  const [expandedFaq, setExpandedFaq] = useState(null);
  const [formData, setFormData] = useState({ name: '', email: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const affiliateRef = searchParams.get('ref');

  useEffect(() => {
    const fetchPage = async () => {
      setLoading(true);
      try {
        const url = affiliateRef 
          ? `${BACKEND_URL}/api/landing-pages/public/${slug}?ref=${affiliateRef}`
          : `${BACKEND_URL}/api/landing-pages/public/${slug}`;
        const response = await axios.get(url);
        setPage(response.data.page);
      } catch (err) {
        setError(err.response?.status === 404 ? 'Page not found' : 'Failed to load page');
      } finally {
        setLoading(false);
      }
    };
    fetchPage();
  }, [slug, affiliateRef]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    // In production, would submit to a form handler
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSubmitted(true);
    setSubmitting(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white">
        <div className="max-w-6xl mx-auto p-8 space-y-8">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Page Not Found</h1>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  const schema = page?.page_schema;
  const colors = schema?.color_scheme || {
    primary: '#FF6B35',
    secondary: '#1A1A2E',
    accent: '#4ECDC4',
    background: '#FFFFFF',
    text: '#1A1A2E'
  };

  const renderSection = (section) => {
    switch (section.type) {
      case 'hero':
        return (
          <section 
            key={section.order} 
            className="py-20 px-6"
            style={{ background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 100%)` }}
          >
            <div className="max-w-4xl mx-auto text-center text-white">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
                {section.headline}
              </h1>
              {section.subheadline && (
                <p className="text-xl md:text-2xl mb-8 opacity-90">
                  {section.subheadline}
                </p>
              )}
              {section.body_text && (
                <p className="text-lg mb-8 opacity-80 max-w-2xl mx-auto">
                  {section.body_text}
                </p>
              )}
              {section.cta_text && (
                <Button 
                  size="lg" 
                  className="bg-white text-gray-900 hover:bg-gray-100 text-lg px-8 py-6 h-auto"
                  onClick={() => document.getElementById('signup-form')?.scrollIntoView({ behavior: 'smooth' })}
                >
                  {section.cta_text}
                  <ChevronRight className="w-5 h-5 ml-2" />
                </Button>
              )}
            </div>
          </section>
        );

      case 'features':
        return (
          <section key={section.order} className="py-16 px-6 bg-gray-50">
            <div className="max-w-6xl mx-auto">
              {section.headline && (
                <h2 className="text-3xl font-bold text-center mb-12" style={{ color: colors.text }}>
                  {section.headline}
                </h2>
              )}
              <div className="grid md:grid-cols-3 gap-8">
                {section.items?.map((item, idx) => (
                  <div key={idx} className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
                    <div 
                      className="w-12 h-12 rounded-lg flex items-center justify-center mb-4"
                      style={{ backgroundColor: `${colors.primary}20` }}
                    >
                      <Sparkles className="w-6 h-6" style={{ color: colors.primary }} />
                    </div>
                    <h3 className="text-xl font-semibold mb-2" style={{ color: colors.text }}>
                      {item.title}
                    </h3>
                    <p className="text-gray-600">{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        );

      case 'benefits':
        return (
          <section key={section.order} className="py-16 px-6">
            <div className="max-w-6xl mx-auto">
              {section.headline && (
                <h2 className="text-3xl font-bold text-center mb-12" style={{ color: colors.text }}>
                  {section.headline}
                </h2>
              )}
              <div className="grid md:grid-cols-2 gap-6">
                {section.items?.map((item, idx) => (
                  <div key={idx} className="flex items-start gap-4 p-4">
                    <div 
                      className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: colors.accent }}
                    >
                      <Check className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold mb-1" style={{ color: colors.text }}>
                        {item.title}
                      </h3>
                      <p className="text-gray-600">{item.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        );

      case 'social_proof':
        return (
          <section key={section.order} className="py-16 px-6 bg-gray-50">
            <div className="max-w-6xl mx-auto">
              {section.headline && (
                <h2 className="text-3xl font-bold text-center mb-12" style={{ color: colors.text }}>
                  {section.headline}
                </h2>
              )}
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {section.items?.map((item, idx) => (
                  <div key={idx} className="bg-white p-6 rounded-xl shadow-sm">
                    <Quote className="w-8 h-8 mb-4" style={{ color: colors.primary }} />
                    <p className="text-gray-700 mb-4 italic">"{item.quote}"</p>
                    <div className="flex items-center gap-3">
                      <div 
                        className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                        style={{ backgroundColor: colors.primary }}
                      >
                        {item.name?.charAt(0)}
                      </div>
                      <div>
                        <p className="font-semibold" style={{ color: colors.text }}>{item.name}</p>
                        {item.title && <p className="text-sm text-gray-500">{item.title}</p>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        );

      case 'faq':
        return (
          <section key={section.order} className="py-16 px-6">
            <div className="max-w-3xl mx-auto">
              {section.headline && (
                <h2 className="text-3xl font-bold text-center mb-12" style={{ color: colors.text }}>
                  {section.headline}
                </h2>
              )}
              <div className="space-y-4">
                {section.items?.map((item, idx) => (
                  <div 
                    key={idx} 
                    className="border rounded-lg overflow-hidden"
                    style={{ borderColor: expandedFaq === idx ? colors.primary : '#e5e7eb' }}
                  >
                    <button
                      className="w-full px-6 py-4 text-left flex items-center justify-between hover:bg-gray-50"
                      onClick={() => setExpandedFaq(expandedFaq === idx ? null : idx)}
                    >
                      <span className="font-semibold" style={{ color: colors.text }}>
                        {item.question}
                      </span>
                      {expandedFaq === idx ? (
                        <ChevronUp className="w-5 h-5 text-gray-500" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-500" />
                      )}
                    </button>
                    {expandedFaq === idx && (
                      <div className="px-6 pb-4 text-gray-600">
                        {item.answer}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </section>
        );

      case 'cta':
        return (
          <section 
            key={section.order} 
            id="signup-form"
            className="py-20 px-6"
            style={{ background: `linear-gradient(135deg, ${colors.secondary} 0%, ${colors.primary} 100%)` }}
          >
            <div className="max-w-2xl mx-auto text-center text-white">
              {section.headline && (
                <h2 className="text-3xl md:text-4xl font-bold mb-4">
                  {section.headline}
                </h2>
              )}
              {section.subheadline && (
                <p className="text-xl mb-8 opacity-90">
                  {section.subheadline}
                </p>
              )}
              
              {submitted ? (
                <div className="bg-white/10 backdrop-blur rounded-xl p-8">
                  <Check className="w-16 h-16 mx-auto mb-4 text-green-400" />
                  <h3 className="text-2xl font-bold mb-2">Thank You!</h3>
                  <p className="opacity-90">We'll be in touch soon.</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="bg-white/10 backdrop-blur rounded-xl p-8 space-y-4">
                  <Input
                    type="text"
                    placeholder="Your Name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="bg-white text-gray-900"
                  />
                  <Input
                    type="email"
                    placeholder="Your Email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    className="bg-white text-gray-900"
                  />
                  <Button 
                    type="submit" 
                    size="lg" 
                    className="w-full text-lg"
                    style={{ backgroundColor: colors.accent }}
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      section.cta_text || 'Get Started'
                    )}
                  </Button>
                </form>
              )}
            </div>
          </section>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: colors.background }}>
      {/* Meta */}
      <title>{schema?.page_title || 'Landing Page'}</title>
      
      {/* Sections */}
      {schema?.sections
        ?.sort((a, b) => a.order - b.order)
        .map(section => renderSection(section))}
      
      {/* Footer */}
      <footer className="py-8 px-6 border-t bg-gray-50">
        <div className="max-w-6xl mx-auto text-center text-gray-500 text-sm">
          <p>Powered by Elevate CRM</p>
          {affiliateRef && (
            <Badge variant="outline" className="mt-2">
              Referred by affiliate
            </Badge>
          )}
        </div>
      </footer>
    </div>
  );
};

export default PublicLandingPage;
