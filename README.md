Here is the **direct plain text** version (no formatting issues) — just copy-paste into your GitHub README.md:

---

# Perfume E-Commerce Platform — Full Stack (Next.js + Django)

## Overview

This is a full-stack perfume e-commerce web application built using Next.js for the frontend and Django + Django REST Framework for the backend. It includes all core e-commerce functionalities such as authentication, product management, cart, wishlist, orders, invoice generation, and admin dashboard.

## Key Features

* JWT-based authentication (login, signup, logout)
* Perfume product listing with filtering and search
* Product detail pages
* Cart management (add, remove, quantity change)
* Wishlist functionality
* Order creation with checkout flow
* Auto-generated PDF invoice for each order
* User profile & order history
* Admin dashboard for product, user, and order management
* Fully responsive Next.js frontend
* Secure Django REST API with Django ORM

---

# Tech Stack

## Frontend (Next.js)

* Next.js 14 (App Router)
* React
* Tailwind CSS
* Axios
* Zustand (state management)

## Backend (Django)

* Django 5
* Django REST Framework
* SimpleJWT
* Pillow
* ReportLab (PDF invoices)
* Django ORM

## Database

* PostgreSQL (recommended)
* SQLite (for development)

---

# Project Structure

Frontend:

* /frontend/app
* /frontend/components
* /frontend/store
* /frontend/utils
* /frontend/public

Backend:

* /backend/config
* /backend/users
* /backend/products
* /backend/orders
* /backend/cart
* /backend/wishlist
* /backend/invoices

---

# Setup Instructions

## 1. Clone the Repository

git clone [https://github.com/yourusername/perfume-ecommerce.git](https://github.com/yourusername/perfume-ecommerce.git)
cd perfume-ecommerce

---

# Backend Setup (Django)

## 2. Create Virtual Environment

cd backend
python -m venv venv
venv\Scripts\activate  (Windows)
source venv/bin/activate  (Mac/Linux)

## 3. Install Dependencies

pip install -r requirements.txt

---

# Backend Environment Variables

Create a .env file inside /backend/config/:

SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=*
DATABASE_NAME=perfume_db
DATABASE_USER=postgres
DATABASE_PASSWORD=yourpassword
DATABASE_HOST=localhost
DATABASE_PORT=5432
JWT_ACCESS_TOKEN_LIFETIME=30
JWT_REFRESH_TOKEN_LIFETIME=1
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=[youremail@gmail.com](mailto:youremail@gmail.com)
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_PORT=587

---

# Database Configuration (PostgreSQL)

CREATE DATABASE perfume_db;
CREATE USER perfume_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE perfume_db TO perfume_user;

---

# Migrations

python manage.py makemigrations
python manage.py migrate

---

# Create Superuser

python manage.py createsuperuser

---

# Start Backend Server

python manage.py runserver
Backend: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

# Frontend Setup (Next.js)

## 1. Navigate

cd ../frontend

## 2. Install Dependencies

npm install

---

# Frontend Environment Variables

Create `.env.local` in `/frontend/`:

NEXT_PUBLIC_API_URL=[http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)
NEXTAUTH_SECRET=your_secret_key

---

# Start Frontend

npm run dev
Frontend: [http://localhost:3000](http://localhost:3000)

---

# Testing Instructions

Backend tests:
python manage.py test

Frontend tests (if used):
npm run test

API testing:
Use Postman
Swagger Docs: /api/docs/

---

# API Summary

Authentication:
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/logout/
GET /api/auth/profile/
PUT /api/auth/profile/

Products:
GET /api/products/
GET /api/products/<id>/

Cart:
GET /api/cart/
POST /api/cart/add/
DELETE /api/cart/remove/<id>/

Wishlist:
GET /api/wishlist/
POST /api/wishlist/add/
DELETE /api/wishlist/remove/<id>/

Orders:
POST /api/orders/create/
GET /api/orders/
GET /api/orders/<id>/invoice/

---

# Frontend Routes

/
/products
/product/[id]
/cart
/wishlist
/checkout
/orders
/login
/register
/admin
/admin/products
/admin/orders

---

# Deployment URLs (replace with your URLs)

Frontend (Vercel): [https://perfume-shop.vercel.app](https://perfume-shop.vercel.app)
Backend (Render/EC2): [https://perfume-api.onrender.com](https://perfume-api.onrender.com)
Swagger Docs: [https://perfume-api.onrender.com/api/docs](https://perfume-api.onrender.com/api/docs)
Admin Panel: [https://perfume-api.onrender.com/admin](https://perfume-api.onrender.com/admin)

---

# Admin Credentials (For Evaluation)

Admin Email: [admin@perfume.com](mailto:admin@perfume.com)
Password: Admin@123

---

# Notes

* Use HTTPS in production
* JWT stored in HttpOnly cookies
* Backend must allow CORS from frontend domain
* Images stored in /media/

---

If you want this in **Markdown style**, **PDF**, **DOCX**, or **beautified README**, just tell me.
