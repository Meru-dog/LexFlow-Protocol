import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WalletProvider } from './contexts/WalletContext';
import { AuthProvider } from './contexts/AuthContext';  // V3: 認証コンテキスト
import { ProtectedRoute } from './components/ProtectedRoute';  // V3: 保護ルート
import { Header } from './components/Header';
import Home from './pages/Home';
import { Dashboard } from './pages/Dashboard';
import { ContractsPage } from './pages/Contracts';
import { UploadPage } from './pages/Upload';
import { ContractDetail } from './pages/ContractDetail';
import ObligationTimeline from './pages/ObligationTimeline';  // V2: F2機能
import ContractVersions from './pages/ContractVersions';    // V2: F3機能
import RedlineCompare from './pages/RedlineCompare';        // V2: F4機能
import VerificationPage from './pages/VerificationPage';    // V2: F7/F9 Dedicated Page
import ZKOnboarding from './components/zk/ZKOnboarding';   // V2: F7/F9機能
// V3: 認証・RBAC・承認フロー
import LoginPage from './pages/Login';
import SignupPage from './pages/Signup';
import ProfilePage from './pages/Profile';
import WorkspaceSettings from './pages/WorkspaceSettings';
import ApprovalFlowsPage from './pages/ApprovalFlows';
import AuditLog from './pages/AuditLog';              // New: 監査証跡ページ
import Notifications from './pages/Notifications';    // New: 通知履歴ページ
import './index.css';

// React Query クライアント
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// メインアプリケーション
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <WalletProvider>
          <BrowserRouter>
            <div className="app">
              <Header />
              <main className="main-content">
                <Routes>
                  {/* Public routes */}
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/signup" element={<SignupPage />} />

                  {/* Protected routes - Home is at root */}
                  <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
                  <Route path="/home" element={<ProtectedRoute><Home /></ProtectedRoute>} />
                  <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                  <Route path="/contracts" element={<ProtectedRoute><ContractsPage /></ProtectedRoute>} />
                  <Route path="/contracts/:id" element={<ProtectedRoute><ContractDetail /></ProtectedRoute>} />
                  <Route path="/contracts/:contractId/obligations" element={<ProtectedRoute><ObligationTimeline /></ProtectedRoute>} />
                  <Route path="/contracts/:contractId/versions" element={<ProtectedRoute><ContractVersions /></ProtectedRoute>} />
                  <Route path="/contracts/:contractId/redline" element={<ProtectedRoute><RedlineCompare /></ProtectedRoute>} />
                  <Route path="/verification" element={<ProtectedRoute><VerificationPage /></ProtectedRoute>} />
                  <Route path="/zk-onboarding" element={<ProtectedRoute><ZKOnboarding /></ProtectedRoute>} />
                  <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
                  <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
                  <Route path="/workspaces" element={<ProtectedRoute><WorkspaceSettings /></ProtectedRoute>} />
                  <Route path="/approvals" element={<ProtectedRoute><ApprovalFlowsPage /></ProtectedRoute>} />
                  <Route path="/audit" element={<ProtectedRoute><AuditLog /></ProtectedRoute>} />
                  <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
                </Routes>
              </main>
            </div>
          </BrowserRouter>
        </WalletProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
