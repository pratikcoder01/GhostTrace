import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from '@/layouts/AppShell';
import { ToastProvider } from '@/components/ui/ToastContext';
import { WebSocketProvider } from '@/context/WebSocketContext';
import { Dashboard } from '@/pages/Dashboard';
import { NewCase } from '@/pages/NewCase';
import { TransactionGraph } from '@/pages/TransactionGraph';
import { Leads } from '@/pages/Leads';
import { OSINT } from '@/pages/OSINT';
import { WalletExplorer } from '@/pages/WalletExplorer';
import { CashoutForecast } from '@/pages/CashoutForecast';
import { AuditChain } from '@/pages/AuditChain';
import { Reports } from '@/pages/Reports';
import { ModelHealth } from '@/pages/ModelHealth';
import { MLInference } from '@/pages/MLInference';
import { Matrices } from '@/pages/Matrices';
import { Exposure } from '@/pages/Exposure';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ToastProvider>
        <WebSocketProvider>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/new-case" element={<NewCase />} />
              <Route path="/graph" element={<TransactionGraph />} />
              <Route path="/matrices" element={<Matrices />} />
              <Route path="/exposure" element={<Exposure />} />
              <Route path="/triage" element={<MLInference />} />
              <Route path="/leads" element={<Leads />} />
              <Route path="/osint" element={<OSINT />} />
              <Route path="/wallets" element={<WalletExplorer />} />
              <Route path="/cashout" element={<CashoutForecast />} />
              <Route path="/audit" element={<AuditChain />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/benchmark" element={<ModelHealth />} />
            </Route>
          </Routes>
        </WebSocketProvider>
      </ToastProvider>
    </BrowserRouter>
  );
};

export default App;
