import React, { Suspense } from 'react'
import Shop from './Shop'
import axios from 'axios';
import { cookies } from 'next/headers';
export const dynamic = 'force-dynamic'


export const metadata = {
  alternates: {
    canonical: `https://www.hidelifestyle.co.uk/shop/`,
  }
};

async function fetchData(searchParams) {
  
  const pageParam = await searchParams?.page || 1;
  const priceParam = await searchParams?.price;
  const sortParam = await searchParams?.sort_by;
  const best_seller = await searchParams?.best_seller;
  const new_arrival = await searchParams?.new_arrival;
  const query = await searchParams?.q;
  const cookieStore =  await cookies()
  const cookieString = cookieStore.toString()

  // Parse the `price` param into a proper object
  let filters = {};
  if (priceParam) {
    const decoded = decodeURIComponent(priceParam); // e.g. "minPrice=18,maxPrice=100"
    const parts = decoded.split(',');

    const priceFilter = {min:0};
    parts.forEach(part => {
      const [key, value] = part.split('=');
      if (key === 'minPrice') priceFilter.min = Number(value);
      if (key === 'maxPrice') priceFilter.max = Number(value);
    });

    filters.price = priceFilter;
  }

  try {
    const [productsResponse, categoriesResponse] = await Promise.all([
      axios.get(`${process.env.API_URL}/products/`, {
        params: {
          page: pageParam,
          sort_by:sortParam,
          best_seller,
          new_arrival,
          query,
          ...(Object.keys(filters).length > 0 && { filters: JSON.stringify(filters) })
        },
        withCredentials:true,
        headers:{
          "Cookie": cookieString
        }
      }),
      axios.get(`${process.env.API_URL}/categories/`)
    ]);

    const products = productsResponse.data.variants;
    const totalPages = productsResponse.data?.pagination?.totalPages;
    const categories = categoriesResponse.data.categories;
    
    return { products, categories, totalPages };
  } catch (error) {
    console.error("Error fetching data:", error);
    return { products: [], categories: [], totalPages:1 };
  }
}

const page = async ({searchParams}) => {

  const { products, categories, totalPages } = await fetchData(searchParams)

  return (
    <Suspense fallback={
      <div className="d-flex align-items-center justify-content-center flex-col" style={{ height: "100vh" }}>
        <div className="loader-circle">
          <span class="loader"></span>
        </div>
      </div>
    }>
      <Shop products={products} categories={categories} totalPages={totalPages} />
    </Suspense>
  )
}

export default page
