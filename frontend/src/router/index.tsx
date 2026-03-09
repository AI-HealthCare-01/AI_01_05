import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppointmentPage } from "../pages/AppointmentPage";
import { DiaryDetailPage } from "../pages/DiaryDetailPage";
import { DiaryPage } from "../pages/DiaryPage";
import { MoodPage } from "../pages/MoodPage";
import { MyPage } from "../pages/MyPage";
import { ReportDetailPage } from "../pages/ReportDetailPage";
import { ReportPage } from "../pages/ReportPage";
import LoginPage from "../pages/LoginPage.tsx";
import KakaoCallbackPage from "../pages/KakaoCallbackPage.tsx";
import {AuthRequired, SignupRequired} from "../components/ProtectedRoute.tsx";
import SignupPage from "../pages/SignupPage.tsx";
import MainPage from "../pages/MainPage.tsx";
import CharacterSelectPage from "../pages/CharacterSelectPage.tsx";

export const router = createBrowserRouter([
  { path: "/", element: <LoginPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/diary", element: <DiaryPage /> },
  { path: "/diary/:entryDate", element: <DiaryDetailPage /> },
  { path: "/report", element: <ReportPage /> },
  { path: "/report/:reportId", element: <ReportDetailPage /> },
  { path: "/moods", element: <MoodPage /> },
  { path: "/appointments", element: <AppointmentPage /> },
  { path: "/mypage", element: <MyPage /> },
  { path: "/auth/kakao/callback", element: <KakaoCallbackPage /> },
  { path: "/signup", element : <SignupRequired><SignupPage /></SignupRequired>},
  { path: "/main", element: <AuthRequired><MainPage /></AuthRequired>},
  { path: "/character-select", element: <AuthRequired><CharacterSelectPage /></AuthRequired>},
  { path: "*", element: <Navigate to="/" replace /> },
]);
