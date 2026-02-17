import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { cn } from '../../lib/utils';
import {
  Star, Check, ChevronRight, Quote, HelpCircle,
  ChevronDown, ChevronUp, Loader2, Sparkles,
  ArrowUp, ArrowDown, Trash2, MessageSquare
} from 'lucide-react';

// ==================== SECTION SUB-COMPONENTS ====================

const HeroSection = ({ section, colors, onCtaClick }) => (
  <section
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
          onClick={onCtaClick}
        >
          {section.cta_text}
          <ChevronRight className="w-5 h-5 ml-2" />
        </Button>
      )}
    </div>
  </section>
);

const FeaturesSection = ({ section, colors }) => (
  <section className="py-16 px-6 bg-gray-50">
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

const BenefitsSection = ({ section, colors }) => (
  <section className="py-16 px-6">
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

const SocialProofSection = ({ section, colors }) => (
  <section className="py-16 px-6 bg-gray-50">
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

const FaqSection = ({ section, colors }) => {
  const [expandedFaq, setExpandedFaq] = useState(null);

  return (
    <section className="py-16 px-6">
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
};

const CtaSection = ({ section, colors, formData, setFormData, submitting, submitted, submissionError, onSubmit, onCtaClick }) => (
  <section
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

      {onSubmit ? (
        // Full form mode (public page)
        submitted ? (
          <div className="bg-white/10 backdrop-blur rounded-xl p-8">
            <Check className="w-16 h-16 mx-auto mb-4 text-green-400" />
            <h3 className="text-2xl font-bold mb-2">Thank You!</h3>
            <p className="opacity-90">We'll be in touch soon.</p>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="bg-white/10 backdrop-blur rounded-xl p-8 space-y-4">
            <Input
              type="text"
              placeholder="Your Name"
              value={formData?.name || ''}
              onChange={(e) => setFormData?.({ ...formData, name: e.target.value })}
              required
              className="bg-white text-gray-900"
            />
            <Input
              type="email"
              placeholder="Your Email"
              value={formData?.email || ''}
              onChange={(e) => setFormData?.({ ...formData, email: e.target.value })}
              required
              className="bg-white text-gray-900"
            />
            <Input
              type="tel"
              placeholder="Phone (optional)"
              value={formData?.phone || ''}
              onChange={(e) => setFormData?.({ ...formData, phone: e.target.value })}
              className="bg-white text-gray-900"
            />
            <Input
              type="text"
              placeholder="Company (optional)"
              value={formData?.company || ''}
              onChange={(e) => setFormData?.({ ...formData, company: e.target.value })}
              className="bg-white text-gray-900"
            />
            {submissionError && (
              <p className="text-sm text-red-200 text-left">{submissionError}</p>
            )}
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
        )
      ) : (
        // Preview mode (builder) - just show the CTA button
        <div className="bg-white/10 backdrop-blur rounded-xl p-8 space-y-4">
          <div className="h-10 bg-white/20 rounded mb-3" />
          <div className="h-10 bg-white/20 rounded mb-3" />
          <div className="h-10 bg-white/20 rounded mb-3" />
          <div className="h-10 bg-white/20 rounded mb-3" />
          <Button
            size="lg"
            className="w-full text-lg"
            style={{ backgroundColor: colors.accent }}
            onClick={onCtaClick}
          >
            {section.cta_text || 'Get Started'}
          </Button>
        </div>
      )}
    </div>
  </section>
);

// ==================== INTERACTIVE WRAPPER ====================

const InteractiveWrapper = ({ children, isSelected, onClick, sectionType, sectionIndex, onMoveUp, onMoveDown, onDelete, onEditInChat, isFirst, isLast }) => (
  <div
    className={cn(
      "relative group transition-all cursor-pointer",
      "hover:ring-2 hover:ring-blue-300 hover:ring-offset-2",
      isSelected && "ring-2 ring-blue-500 ring-offset-2"
    )}
    onClick={(e) => {
      e.stopPropagation();
      onClick?.();
    }}
  >
    {children}
    {isSelected && (
      <div className="absolute top-2 right-2 z-10 flex items-center gap-1 bg-white rounded-lg shadow-lg border p-1">
        <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={(e) => { e.stopPropagation(); onEditInChat?.(); }}>
          <MessageSquare className="w-3.5 h-3.5" />
        </Button>
        {!isFirst && (
          <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={(e) => { e.stopPropagation(); onMoveUp?.(); }}>
            <ArrowUp className="w-3.5 h-3.5" />
          </Button>
        )}
        {!isLast && (
          <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={(e) => { e.stopPropagation(); onMoveDown?.(); }}>
            <ArrowDown className="w-3.5 h-3.5" />
          </Button>
        )}
        <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-700" onClick={(e) => { e.stopPropagation(); onDelete?.(); }}>
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      </div>
    )}
    {!isSelected && (
      <div className="absolute top-2 left-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded capitalize">
          {sectionType}
        </span>
      </div>
    )}
  </div>
);

// ==================== MAIN COMPONENT ====================

const SectionRenderer = ({
  section,
  colorScheme,
  isInteractive = false,
  isSelected = false,
  onClick,
  onCtaClick,
  onMoveUp,
  onMoveDown,
  onDelete,
  onEditInChat,
  isFirst = false,
  isLast = false,
  // Public page form props
  formData,
  setFormData,
  submitting,
  submitted,
  submissionError,
  onSubmit,
}) => {
  const colors = colorScheme || {
    primary: '#FF6B35',
    secondary: '#1A1A2E',
    accent: '#4ECDC4',
    background: '#FFFFFF',
    text: '#1A1A2E'
  };

  const renderSection = () => {
    switch (section.type) {
      case 'hero':
        return <HeroSection section={section} colors={colors} onCtaClick={onCtaClick} />;
      case 'features':
        return <FeaturesSection section={section} colors={colors} />;
      case 'benefits':
        return <BenefitsSection section={section} colors={colors} />;
      case 'social_proof':
        return <SocialProofSection section={section} colors={colors} />;
      case 'faq':
        return <FaqSection section={section} colors={colors} />;
      case 'cta':
        return (
          <CtaSection
            section={section}
            colors={colors}
            formData={formData}
            setFormData={setFormData}
            submitting={submitting}
            submitted={submitted}
            submissionError={submissionError}
            onSubmit={onSubmit}
            onCtaClick={onCtaClick}
          />
        );
      default:
        return null;
    }
  };

  if (isInteractive) {
    return (
      <InteractiveWrapper
        isSelected={isSelected}
        onClick={onClick}
        sectionType={section.type}
        sectionIndex={section.order}
        onMoveUp={onMoveUp}
        onMoveDown={onMoveDown}
        onDelete={onDelete}
        onEditInChat={onEditInChat}
        isFirst={isFirst}
        isLast={isLast}
      >
        {renderSection()}
      </InteractiveWrapper>
    );
  }

  return renderSection();
};

export default SectionRenderer;
