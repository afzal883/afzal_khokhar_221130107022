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

* PostgreSQL

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

Create .env.local in /frontend/:

NEXT_PUBLIC_API_URL=[http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)
NEXTAUTH_SECRET=your_secret_key

---

# Start Frontend

npm run dev
Frontend: [http://localhost:3000](http://localhost:3000)

---

# Testing Instructions

API testing:
Use Postman

# Notes

* Use HTTPS in production
* JWT stored in HttpOnly cookies
* Backend must allow CORS from frontend domain
* Images stored in /media/

---
