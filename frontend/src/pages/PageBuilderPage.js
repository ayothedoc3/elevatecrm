import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '../components/ui/resizable';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import BuilderChatPanel from '../components/landing-pages/BuilderChatPanel';
import BuilderPreviewPanel from '../components/landing-pages/BuilderPreviewPanel';

// Simple UUID generator (no external dependency needed)
const generateId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

const PageBuilderPage = () => {
  const { pageId } = useParams();
  const navigate = useNavigate();
  const { api } = useAuth();

  // Core state
  const [pageSchema, setPageSchema] = useState(null);
  const [messages, setMessages] = useState([]);
  const [conversationId] = useState(() => generateId());
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedSectionIndex, setSelectedSectionIndex] = useState(null);
  const [modifiedSections, setModifiedSections] = useState([]);

  // Page metadata
  const [currentPageId, setCurrentPageId] = useState(pageId || null);
  const [pageName, setPageName] = useState('');
  const [pageStatus, setPageStatus] = useState('draft');
  const [pageSlug, setPageSlug] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Save dialog
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveDialogName, setSaveDialogName] = useState('');

  // AI Model selection
  const [aiModel, setAiModel] = useState('anthropic/claude-sonnet-4.5');

  // Preview device
  const [devicePreview, setDevicePreview] = useState('desktop');

  // Load existing page if editing
  useEffect(() => {
    if (pageId) {
      loadExistingPage(pageId);
    }
  }, [pageId]);

  const loadExistingPage = async (id) => {
    try {
      const response = await api.get(`/landing-pages/${id}`);
      const page = response.data.page || response.data;
      setPageSchema(page.page_schema);
      setPageName(page.name);
      setPageStatus(page.status);
      setPageSlug(page.slug);
      setCurrentPageId(id);

      // Add a system message
      setMessages([{
        id: generateId(),
        role: 'assistant',
        content: `Loaded "${page.name}" with ${page.page_schema?.sections?.length || 0} sections. What would you like to change?`,
        timestamp: new Date().toISOString(),
        hadSchemaUpdate: false
      }]);
    } catch (err) {
      toast.error('Failed to load page');
      navigate('/landing-pages');
    }
  };

  // Send a chat message
  const handleSendMessage = useCallback(async (text) => {
    if (!text.trim() || isGenerating) return;

    const userMsg = {
      id: generateId(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMsg]);
    setIsGenerating(true);
    setModifiedSections([]);

    try {
      const response = await api.post('/landing-pages/chat', {
        conversation_id: conversationId,
        message: text,
        current_schema: pageSchema,
        selected_section_index: selectedSectionIndex,
        page_context: {
          page_type: 'generic',
          tone: 'professional'
        },
        ai_model: aiModel
      });

      const data = response.data;

      const assistantMsg = {
        id: generateId(),
        role: 'assistant',
        content: data.response_text,
        timestamp: new Date().toISOString(),
        hadSchemaUpdate: !!data.updated_schema
      };

      setMessages(prev => [...prev, assistantMsg]);

      if (data.updated_schema) {
        setPageSchema(data.updated_schema);
        setModifiedSections(data.modified_sections || []);
        setIsDirty(true);

        // Auto-derive page name from title if not set
        if (!pageName && data.updated_schema.page_title) {
          setPageName(data.updated_schema.page_title);
        }
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to get AI response';
      const assistantMsg = {
        id: generateId(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${errorMsg}`,
        timestamp: new Date().toISOString(),
        hadSchemaUpdate: false
      };
      setMessages(prev => [...prev, assistantMsg]);
      toast.error(errorMsg);
    } finally {
      setIsGenerating(false);
    }
  }, [api, conversationId, pageSchema, selectedSectionIndex, pageName, isGenerating, aiModel]);

  // Save page
  const handleSave = useCallback(async () => {
    if (!pageSchema) return;

    // If no pageId yet, prompt for name
    if (!currentPageId) {
      setSaveDialogName(pageName || pageSchema.page_title || 'My Landing Page');
      setShowSaveDialog(true);
      return;
    }

    // Update existing page
    setIsSaving(true);
    try {
      await api.put(`/landing-pages/${currentPageId}`, {
        page_schema: pageSchema,
        name: pageName
      });
      setIsDirty(false);
      toast.success('Page saved!');
    } catch (err) {
      toast.error('Failed to save page');
    } finally {
      setIsSaving(false);
    }
  }, [api, pageSchema, currentPageId, pageName]);

  // Create new page (from save dialog)
  const handleCreatePage = async () => {
    if (!saveDialogName.trim()) return;

    setIsSaving(true);
    try {
      const response = await api.post('/landing-pages', {
        name: saveDialogName.trim(),
        page_type: 'generic',
        page_schema: pageSchema
      });
      const newPage = response.data.page || response.data;
      setCurrentPageId(newPage.id);
      setPageName(newPage.name);
      setPageSlug(newPage.slug);
      setPageStatus(newPage.status);
      setIsDirty(false);
      setShowSaveDialog(false);
      toast.success('Page created!');

      // Update URL without full reload
      window.history.replaceState(null, '', `/landing-pages/builder/${newPage.id}`);
    } catch (err) {
      toast.error('Failed to create page');
    } finally {
      setIsSaving(false);
    }
  };

  // Publish page
  const handlePublish = useCallback(async () => {
    if (!currentPageId) {
      handleSave();
      return;
    }

    try {
      await api.post(`/landing-pages/${currentPageId}/publish`);
      setPageStatus('published');
      toast.success('Page published!');
    } catch (err) {
      toast.error('Failed to publish page');
    }
  }, [api, currentPageId, handleSave]);

  // Move section
  const handleMoveSection = useCallback((index, direction) => {
    if (!pageSchema?.sections) return;

    const sections = [...pageSchema.sections].sort((a, b) => a.order - b.order);
    const targetIndex = direction === 'up' ? index - 1 : index + 1;

    if (targetIndex < 0 || targetIndex >= sections.length) return;

    // Swap orders
    const tempOrder = sections[index].order;
    sections[index] = { ...sections[index], order: sections[targetIndex].order };
    sections[targetIndex] = { ...sections[targetIndex], order: tempOrder };

    setPageSchema({ ...pageSchema, sections });
    setSelectedSectionIndex(targetIndex);
    setIsDirty(true);
  }, [pageSchema]);

  // Delete section
  const handleDeleteSection = useCallback((index) => {
    if (!pageSchema?.sections) return;

    const sections = [...pageSchema.sections]
      .sort((a, b) => a.order - b.order)
      .filter((_, i) => i !== index)
      .map((s, i) => ({ ...s, order: i + 1 }));

    setPageSchema({ ...pageSchema, sections });
    setSelectedSectionIndex(null);
    setIsDirty(true);
  }, [pageSchema]);

  // Edit section in chat
  const handleEditInChat = useCallback((index) => {
    setSelectedSectionIndex(index);
  }, []);

  return (
    <div className="h-[calc(100vh-120px)] w-full flex flex-col -m-6">
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Chat Panel */}
        <ResizablePanel defaultSize={35} minSize={25} maxSize={50}>
          <BuilderChatPanel
            messages={messages}
            isGenerating={isGenerating}
            onSendMessage={handleSendMessage}
            selectedSectionIndex={selectedSectionIndex}
            pageSchema={pageSchema}
            onDeselectSection={() => setSelectedSectionIndex(null)}
            onBack={() => navigate('/landing-pages')}
            pageName={pageName}
            aiModel={aiModel}
            onModelChange={setAiModel}
          />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Preview Panel */}
        <ResizablePanel defaultSize={65} minSize={40}>
          <BuilderPreviewPanel
            pageSchema={pageSchema}
            selectedSectionIndex={selectedSectionIndex}
            setSelectedSectionIndex={setSelectedSectionIndex}
            isGenerating={isGenerating}
            devicePreview={devicePreview}
            setDevicePreview={setDevicePreview}
            onSave={handleSave}
            onPublish={handlePublish}
            isSaving={isSaving}
            pageId={currentPageId}
            pageStatus={pageStatus}
            onMoveSection={handleMoveSection}
            onDeleteSection={handleDeleteSection}
            onEditInChat={handleEditInChat}
            modifiedSections={modifiedSections}
          />
        </ResizablePanel>
      </ResizablePanelGroup>

      {/* Save Dialog (for first save) */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Save Landing Page</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <label className="text-sm font-medium mb-2 block">Page Name</label>
            <Input
              value={saveDialogName}
              onChange={(e) => setSaveDialogName(e.target.value)}
              placeholder="My Landing Page"
              onKeyDown={(e) => e.key === 'Enter' && handleCreatePage()}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreatePage} disabled={!saveDialogName.trim() || isSaving}>
              {isSaving ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                'Save Page'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PageBuilderPage;
