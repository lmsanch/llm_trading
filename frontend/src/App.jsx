import { DashboardLayout } from './components/dashboard/layout/DashboardLayout';
import { ToastProvider } from './components/dashboard/ui/ToastProvider';
import './App.css';

function App() {
  return (
    <ToastProvider>
      <DashboardLayout />
    </ToastProvider>
  );
}

export default App;