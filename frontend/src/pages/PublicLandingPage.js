import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import SectionRenderer from '../components/landing-pages/SectionRenderer';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PublicLandingPage = () => {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(null);
  const [tenantSlug, setTenantSlug] = useState(null);
  const [formData, setFormData] = useState({ name: '', email: '', phone: '', company: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submissionError, setSubmissionError] = useState(null);

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
        setTenantSlug(response.data.tenant_slug || null);
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
    setSubmissionError(null);
    setSubmitting(true);
    try {
      const payload = {
        name: formData.name,
        email: formData.email || undefined,
        phone: formData.phone || undefined,
        company: formData.company || undefined,
        affiliate_ref: affiliateRef || undefined,
      };

      if (tenantSlug) {
        await axios.post(`${BACKEND_URL}/api/public/forms/${tenantSlug}/${slug}`, payload);
      } else {
        await axios.post(`${BACKEND_URL}/api/landing-pages/public/${slug}/submit`, payload);
      }

      setSubmitted(true);
    } catch (err) {
      setSubmissionError(err?.response?.data?.detail || 'Failed to submit form');
    } finally {
      setSubmitting(false);
    }
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

  return (
    <div className="min-h-screen" style={{ backgroundColor: colors.background }}>
      <title>{schema?.page_title || 'Landing Page'}</title>

      {schema?.sections
        ?.sort((a, b) => a.order - b.order)
        .map(section => (
          <SectionRenderer
            key={section.order}
            section={section}
            colorScheme={colors}
            isInteractive={false}
            onCtaClick={() => document.getElementById('signup-form')?.scrollIntoView({ behavior: 'smooth' })}
            formData={formData}
            setFormData={setFormData}
            submitting={submitting}
            submitted={submitted}
            submissionError={submissionError}
            onSubmit={handleSubmit}
          />
        ))}

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
