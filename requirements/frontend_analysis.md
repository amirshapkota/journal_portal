# Frontend Architecture Analysis - Journal Portal

## Executive Summary

**Tech Stack:** Next.js 16 (App Router) + React 19 + TypeScript-free (JSX only)  
**UI Framework:** Tailwind CSS v4 + Radix UI primitives + shadcn-style components  
**State Management:** Redux Toolkit (auth) + TanStack React Query (server state)  
**HTTP Client:** Axios with automatic token refresh & cross-tab auth sync  
**Form Management:** React Hook Form + Zod validation  

**Architecture Pattern:** Feature-based folder structure with domain-driven organization

---

## 1. Project Structure

### Root Structure
```
frontend/
├── app/                    # Next.js App Router (routes)
├── components/            # Shared UI primitives (shadcn/radix)
├── features/              # Feature modules (domain-driven)
├── store/                 # Redux store configuration
├── lib/                   # Utilities & core logic
├── hooks/                 # Global hooks
├── docs/                  # Documentation
├── public/               # Static assets
└── node_modules/         # Dependencies
```

### App Directory (Routes)
```
app/
├── (auth)/               # Auth routes group
│   ├── login/           # Login page
│   └── register/        # Register page
├── (panel)/             # Protected panel routes group
│   ├── admin/          # Admin dashboard & features
│   ├── author/         # Author workspace
│   ├── reader/         # Reader dashboard
│   ├── reviewer/       # Reviewer workspace
│   └── settings/       # User settings
├── choose-role/        # Role selection page
├── unauthorized/       # Access denied page
├── layout.jsx         # Root layout (fonts, providers)
├── providers.jsx      # Context providers wrapper
└── globals.css        # Tailwind + CSS variables
```

### Features Structure (Domain-Driven)
```
features/
├── auth/                 # Authentication feature
│   ├── components/      # LoginForm, RegisterForm
│   ├── api/            # LoginApiSlice, RegisterApiSlice
│   ├── hooks/          # useLoginUser, useRegisterUser
│   ├── redux/          # authSlice (persisted)
│   └── utils/          # authSchema (zod)
├── panel/               # Panel features by role
│   ├── admin/
│   │   ├── dashboard/
│   │   ├── journal/
│   │   ├── user/
│   │   └── verification-requests/
│   ├── author/
│   │   └── components/
│   ├── reader/
│   │   └── components/
│   └── reviewer/
└── shared/              # Cross-feature shared code
    ├── components/      # FormInputField, RoleBasedAuth
    ├── hooks/          # useToggle, useRoleRedirect
    └── utils/
```

---

## 2. Technology Stack Deep Dive

### 2.1 Core Framework
- **Next.js 16.0.1** (App Router)
  - File-based routing in `app/` directory
  - Server & Client components pattern
  - Currently primarily client-side (most components use `"use client"`)
  
- **React 19.2.0**
  - Latest React with improved hooks and performance
  - JSX-only (no TypeScript in this project)

### 2.2 UI & Styling
- **Tailwind CSS v4** with PostCSS
  - Custom design tokens in `globals.css`
  - CSS variables for theming (light/dark modes)
  - Fonts: Jost (headings) + Karla (body)

- **Radix UI Primitives** (18+ components)
  - Accessible, unstyled components
  - Dialog, Dropdown, Popover, Select, etc.
  - Full list: accordion, alert-dialog, avatar, checkbox, collapsible, dialog, dropdown-menu, label, popover, progress, radio-group, scroll-area, select, separator, slot, switch, tooltip

- **shadcn-style Components** (`components/ui/`)
  - Pre-built styled variants using `class-variance-authority`
  - 30+ reusable components: Button, Input, Form, Card, Table, Badge, Sheet, Sidebar, etc.

- **Icons:** lucide-react (v0.548.0)
- **Animations:** Framer Motion v12.23.24 + tw-animate-css

### 2.3 State Management

#### Global Persistent State (Redux Toolkit)
```javascript
// store/store.js
- Redux Toolkit v2.9.2
- Single slice: auth (user data, access token)
- Persisted to localStorage via redux-persist v6.0.0
- Middleware configured to ignore persist actions

// Auth Slice
{
  status: boolean,
  userData: { user, access },
  access: string (JWT token)
}
```

#### Server State (TanStack React Query)
```javascript
- @tanstack/react-query v5.90.5
- Used for all API calls (login, register, etc.)
- Caching, refetching, background updates
- Mutations for write operations
- No global QueryClient config exposed
```

#### Local UI State
- React `useState` for component-level state
- Custom hooks: `useToggle`, `useMobile`
- Theme: `next-themes` v0.4.6

### 2.4 HTTP & API Integration

#### Axios Instance Configuration
```javascript
// lib/instance.js
- Base URL: http://localhost:8000/api/v1/
- Timeout: 15s
- Automatic JWT token injection (Bearer)
- Token refresh on 401 errors
- Cross-tab auth sync via BroadcastChannel
- Public endpoints whitelist: /login/, /register/

Request Flow:
1. Request interceptor adds Authorization header
2. Response interceptor catches 401
3. Attempts token refresh with current access token
4. Queues failed requests during refresh
5. Retries all queued requests with new token
6. On refresh failure: logout + redirect to login
```

#### Cross-Tab Authentication
```javascript
// BroadcastChannel API
- Syncs login/logout across browser tabs
- Prevents auth state desync
- Broadcasts: "login", "logout"
- Implemented in lib/instance.js
```

### 2.5 Form Management
- **React Hook Form v7.65.0**
  - Performance-optimized form state
  - Integration with shadcn Form components
  
- **Zod v4.1.12**
  - Schema validation
  - Type-safe (runtime validation)
  - Used in `features/auth/utils/authSchema.js`

### 2.6 Data Visualization
- **Chart.js v4.5.1** + **react-chartjs-2 v5.3.1**
- **Recharts v3.3.0**
- Used in dashboard score cards and analytics

### 2.7 Additional Libraries
- **date-fns v4.1.0** - Date utilities
- **sonner v2.0.7** - Toast notifications
- **lottie-react v2.4.1** - Animations
- **cmdk v1.1.1** - Command palette
- **vaul v1.1.2** - Drawer component

---

## 3. Authentication Flow

### Login Process
```
1. User submits LoginForm (features/auth/components/LoginForm.jsx)
   └─> Uses react-hook-form + zod validation
   
2. useLoginUser hook triggers mutation
   └─> Calls loginUser() from LoginApiSlice
   └─> POST /auth/login/ with {email, password}
   
3. On success:
   └─> Dispatch login action to Redux (authSlice)
   └─> Store user data + JWT access token
   └─> Persist to localStorage via redux-persist
   └─> Set cookie: auth-token (7 days)
   └─> Broadcast "login" to other tabs
   └─> Redirect based on user roles (useRoleRedirect)
   
4. On error:
   └─> Display toast notification with error message
   └─> Handle throttling, invalid credentials, etc.
```

### Token Refresh Flow
```
1. API call returns 401 Unauthorized
2. Axios interceptor catches error
3. Sets isRefreshing flag = true
4. Queues concurrent requests
5. POST /auth/refresh/ with current access token
6. On success:
   └─> Update Redux state with new token
   └─> Update cookie
   └─> Retry all queued requests
   └─> Return to original flow
7. On failure:
   └─> Dispatch logout action
   └─> Clear persisted state
   └─> Broadcast "logout"
   └─> Redirect to /login
```

### Logout Process
```
1. User clicks logout
2. useLogout hook called
3. Dispatch logout action to Redux
4. Clear localStorage (persist:auth)
5. Clear auth-token cookie
6. Broadcast "logout" to other tabs
7. Navigate to /login
```

---

## 4. Routing & Navigation

### Route Groups
```
(auth)     → Shared auth layout, no auth required
(panel)    → Protected routes, requires authentication
```

### Role-Based Routing
```javascript
// After login, useRoleRedirect determines destination:
ADMIN    → /panel/admin/dashboard
AUTHOR   → /panel/author/dashboard  
REVIEWER → /panel/reviewer/dashboard
READER   → /panel/reader/dashboard
EDITOR   → /panel/editor/dashboard (if exists)
```

### Protected Routes
- Layout-level auth check in `app/(panel)/layout.jsx`
- `RoleBasedAuth` component guards specific features
- Unauthorized access → redirect to `/unauthorized`

---

## 5. Component Architecture

### UI Component Library (components/ui/)
**30 shadcn-style components:**
- Layout: Card, Sheet, Sidebar, Separator, ScrollArea
- Forms: Input, Textarea, Select, Checkbox, RadioGroup, Switch, Form, Label
- Feedback: Badge, Progress, Skeleton, Sonner (toasts), Tooltip
- Overlays: Dialog, Drawer, AlertDialog, Popover, DropdownMenu
- Navigation: Command, Collapsible, Accordion
- Data: Table
- Interactive: Button, Avatar

**Styling Pattern:**
```jsx
// Uses class-variance-authority for variants
import { cva } from "class-variance-authority"

const buttonVariants = cva(
  "base-classes",
  {
    variants: {
      variant: { default, destructive, outline, ghost },
      size: { default, sm, lg, icon }
    }
  }
)
```

### Feature Components

#### Auth Features
- `LoginForm.jsx` - Email/password login with zod validation
- `RegisterForm.jsx` - User registration form

#### Admin Features
- Dashboard components
- Journal management UI
- User management UI
- Verification request handling

#### Author Features
- Submission components (under development)
- Dashboard components

#### Reader Features
- `ReaderAppbar.jsx` - Top navigation with theme toggle, role switcher
- `ReaderSidebar.jsx` - Side navigation
- `RoleRequestForm.jsx` - Request AUTHOR/REVIEWER/EDITOR roles
- `ScoreCard.jsx` - Verification score display
- Dashboard analytics

#### Shared Features
- `FormInputField.jsx` - Reusable form field wrapper
- `RoleBasedAuth.jsx` - Role-based access control component
- `SystemSidebar.jsx` - System-wide sidebar

---

## 6. API Integration Patterns

### API Slice Pattern
```javascript
// features/auth/api/LoginApiSlice.js
import { instance } from "@/lib/instance"

export const loginUser = async (data) => {
  const response = await instance.post("auth/login/", data)
  return response.data
}
```

### React Query Hook Pattern
```javascript
// features/auth/hooks/mutation/useLoginUser.js
import { useMutation } from "@tanstack/react-query"
import { loginUser } from "../../api/LoginApiSlice"

export const useLoginUser = () => {
  const dispatch = useDispatch()
  
  return useMutation({
    mutationFn: loginUser,
    onSuccess: (userData) => {
      dispatch(authLogin({ userData }))
      toast.success("Login successful")
      redirectUser(userData.user.roles)
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || "Login failed")
    }
  })
}
```

### Usage in Components
```jsx
const { mutate: LoginMutation, isPending } = useLoginUser()

const onSubmit = (data) => {
  LoginMutation(data)
}
```

---

## 7. Key Implementation Details

### 7.1 Cross-Tab Authentication Sync
```javascript
// lib/instance.js & features/auth/hooks/useCrossTabAuth.js
const authChannel = new BroadcastChannel("auth-channel")

// Broadcast on login/logout
authChannel.postMessage("login")
authChannel.postMessage("logout")

// Listen in other tabs
authChannel.onmessage = (event) => {
  if (event.data === "logout") {
    dispatch(logout())
    router.push("/login")
  }
}
```

### 7.2 Dynamic Store & Router Injection
```javascript
// Solves circular dependency issues
// Set in app/providers.jsx

setStoreReference(store, logout)  // Axios needs store for token
setAxiosRouter(router)            // Axios needs router for redirects
```

### 7.3 Theme System
```javascript
// next-themes integration
<ThemeProvider 
  attribute="class" 
  defaultTheme="system" 
  enableSystem
>
  {children}
</ThemeProvider>

// CSS variables in globals.css
:root {
  --background: ...
  --foreground: ...
  --primary: ...
}

.dark {
  --background: ...
  --foreground: ...
}
```

### 7.4 Form Validation Schema
```javascript
// features/auth/utils/authSchema.js
import { z } from "zod"

export const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(6, "Password must be at least 6 characters")
})
```

---

## 8. Environment & Configuration

### Environment Variables
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1/
```

### Next.js Config
```javascript
// next.config.mjs
const nextConfig = {
  /* Minimal config - using defaults */
}
```

### Package Scripts
```json
{
  "dev": "next dev",           // Development server
  "build": "next build",       // Production build
  "start": "next start",       // Production server
  "lint": "eslint"            // Code linting
}
```

---

## 9. Current Implementation Status

### ✅ Completed Features
1. **Authentication System**
   - Login/Register flows
   - JWT token management
   - Automatic token refresh
   - Cross-tab sync
   - Redux persistence

2. **UI Component Library**
   - 30+ shadcn-style components
   - Radix UI integration
   - Dark/light theme support
   - Responsive design

3. **Reader Dashboard**
   - Dashboard layout with sidebar/appbar
   - Role request form
   - Score card visualization
   - Profile management

4. **Admin Panel Structure**
   - Journal management setup
   - User management setup
   - Verification request handling

### 🚧 Partially Implemented
1. **Author Dashboard**
   - Components exist but limited functionality
   - Submission workflow incomplete

2. **Reviewer Dashboard**
   - Structure exists
   - Features under development

3. **API Integration**
   - Auth APIs complete
   - Other feature APIs in progress

### ❌ Missing/TODO
1. **SuperDoc Integration**
   - Frontend library not integrated
   - Editor component placeholder exists
   - Backend APIs ready but not connected

2. **Journal Taxonomy UI**
   - Section/Category/ResearchType/Area CRUD
   - Backend models created but no frontend

3. **Submission Workflow**
   - Multi-step submission form
   - Document upload integration
   - Author management UI

4. **Review System UI**
   - Reviewer assignment interface
   - Review form components
   - Decision workflow

5. **Analytics Dashboard**
   - Chart components exist
   - Data integration incomplete

6. **Testing**
   - No test files present
   - No test configuration

---

## 10. Strengths & Architecture Decisions

### ✅ Strengths
1. **Modern Stack**: Next.js 16, React 19, latest libraries
2. **Feature-Based Organization**: Easy to navigate and scale
3. **Type Safety**: Zod validation provides runtime type safety
4. **Robust Auth**: Token refresh, cross-tab sync, persistence
5. **Reusable Components**: shadcn pattern for consistency
6. **Clean Separation**: API, hooks, components well-organized
7. **Performance**: React Query caching, optimistic updates ready

### 🤔 Concerns & Recommendations
1. **No TypeScript**: Using JSX only - consider migration for type safety
2. **Server Components**: Mostly client-side - could leverage SSR more
3. **Error Boundaries**: No error boundary implementation visible
4. **Testing**: Zero test coverage - critical gap
5. **API Documentation**: No OpenAPI/Swagger integration in frontend
6. **Loading States**: Inconsistent loading/skeleton state handling
7. **Accessibility**: Radix provides a11y but not tested
8. **Bundle Size**: Many dependencies - should analyze bundle

---

## 11. Development Workflow

### Local Development
```bash
# Install dependencies
npm install

# Start dev server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

### File Creation Patterns
```
New Feature:
features/
└── my-feature/
    ├── components/      # UI components
    ├── api/            # Axios API wrappers
    ├── hooks/          # React Query hooks
    │   ├── query/      # useGetData hooks
    │   └── mutation/   # useCreateData hooks
    ├── utils/          # Utilities, schemas
    └── index.js        # Exports

New Page:
app/
└── my-route/
    └── page.jsx        # Route component
```

---

## 12. Integration Points with Backend

### Current API Endpoints Used
```
POST /auth/login/           - User login
POST /auth/register/        - User registration  
POST /auth/refresh/         - Token refresh
POST /auth/logout/          - User logout (if implemented)
```

### Expected Backend Integration
```
Journals:
  GET    /journals/journals/
  POST   /journals/journals/
  GET    /journals/sections/?journal={id}
  POST   /journals/sections/
  
Submissions:
  GET    /submissions/submissions/
  POST   /submissions/submissions/
  
Reviews:
  GET    /reviews/assignments/
  POST   /reviews/reviews/
  
Users:
  GET    /users/profiles/
  PATCH  /users/profiles/{id}/
  
Verification:
  GET    /users/verification-requests/
  POST   /users/verification-requests/
  PATCH  /users/verification-requests/{id}/
```

---

## 13. Recommendations for Next Steps

### High Priority
1. **Add TypeScript**: Gradual migration for type safety
2. **Implement Testing**: Jest + React Testing Library
3. **SuperDoc Integration**: Connect editor to backend APIs
4. **Error Boundaries**: Add global error handling
5. **Loading States**: Standardize skeleton/loading patterns

### Medium Priority
6. **Journal Taxonomy UI**: CRUD for Section/Category/ResearchType/Area
7. **Submission Workflow**: Multi-step form with document upload
8. **Review System**: Reviewer dashboard and forms
9. **Analytics Dashboard**: Connect charts to backend data
10. **Bundle Optimization**: Code splitting, lazy loading

### Low Priority
11. **Storybook**: Component documentation
12. **E2E Testing**: Playwright/Cypress
13. **Performance Monitoring**: Web Vitals integration
14. **i18n**: Internationalization setup
15. **PWA**: Progressive Web App features

---

## 14. File Count Summary

**Total Structure:**
- **App Routes**: ~15-20 route folders
- **UI Components**: 30 components in `components/ui/`
- **Feature Components**: 50+ across all features
- **API Slices**: 10+ API wrapper files
- **Hooks**: 20+ custom hooks
- **Documentation**: 5 markdown files

**Dependencies:**
- **Production**: 34 packages
- **Development**: 6 packages
- **Total node_modules**: ~1000+ packages (with transitive deps)

---

## Conclusion

The Journal Portal frontend is a **well-architected, modern Next.js application** with:
- Clean feature-based organization
- Robust authentication system
- Reusable UI component library
- Proper state management separation

**Main gaps:**
- SuperDoc editor integration
- Journal taxonomy UI
- Complete submission/review workflows
- Testing infrastructure
- TypeScript adoption

The foundation is solid for scaling to a full-featured journal management system. Priority should be completing the core workflows (submission, review) and adding comprehensive testing.
