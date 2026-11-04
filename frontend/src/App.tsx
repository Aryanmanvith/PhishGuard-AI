import { Route, Routes } from 'react-router-dom';

import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import EmailAnalyzerPage from './pages/EmailAnalyzerPage';
import HistoryPage from './pages/HistoryPage';
import ModelPage from './pages/ModelPage';
import NotFoundPage from './pages/NotFoundPage';
import ScanDetailPage from './pages/ScanDetailPage';
import UrlAnalyzerPage from './pages/UrlAnalyzerPage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="url" element={<UrlAnalyzerPage />} />
        <Route path="email" element={<EmailAnalyzerPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="history/:scanId" element={<ScanDetailPage />} />
        <Route path="model" element={<ModelPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
