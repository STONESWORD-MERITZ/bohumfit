import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Disclosure from "./pages/Disclosure";
import BeforeAfter from "./pages/BeforeAfter";
import Login from "./pages/Login";
import Signup from "./pages/Signup";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route
            path="disclosure"
            element={<ProtectedRoute><Disclosure /></ProtectedRoute>}
          />
          <Route
            path="before-after"
            element={<ProtectedRoute><BeforeAfter /></ProtectedRoute>}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
