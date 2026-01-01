/**
 * LexFlow Protocol - メインアプリケーション
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WalletProvider } from './contexts/WalletContext';
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
      <WalletProvider>
        <BrowserRouter>
          <div className="app">
            <Header />
            <main className="main-content">
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/contracts" element={<ContractsPage />} />
                <Route path="/contracts/:id" element={<ContractDetail />} />
                <Route path="/contracts/:contractId/obligations" element={<ObligationTimeline />} /> {/* V2: F2 */}
                <Route path="/contracts/:contractId/versions" element={<ContractVersions />} />  {/* V2: F3 */}
                <Route path="/contracts/:contractId/redline" element={<RedlineCompare />} />     {/* V2: F4 */}
                <Route path="/verification" element={<VerificationPage />} />                    {/* V2: F7/F9 Dedicated Page */}
                <Route path="/zk-onboarding" element={<ZKOnboarding />} />                       {/* V2: Legacy Route */}
                <Route path="/upload" element={<UploadPage />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </WalletProvider>
    </QueryClientProvider>
  );
}

export default App;
