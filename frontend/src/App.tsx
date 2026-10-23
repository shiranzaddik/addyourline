import { BrowserRouter, Route, Routes } from "react-router-dom";

import { I18nProvider } from "./i18n/I18nContext";
import { ThemeProvider } from "./theme/ThemeContext";
import { CompletedPage } from "./pages/CompletedPage";
import { HomePage } from "./pages/HomePage";
import { JoinPage } from "./pages/JoinPage";
import { PlayPage } from "./pages/PlayPage";

export default function App() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/play/:storyId" element={<PlayPage />} />
            <Route path="/story/:storyId" element={<CompletedPage />} />
            {/* Invitation landing — keep last so static routes win. */}
            <Route path="/:storyId" element={<JoinPage />} />
          </Routes>
        </BrowserRouter>
      </I18nProvider>
    </ThemeProvider>
  );
}
