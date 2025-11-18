import React, { Suspense } from 'react'
import ForgotPassword from './ForgotPassword'
export const metadata = {
  alternates: {
    canonical: `https://www.hidelifestyle.co.uk/login/forgot-password/`,
  }
};
const page = () => {
  return (
    <Suspense fallback={
      <div className="d-flex align-items-center justify-content-center flex-col" style={{ height: "100vh" }}>
          <div className="loader-circle">
              <span class="loader"></span>
          </div>
      </div>
    }>
      <ForgotPassword />
    </Suspense>
  )
}

export default page
