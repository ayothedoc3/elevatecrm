import React, { useRef, useEffect } from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  ArrowLeft, Send, Loader2, Sparkles, Bot, User, X
} from 'lucide-react';

const SUGGESTIONS = [
  "Create a landing page for our product",
  "Build a page to recruit affiliates",
  "Design a demo booking page",
  "Make a lead magnet download page"
];

const AI_MODELS = [
  { value: 'gpt-4o', label: 'GPT-4o', provider: 'OpenAI' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini', provider: 'OpenAI' },
  { value: 'gpt-4.1', label: 'GPT-4.1', provider: 'OpenAI' },
  { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini', provider: 'OpenAI' },
  { value: 'anthropic/claude-sonnet-4.5', label: 'Claude Sonnet 4.5', provider: 'Claude' },
  { value: 'anthropic/claude-sonnet-4', label: 'Claude Sonnet 4', provider: 'Claude' },
  { value: 'anthropic/claude-3-5-haiku', label: 'Claude 3.5 Haiku', provider: 'Claude' },
];

const BuilderChatPanel = ({
  messages,
  isGenerating,
  onSendMessage,
  selectedSectionIndex,
  pageSchema,
  onDeselectSection,
  onBack,
  pageName,
  aiModel,
  onModelChange
}) => {
  const [input, setInput] = React.useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isGenerating) return;
    onSendMessage(text);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const selectedSection = selectedSectionIndex !== null && pageSchema?.sections
    ? pageSchema.sections.sort((a, b) => a.order - b.order)[selectedSectionIndex]
    : null;

  const currentModel = AI_MODELS.find(m => m.value === aiModel) || AI_MODELS[0];

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b">
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={onBack}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold text-sm truncate">{pageName || 'New Page'}</h2>
          <p className="text-xs text-muted-foreground">
            {pageSchema?.sections?.length
              ? `${pageSchema.sections.length} sections`
              : 'AI Page Builder'}
          </p>
        </div>
        <Sparkles className="w-4 h-4 text-primary" />
      </div>

      {/* Model Selector */}
      <div className="px-4 py-2 border-b">
        <Select value={aiModel} onValueChange={onModelChange}>
          <SelectTrigger className="h-8 text-xs">
            <SelectValue>
              <span className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${currentModel.provider === 'Claude' ? 'bg-orange-500' : 'bg-green-500'}`} />
                {currentModel.label}
              </span>
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <div className="px-2 py-1 text-xs font-semibold text-muted-foreground">OpenAI</div>
            {AI_MODELS.filter(m => m.provider === 'OpenAI').map(model => (
              <SelectItem key={model.value} value={model.value} className="text-xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  {model.label}
                </span>
              </SelectItem>
            ))}
            <div className="px-2 py-1 text-xs font-semibold text-muted-foreground mt-1">Claude (via OpenRouter)</div>
            {AI_MODELS.filter(m => m.provider === 'Claude').map(model => (
              <SelectItem key={model.value} value={model.value} className="text-xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-500" />
                  {model.label}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-4">
        <div className="py-4 space-y-4">
          {/* Welcome message if no messages */}
          {messages.length === 0 && (
            <div className="text-center py-8">
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">AI Page Builder</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Describe the landing page you want to create and I'll build it for you.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {SUGGESTIONS.map((suggestion, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() => {
                      setInput(suggestion);
                      inputRef.current?.focus();
                    }}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* Chat messages */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-primary" />
                </div>
              )}
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.hadSchemaUpdate && (
                  <Badge variant="outline" className="mt-2 text-xs bg-green-50 text-green-700 border-green-200">
                    Preview updated
                  </Badge>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
                  <User className="w-4 h-4 text-primary-foreground" />
                </div>
              )}
            </div>
          ))}

          {/* Generating indicator */}
          {isGenerating && (
            <div className="flex gap-2 justify-start">
              <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="bg-muted rounded-lg px-3 py-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Building your page...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Section context badge */}
      {selectedSection && (
        <div className="px-4 pb-2">
          <div className="flex items-center gap-2 text-xs bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md px-3 py-1.5">
            <span className="text-blue-700 dark:text-blue-300">
              Editing: <span className="font-medium capitalize">{selectedSection.type.replace('_', ' ')}</span> section
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-4 w-4 p-0 ml-auto"
              onClick={onDeselectSection}
            >
              <X className="w-3 h-3" />
            </Button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="border-t p-3">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedSection
                ? `Describe changes for the ${selectedSection.type.replace('_', ' ')} section...`
                : 'Describe your landing page...'
            }
            disabled={isGenerating}
            rows={1}
            className="flex-1 min-h-[40px] max-h-[120px] resize-none rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
            style={{ height: 'auto', overflow: 'hidden' }}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
          />
          <Button
            size="sm"
            className="h-10 w-10 p-0 flex-shrink-0"
            onClick={handleSend}
            disabled={!input.trim() || isGenerating}
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default BuilderChatPanel;
