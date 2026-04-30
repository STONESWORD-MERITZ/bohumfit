import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Disclosure from "./pages/Disclosure";
import BeforeAfter from "./pages/BeforeAfter";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="disclosure" element={<Disclosure />} />
          <Route path="before-after" element={<BeforeAfter />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
