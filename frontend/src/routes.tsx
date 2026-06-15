import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/shell/AppShell'
import { LandingPage } from '@/pages/LandingPage'
import { HomePage } from '@/pages/HomePage'
import { CourseDetailPage } from '@/pages/CourseDetailPage'
import { LectureReadingPage } from '@/pages/LectureReadingPage'
import { UploadPage } from '@/pages/UploadPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/app', element: <HomePage /> },
      { path: '/courses/:courseId', element: <CourseDetailPage /> },
      { path: '/courses/:courseId/upload', element: <UploadPage /> },
      { path: '/lectures/:lectureId', element: <LectureReadingPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
