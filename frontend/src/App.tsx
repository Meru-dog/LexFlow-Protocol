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
