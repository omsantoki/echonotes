import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/shell/AppShell'
import { RequireAuth } from '@/components/auth/RequireAuth'
import { LandingPage } from '@/pages/LandingPage'
import { HomePage } from '@/pages/HomePage'
import { CourseDetailPage } from '@/pages/CourseDetailPage'
import { LectureReadingPage } from '@/pages/LectureReadingPage'
import { UploadPage } from '@/pages/UploadPage'
import { LoginPage } from '@/pages/LoginPage'
import { SignUpPage } from '@/pages/SignUpPage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/pages/ResetPasswordPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      // Public — the landing page never forces a login (feature 002, US-11).
      { path: '/', element: <LandingPage /> },
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignUpPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/reset-password', element: <ResetPasswordPage /> },

      // Gated — the data pages require a session (RequireAuth → /login).
      {
        element: <RequireAuth />,
        children: [
          { path: '/app', element: <HomePage /> },
          { path: '/courses/:courseId', element: <CourseDetailPage /> },
          { path: '/courses/:courseId/upload', element: <UploadPage /> },
          { path: '/lectures/:lectureId', element: <LectureReadingPage /> },
        ],
      },

      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
