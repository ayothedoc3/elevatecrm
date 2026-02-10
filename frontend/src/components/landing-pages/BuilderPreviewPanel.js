import React from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { Skeleton } from '../ui/skeleton';
import SectionRenderer from './SectionRenderer';
import {
  Monitor, Tablet, Smartphone, Save, Globe, ExternalLink,
  LayoutTemplate, Loader2
} from 'lucide-react';

const BuilderPreviewPanel = ({
  pageSchema,
  selectedSectionIndex,
  setSelectedSectionIndex,
  isGenerating,
  devicePreview,
  setDevicePreview,
  onSave,
  onPublish,
  isSaving,
  pageId,
  pageStatus,
  onMoveSection,
  onDeleteSection,
  onEditInChat,
  modifiedSections
}) => {
  const colors = pageSchema?.color_scheme || {
    primary: '#FF6B35',
    secondary: '#1A1A2E',
    accent: '#4ECDC4',
    background: '#FFFFFF',
    text: '#1A1A2E'
  };

  const sortedSections = pageSchema?.sections
    ? [...pageSchema.sections].sort((a, b) => a.order - b.order)
    : [];

  const previewWidths = {
    desktop: '100%',
    tablet: '768px',
    mobile: '375px'
  };

  return (
    <div className="flex flex-col h-full bg-muted/30">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-background">
        <div className="flex items-center gap-1">
          {[
            { key: 'desktop', icon: Monitor, label: 'Desktop' },
            { key: 'tablet', icon: Tablet, label: 'Tablet' },
            { key: 'mobile', icon: Smartphone, label: 'Mobile' }
          ].map(({ key, icon: Icon, label }) => (
            <Button
              key={key}
              variant={devicePreview === key ? 'default' : 'ghost'}
              size="sm"
              className="h-8 px-2"
              onClick={() => setDevicePreview(key)}
              title={label}
            >
              <Icon className="w-4 h-4" />
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {pageId && pageStatus === 'published' && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8"
              onClick={() => window.open(`/pages/${pageSchema?.slug || ''}`, '_blank')}
            >
              <ExternalLink className="w-4 h-4 mr-1" />
              View Live
            </Button>
          )}
          {pageId && pageStatus === 'draft' && (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={onPublish}
            >
              <Globe className="w-4 h-4 mr-1" />
              Publish
            </Button>
          )}
          <Button
            size="sm"
            className="h-8"
            onClick={onSave}
            disabled={isSaving || !pageSchema}
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Save className="w-4 h-4 mr-1" />
            )}
            Save
          </Button>
        </div>
      </div>

      {/* Preview area */}
      <ScrollArea className="flex-1">
        <div className="p-4 flex justify-center">
          <div
            className="bg-white rounded-lg shadow-sm border overflow-hidden transition-all duration-300"
            style={{
              width: previewWidths[devicePreview],
              maxWidth: '100%',
              minHeight: '400px'
            }}
            onClick={() => setSelectedSectionIndex(null)}
          >
            {/* Empty state */}
            {!pageSchema && !isGenerating && (
              <div className="flex flex-col items-center justify-center py-32 px-8 text-center">
                <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mb-4">
                  <LayoutTemplate className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="font-semibold text-lg mb-2">No page yet</h3>
                <p className="text-muted-foreground text-sm max-w-md">
                  Describe your landing page in the chat panel and I'll generate it for you. You can then iterate on it through conversation.
                </p>
              </div>
            )}

            {/* Loading skeleton */}
            {!pageSchema && isGenerating && (
              <div className="space-y-0">
                <Skeleton className="h-64 w-full rounded-none" />
                <div className="p-8 space-y-4">
                  <Skeleton className="h-8 w-3/4 mx-auto" />
                  <div className="grid grid-cols-3 gap-4">
                    <Skeleton className="h-32" />
                    <Skeleton className="h-32" />
                    <Skeleton className="h-32" />
                  </div>
                </div>
                <div className="p-8 space-y-4">
                  <Skeleton className="h-8 w-1/2 mx-auto" />
                  <Skeleton className="h-24 w-full" />
                  <Skeleton className="h-24 w-full" />
                </div>
                <Skeleton className="h-48 w-full rounded-none" />
              </div>
            )}

            {/* Rendered sections */}
            {pageSchema && sortedSections.map((section, index) => (
              <div
                key={`${section.type}-${section.order}`}
                className={
                  isGenerating && modifiedSections?.includes(index)
                    ? 'animate-pulse'
                    : ''
                }
              >
                <SectionRenderer
                  section={section}
                  colorScheme={colors}
                  isInteractive={true}
                  isSelected={selectedSectionIndex === index}
                  onClick={() => setSelectedSectionIndex(
                    selectedSectionIndex === index ? null : index
                  )}
                  onMoveUp={() => onMoveSection(index, 'up')}
                  onMoveDown={() => onMoveSection(index, 'down')}
                  onDelete={() => onDeleteSection(index)}
                  onEditInChat={() => onEditInChat(index)}
                  isFirst={index === 0}
                  isLast={index === sortedSections.length - 1}
                />
              </div>
            ))}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
};

export default BuilderPreviewPanel;
