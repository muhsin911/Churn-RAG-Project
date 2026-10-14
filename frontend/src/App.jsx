import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Predictor from "./pages/Predictor.jsx";
import ChatAssistant from "./pages/ChatAssistant.jsx";
import Customers from "./pages/Customers.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />}>
          <Route index element={<Navigate to="/predict" replace />} />
          <Route path="predict" element={<Predictor />} />
          <Route path="customers" element={<Customers />} />
          <Route path="assistant" element={<ChatAssistant />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}