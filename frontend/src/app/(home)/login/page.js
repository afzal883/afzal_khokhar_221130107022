import React, { Suspense } from 'react'
import Login from './Login'

export const metadata = {
    alternates: {
        canonical: `https://www.hidelifestyle.co.uk/login/`,
    }
};

const page = () => {
    return (
        <Suspense fallback={
            <div className="d-flex align-items-center justify-content-center flex-col" style={{ height: '100vh' }}>
                <div className="loader-circle">
                    <span class="loader"></span>
                </div>
            </div>
        }>
            <Login />
        </Suspense>
    )
}

export default page
