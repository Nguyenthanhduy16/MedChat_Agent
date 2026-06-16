# PharmaCare Frontend - Quick Start Guide

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Server
```bash
npm run dev
```

The app will run on `http://localhost:5173`

### 3. Build for Production
```bash
npm run build
npm run preview  # Preview production build locally
```

---

## 📁 What's Been Created

### Component Files (All using TailwindCSS)

**Layout Components:**
- `src/components/Sidebar.jsx` - Left navigation (256px wide)
- `src/components/TopBar.jsx` - Header with tabs and search
- `src/components/RightPanel.jsx` - Health stats and profile sidebar

**Chat Components:**
- `src/features/chat/components/ChatThread.jsx` - Message container
- `src/features/chat/components/MessageBubble.jsx` - Individual messages
- `src/features/chat/components/TreatmentCard.jsx` - Medication recommendations
- `src/features/chat/components/InteractionAlert.jsx` - Drug warnings
- `src/features/chat/components/Composer.jsx` - Message input area

**Main App:**
- `src/App.jsx` - Complete integrated application

### Configuration Files

- `tailwind.config.js` - TailwindCSS theme with medical colors
- `src/index.css` - Tailwind imports
- `package.json` - Dependencies (already includes all needed packages)

### Documentation

- `FRONTEND_README.md` - Detailed component documentation
- `COMPONENT_EXAMPLES.md` - Usage examples for each component
- `QUICK_START.md` - This file

---

## 🎨 Design Specifications

### Colors
- **Primary Blue**: #003d9b (messages, buttons)
- **AI Messages**: #f1f5f9 (light gray background)
- **User Messages**: #003d9b (blue)
- **Warning Alert**: #eab308 (yellow left border)
- **Danger**: #dc2626 (red)
- **Text**: #191c1e (dark gray)
- **Subtext**: #64748b (slate)

### Layout
- **Sidebar Width**: 256px (left)
- **RightPanel Width**: 192px (right)
- **Main Content**: Flexible (remaining width)
- **Header Height**: 64px
- **Message Thread**: Scrollable with auto-scroll to bottom

---

## 🔌 Backend Integration

The frontend is ready to connect to your FastAPI backend:

### API Endpoints Expected

**1. Send Message**
```bash
POST /api/chat
Content-Type: application/json

{
  "sessionId": "uuid",
  "message": "I have flu symptoms"
}

Response:
{
  "response": "AI response text",
  "treatments": [...],
  "alerts": [...],
  "sources": [...]
}
```

**2. Get Chat History**
```bash
GET /api/history/{sessionId}

Response:
{
  "messages": [...],
  "treatments": [...],
  "alerts": [...]
}
```

**3. Get Health Analytics**
```bash
GET /api/analytics

Response:
{
  "vitals": { "restingHR": 72, "bloodPressure": "128/84" },
  "profile": { "age": 42, "gender": "Male", ... },
  "medications": [...],
  "allergies": [...]
}
```

### Connecting to Backend

In `src/App.jsx`, update the `handleSendMessage` function:

```javascript
const handleSendMessage = async (content) => {
  const newMessages = [...messages, {
    role: 'user',
    content,
    timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
  }];
  setMessages(newMessages);

  try {
    const response = await fetch('http://localhost:8000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId: 'current-session-id',
        message: content,
      }),
    });

    const data = await response.json();
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: data.response,
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      sources: data.sources || [],
    }]);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

---

## ✅ Component Checklist

All components are **fully implemented** and match the Figma design:

- ✅ Sidebar with navigation
- ✅ TopBar with tabs and search
- ✅ ChatThread with scrolling
- ✅ MessageBubble (AI + User)
- ✅ TreatmentCard with dosage/duration grid
- ✅ InteractionAlert with severity levels
- ✅ Composer with send button and toolbar
- ✅ RightPanel with vitals and profile
- ✅ Full responsive layout
- ✅ TailwindCSS styling
- ✅ Icon support (lucide-react)
- ✅ Markdown rendering (react-markdown)

---

## 🧪 Testing Components

### Test Message Flow

1. **Open the app**: http://localhost:5173
2. **See default messages** in ChatThread (already loaded)
3. **Type in Composer**: Type a message in the input box
4. **Click Send**: Message appears on right with blue background
5. **AI Response**: Simulated response appears after 1 second (left side, gray)

### Test Specific Features

**Hover Effects:**
- Hover over AI messages → see Copy, Share, Thumbs buttons
- Hover over alerts → see Dismiss button

**Treatment Card:**
- Visible in the thread with dosage/duration info
- Click "Request Prescription Refill" button

**Interaction Alert:**
- Yellow border on left side
- Shows drug interaction warning
- Can be dismissed

**Sidebar:**
- Click on different sections (Consultations, Prescriptions, etc.)
- See active state change

---

## 🔧 Troubleshooting

### Issue: Components not rendering
**Solution**: Ensure TailwindCSS is imported in `index.css`
```css
@import "tailwindcss";
```

### Issue: Icons not showing
**Solution**: Check lucide-react is installed
```bash
npm install lucide-react
```

### Issue: Markdown not rendering
**Solution**: Check react-markdown is installed
```bash
npm install react-markdown remark-gfm
```

### Issue: Styling looks different
**Solution**: Clear Vite cache and rebuild
```bash
rm -rf node_modules/.vite
npm run dev
```

---

## 📦 Deployment

### Build for Production
```bash
npm run build
```

Output: `dist/` folder with optimized static files

### Deploy Options

**Option 1: Vercel (Recommended)**
```bash
npm install -g vercel
vercel
```

**Option 2: Netlify**
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=dist
```

**Option 3: Docker**
```dockerfile
FROM node:20
WORKDIR /app
COPY . .
RUN npm install
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

---

## 📚 Documentation Files

- **FRONTEND_README.md** - Complete component reference
- **COMPONENT_EXAMPLES.md** - Usage examples and patterns
- **QUICK_START.md** - This file (getting started)
- **../implementation_plan.md** - Overall system architecture
- **../BACKEND_INTEGRATION_GUIDE.md** - Backend setup

---

## 🆘 Support

For issues or questions:

1. Check **COMPONENT_EXAMPLES.md** for usage patterns
2. Review **FRONTEND_README.md** for component props
3. Check browser console for error messages
4. Verify backend is running on `http://localhost:8000`

---

## 🎯 Next Steps

1. ✅ **Frontend components created** (YOU ARE HERE)
2. ⏳ **Setup FastAPI backend** - See BACKEND_INTEGRATION_GUIDE.md
3. ⏳ **Connect frontend to backend API**
4. ⏳ **Test end-to-end chat flow**
5. ⏳ **Deploy to production**

---

**Happy coding! 🚀**
