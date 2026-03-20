import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";

import { AppointmentListPage } from "../pages/AppointmentListPage";
import { AppointmentPage } from "../pages/AppointmentPage";
import { DiaryDetailPage } from "../pages/DiaryDetailPage";
import { DiaryPage } from "../pages/DiaryPage";
import { MoodPage } from "../pages/MoodPage";
import { MyPage } from "../pages/MyPage";
import { ReportDetailPage } from "../pages/ReportDetailPage";
import { ReportPage } from "../pages/ReportPage";
import LoginPage from "../pages/LoginPage.tsx";
import {AuthRequired, SignupRequired} from "../components/ProtectedRoute.tsx";
import SignupPage from "../pages/SignupPage.tsx";
import MainPage from "../pages/MainPage.tsx";
import CharacterSelectPage from "../pages/CharacterSelectPage.tsx";
import AddMedicationPage from "../pages/AddMedicationPage.tsx";
import MedicineSearchPage from "../pages/MedicineSearchPage.tsx";
import MedicineConfirmPage from "../pages/MedicineConfirmPage.tsx";
import MedicationManagePage from "../pages/MedicationManagePage.tsx";
import { MedicationFlowProvider } from "../store/MedicationFlowContext.tsx";
import { ChatProvider } from "../context/ChatContext.tsx";
import ChatPage from "../pages/ChatPage.tsx";

function MedicationFlowLayout() {
  // 복약 등록 플로우 내부 페이지 간 상태를 공유하기 위한 Provider 경계.
  return (
    <MedicationFlowProvider>
      <Outlet />
    </MedicationFlowProvider>
  );
}

// 라우트 테이블: 페이지 컴포넌트 매핑 + 인증 가드(AuthRequired/SignupRequired) 적용.
export const router = createBrowserRouter([
  { path: "/", element: <LoginPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/diary", element: <DiaryPage /> },
  { path: "/diary/:entryDate", element: <DiaryDetailPage /> },
  { path: "/report", element: <ReportPage /> },
  { path: "/report/:reportId", element: <ReportDetailPage /> },
  { path: "/moods", element: <MoodPage /> },
  { path: "/appointments", element: <AppointmentListPage /> },
  { path: "/appointments/new", element: <AppointmentPage /> },
  { path: "/appointments/:appointmentId/edit", element: <AppointmentPage /> },
  { path: "/mypage", element: <AuthRequired><MyPage /></AuthRequired>},
  { path: "/medications", element: <AuthRequired><MedicationManagePage /></AuthRequired>},
  { path: "/signup", element : <SignupRequired><SignupPage /></SignupRequired>},
  { path: "/main", element: <AuthRequired><MainPage /></AuthRequired>},
  { path: "/character-select", element: <AuthRequired><CharacterSelectPage /></AuthRequired>},
  {
    element: <AuthRequired><MedicationFlowLayout /></AuthRequired>,
    children: [
      { path: "/medications/add", element: <AddMedicationPage /> },
      { path: "/medications/search", element: <MedicineSearchPage /> },
      { path: "/medications/confirm", element: <MedicineConfirmPage /> },
    ],
  },
  { path: "/chat", element: <AuthRequired><ChatProvider><ChatPage /></ChatProvider></AuthRequired>},
  { path: "*", element: <Navigate to="/" replace /> },
]);
