import { useState, useRef, useEffect } from 'react';
import { Send, Monitor, Paperclip, Mic, ChevronDown, X, File, Image as ImageIcon, Plus, FileText, ChevronRight, Telescope, Globe, MoreHorizontal } from 'lucide-react';

export default function Composer({ onSend, disabled, onRequireAuth }) {
  const [message, setMessage] = useState('');
  const [mode, setMode] = useState('thinking'); // 'instant' or 'thinking'
  const [showModeMenu, setShowModeMenu] = useState(false);
  const [showPlusMenu, setShowPlusMenu] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  
  const textareaRef = useRef(null);
  const menuRef = useRef(null);
  const plusMenuRef = useRef(null);
  const fileInputRef = useRef(null);
  const recognitionRef = useRef(null);
  const messageRef = useRef(message);

  useEffect(() => {
    messageRef.current = message;
  }, [message]);

  useEffect(() => {
    function handleClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowModeMenu(false);
      if (plusMenuRef.current && !plusMenuRef.current.contains(e.target)) setShowPlusMenu(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [message]);

  // Initialize Speech Recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'vi-VN';

      let currentFinalTranscript = '';

      recognition.onstart = () => {
        setIsRecording(true);
        currentFinalTranscript = messageRef.current ? messageRef.current + ' ' : '';
      };

      recognition.onresult = (event) => {
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            currentFinalTranscript += event.results[i][0].transcript + ' ';
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        setMessage(currentFinalTranscript + interimTranscript);
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert('Trình duyệt của bạn không hỗ trợ tính năng nhận diện giọng nói (Web Speech API). Hãy thử dùng Chrome hoặc Edge.');
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files).map(file => ({
        file,
        id: Math.random().toString(36).substring(7),
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null
      }));
      setAttachedFiles(prev => [...prev, ...newFiles]);
    }
    // Reset input value so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (idToRemove) => {
    setAttachedFiles(prev => {
      const newFiles = prev.filter(f => f.id !== idToRemove);
      // Clean up object URLs
      const removedFile = prev.find(f => f.id === idToRemove);
      if (removedFile?.previewUrl) {
        URL.revokeObjectURL(removedFile.previewUrl);
      }
      return newFiles;
    });
  };

  // Clean up object URLs on unmount
  useEffect(() => {
    return () => {
      attachedFiles.forEach(f => {
        if (f.previewUrl) URL.revokeObjectURL(f.previewUrl);
      });
    };
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if ((!message.trim() && attachedFiles.length === 0) || disabled) return;
    if (onRequireAuth) { onRequireAuth(); return; }
    
    // Stop recording if active
    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop();
    }

    // Pass the mode and files to onSend
    onSend?.(message.trim(), mode, attachedFiles.map(f => f.file));
    setMessage('');
    
    // Clean up files
    attachedFiles.forEach(f => {
      if (f.previewUrl) URL.revokeObjectURL(f.previewUrl);
    });
    setAttachedFiles([]);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-white via-white to-transparent pointer-events-none z-20">
      <div className="max-w-3xl mx-auto w-full pointer-events-auto">
        <form 
          onSubmit={handleSubmit} 
          className="relative flex flex-col bg-surface border border-border shadow-sm rounded-[24px] transition-shadow focus-within:shadow-md focus-within:border-primary/30"
        >
          {/* Attached Files Preview Area */}
          {attachedFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 px-4 pt-3 pb-1">
              {attachedFiles.map((fileObj) => (
                <div key={fileObj.id} className="relative group flex items-center bg-surface-muted border border-border rounded-lg p-1.5 pr-3 max-w-[200px]">
                  {fileObj.previewUrl ? (
                    <img src={fileObj.previewUrl} alt="preview" className="w-8 h-8 object-cover rounded shadow-sm mr-2 shrink-0" />
                  ) : (
                    <div className="w-8 h-8 bg-white border border-border rounded flex items-center justify-center mr-2 shrink-0 shadow-sm">
                      <File className="w-4 h-4 text-primary" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-text-primary truncate">{fileObj.file.name}</p>
                    <p className="text-[10px] text-text-muted">{(fileObj.file.size / 1024).toFixed(1)} KB</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(fileObj.id)}
                    className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-surface border border-border rounded-full flex items-center justify-center text-text-muted hover:text-danger hover:border-danger hover:bg-danger-soft transition-colors opacity-0 group-hover:opacity-100 shadow-sm"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-end px-2 py-2">
            {/* Left Actions */}
            <div className="relative" ref={plusMenuRef}>
              <input 
                type="file" 
                multiple
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden" 
                accept="image/*,application/pdf,.doc,.docx,.txt"
              />
              <button
                type="button"
                onClick={() => setShowPlusMenu(p => !p)}
                className="w-10 h-10 flex items-center justify-center rounded-full text-text-muted transition-colors shrink-0 group"
                title="Thêm tệp và nhiều tính năng khác /"
              >
                <div className={`w-8 h-8 rounded-full border flex items-center justify-center transition-colors ${showPlusMenu ? 'bg-surface border-border' : 'border-transparent group-hover:bg-surface group-hover:border-border'}`}>
                  <Plus className="w-5 h-5 text-text-primary" />
                </div>
              </button>

              {/* Plus Menu */}
              {showPlusMenu && (
                <div className="absolute bottom-full left-0 mb-2 w-64 bg-white border border-border shadow-panel rounded-2xl py-2 overflow-hidden z-50">
                  <button 
                    type="button"
                    onClick={() => { fileInputRef.current?.click(); setShowPlusMenu(false); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-[15px] text-left hover:bg-surface-hover transition-colors text-text-primary"
                  >
                    <Paperclip className="w-5 h-5 text-text-secondary" />
                    <span>Tải lên ảnh & tệp</span>
                  </button>
                  <button 
                    type="button"
                    className="w-full flex items-center justify-between px-4 py-2.5 text-[15px] text-left hover:bg-surface-hover transition-colors text-text-primary"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-text-secondary" />
                      <span>Các tệp gần đây</span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-text-muted" />
                  </button>
                  
                  <div className="h-px bg-border my-1.5 mx-4"></div>
                  
                  <button 
                    type="button"
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-[15px] text-left hover:bg-surface-hover transition-colors text-text-primary"
                  >
                    <ImageIcon className="w-5 h-5 text-text-secondary" />
                    <span>Tạo hình ảnh</span>
                  </button>
                  <button 
                    type="button"
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-[15px] text-left hover:bg-surface-hover transition-colors text-text-primary"
                  >
                    <Telescope className="w-5 h-5 text-text-secondary" />
                    <span>Nghiên cứu chuyên sâu</span>
                  </button>
                  <button 
                    type="button"
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-[15px] text-left hover:bg-surface-hover transition-colors text-text-primary"
                  >
                    <Globe className="w-5 h-5 text-text-secondary" />
                    <span>Tìm kiếm trên mạng</span>
                  </button>
                  <button 
                    type="button"
                    className="w-full flex items-center justify-between px-4 py-2.5 text-[15px] text-left hover:bg-surface-hover transition-colors text-text-primary mt-1"
                  >
                    <div className="flex items-center gap-3">
                      <MoreHorizontal className="w-5 h-5 text-text-secondary" />
                      <span>Thêm</span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-text-muted" />
                  </button>
                </div>
              )}
            </div>

            {/* Input */}
            <textarea
              ref={textareaRef}
              rows={1}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={disabled ? "MedAgent đang xử lý..." : "Hỏi về triệu chứng, thuốc hoặc vấn đề sức khỏe..."}
              className="flex-1 bg-transparent px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none disabled:opacity-50 min-w-0 resize-none overflow-y-auto"
              style={{ maxHeight: '200px' }}
            />

            {/* Right Actions */}
            <div className="flex items-center gap-1 pr-1 shrink-0">
              {/* Mode Selector */}
              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => setShowModeMenu(m => !m)}
                  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-muted hover:bg-surface-hover transition-colors text-[13px] font-medium text-text-primary mr-1"
                >
                  {mode === 'instant' ? 'Instant' : 'Lâu hơn'}
                  <ChevronDown className="w-3.5 h-3.5" />
                </button>
                
                {showModeMenu && (
                  <div className="absolute bottom-full right-0 mb-2 w-48 bg-white border border-border shadow-panel rounded-2xl py-2 overflow-hidden z-50">
                    <div className="px-4 py-2 mb-1">
                      <span className="text-[13px] font-medium text-text-muted">Mới nhất • 5.5</span>
                    </div>
                    <button 
                      type="button"
                      onClick={() => { setMode('instant'); setShowModeMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-left hover:bg-surface-hover transition-colors"
                    >
                      <span className={mode === 'instant' ? 'text-text-primary' : 'text-text-secondary'}>Instant</span>
                    </button>
                    <button 
                      type="button"
                      onClick={() => { setMode('thinking'); setShowModeMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-left hover:bg-surface-hover transition-colors"
                    >
                      <span className={mode === 'thinking' ? 'text-text-primary' : 'text-text-secondary'}>
                        Thinking <span className="text-text-muted ml-0.5">• Lâu hơn</span>
                      </span>
                    </button>
                    <div className="h-px bg-border my-1.5 mx-4"></div>
                    <button type="button" className="w-full flex items-center px-4 py-2 text-sm text-left hover:bg-surface-hover transition-colors text-text-primary">
                      Định cấu hình...
                    </button>
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={toggleRecording}
                className={`w-9 h-9 hidden sm:flex items-center justify-center rounded-full transition-colors ${
                  isRecording 
                    ? 'text-danger bg-danger/10 hover:bg-danger/20' 
                    : 'text-text-muted hover:bg-surface-hover hover:text-text-primary'
                }`}
                title={isRecording ? "Dừng ghi âm" : "Nhập bằng giọng nói"}
              >
                <Mic className={`w-5 h-5 ${isRecording ? 'animate-pulse' : ''}`} />
              </button>
              <button
                type="submit"
                disabled={(!message.trim() && attachedFiles.length === 0) || disabled}
                className="w-9 h-9 flex items-center justify-center rounded-full transition-all disabled:opacity-50 disabled:bg-surface-muted disabled:text-text-muted bg-primary text-white hover:bg-primary-dark"
              >
                <Send className="w-4 h-4 ml-0.5" />
              </button>
            </div>
          </div>
        </form>

        {/* Disclaimer */}
        <div className="text-center mt-2">
          <p className="text-[11px] text-text-muted">
            AI có thể mắc lỗi. Vui lòng tham khảo ý kiến bác sĩ hoặc chuyên gia y tế trước khi áp dụng.
          </p>
        </div>
      </div>
    </div>
  );
}
