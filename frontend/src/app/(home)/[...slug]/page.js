import React, { Suspense } from 'react'
import Shop from '../shop/Shop'
import axios from 'axios';
import { notFound } from 'next/navigation';
import Detail from '../components/Detail';
import { cookies } from 'next/headers';
export const dynamic = 'force-dynamic'


export async function generateMetadata({ params }) {
    const { slug = [] } = await params;

    try {
        if (slug.length === 1) {
            // Category page
            const [category] = slug;
            const response = await axios.get(`${process.env.API_URL}/categories?category=${category}`);
            const data = response?.data // assuming it's an array
            if (data) {
                return {
                    title: data?.categories?.meta_title || data.name,
                    description: data?.categories?.meta_description || '',
                    robots: data?.categories?.index === false ? 'noindex, nofollow' : 'index, follow',
                    alternates: {
                        canonical: `https://www.iconperfumes.in/${category}/` || ''
                    }
                };
            }
        }

        if (slug.length === 2) {
            const [category, second] = slug;

            // First, check if it's a product
            const isProduct = await axios.get(`${process.env.API_URL}/categories?category=${category}&product=${second}`);
            console.log("categories meta data", isProduct?.success)

            if (isProduct?.data?.success) {
                const productData = await axios.get(`${process.env.API_URL}/product/${second}`);
                const data = productData.data;
                return {
                    title: data?.variants[0]?.meta_title || "",
                    description: data?.variants[0]?.meta_description || '',
                    robots: data?.variants[0]?.index === false ? 'noindex, nofollow' : 'index, follow',
                    alternates: {
                        canonical: `https://www.iconperfumes.in/${category}/${data?.variants[0]?.product?.slug}/` || ''
                    }
                };
            }

            // Otherwise, treat as subcategory
            const response = await axios.get(`${process.env.API_URL}/categories?category=${category}&sub-category=${second}`);
            const data = response?.data;

            if (data?.success) {
                return {
                    title: data?.categories?.meta_title || data.name,
                    description: data?.categories?.meta_description || '',
                    robots: data?.categories?.index === false ? 'noindex, nofollow' : 'index, follow',
                    alternates: {
                        canonical: `https://www.iconperfumes.in/${category}/${second}/` || ''
                    }
                };
            }
        }

        if (slug.length === 3) {
            const [category, subcategory, product] = slug;
            const productData = await axios.get(`${process.env.API_URL}/product/${product}`);
            const data = productData.data;
            return {
                title: data?.variants[0]?.meta_title || "",
                description: data?.variants[0]?.meta_description || "",
                robots: data?.variants[0]?.index === false ? 'noindex, nofollow' : 'index, follow',
                alternates: {
                    canonical: `https://www.iconperfumes.in/${category}/${subcategory}/${data?.variants[0]?.product?.slug}/` || ''
                }
            }
        }
    } catch (error) {
        console.error("Metadata error:", error);
    }

    // Default fallback
    return {
        title: 'Page Not Found',
        description: 'The page you are looking for does not exist.',
        robots: 'noindex, nofollow',
    };
}


async function fetchCategoryProducts(category_name, searchParams) {

    const cookieStore = await cookies()
    const cookieString = cookieStore.toString()
    try {
        const pageParam = await searchParams?.page || 1;
        const priceParam = await searchParams?.price;
        const sortParam = await searchParams?.sort_by;
        let filters = {};
        if (priceParam) {
            const decoded = decodeURIComponent(priceParam); // e.g. "minPrice=18,maxPrice=100"
            const parts = decoded.split(',');

            const priceFilter = { min: 0 };
            parts.forEach(part => {
                const [key, value] = part.split('=');
                if (key === 'minPrice') priceFilter.min = Number(value);
                if (key === 'maxPrice') priceFilter.max = Number(value);
            });

            filters.price = priceFilter;
        }

        // Fetch banners, categories, and products concurrently
        const [productsResponse] = await Promise.all([
            axios.get(`${process.env.API_URL}/products?category=${category_name}`, {
                params: {
                    page: pageParam,
                    sort_by: sortParam,
                    ...(Object.keys(filters).length > 0 && { filters: JSON.stringify(filters) })
                },
                withCredentials: true,
                headers: {
                    "Cookie": cookieString
                }
            }),
        ]);
        // Parse the JSON responses

        const products = productsResponse?.data?.variants || [];
        const totalPages = productsResponse.data?.pagination?.totalPages;

        return { products, totalPages };
    } catch (error) {
        console.error("Error fetching data:", error);
        const products = []
        return { products, totalPages: 1 }
        // return error
    }
}
async function fetchSubCategoryProducts(category_name, sub_category_name, searchParams) {
    const cookieStore = await cookies()
    const cookieString = cookieStore.toString()
    try {
        const pageParam = await searchParams?.page || 1;
        const priceParam = await searchParams?.price;
        const sortParam = await searchParams?.sort_by;
        let filters = {};
        if (priceParam) {
            const decoded = decodeURIComponent(priceParam); // e.g. "minPrice=18,maxPrice=100"
            const parts = decoded.split(',');

            const priceFilter = { min: 0 };
            parts.forEach(part => {
                const [key, value] = part.split('=');
                if (key === 'minPrice') priceFilter.min = Number(value);
                if (key === 'maxPrice') priceFilter.max = Number(value);
            });

            filters.price = priceFilter;
        }

        // Fetch banners, categories, and products concurrently
        const [productsResponse] = await Promise.all([
            axios.get(`${process.env.API_URL}/products?category=${category_name}&sub-category=${sub_category_name}`, {
                params: {
                    page: pageParam,
                    sort_by: sortParam,
                    ...(Object.keys(filters).length > 0 && { filters: JSON.stringify(filters) })
                },
                withCredentials: true,
                headers: {
                    "Cookie": cookieString
                }
            }),
        ]);
        // Parse the JSON responses

        const sub_cate_products = productsResponse?.data?.variants || [];
        const totalPages = productsResponse.data?.pagination?.totalPages;


        return { sub_cate_products, totalPages };
    } catch (error) {
        console.error("Error fetching data:", error);
        const sub_cate_products = []
        return { sub_cate_products, totalPages: 1 }
        // return error
    }
}
async function fetchProduct(product) {
    const cookieStore = await cookies()
    const cookieString = cookieStore.toString()
    try {
        // const response = await axios.get(`${process.env.API_URL}/product/${product}/${sku}/?desc=${desc}`)
        const [responseData] = await Promise.all([
            axios.get(`${process.env.API_URL}/product/${product}`, {
                withCredentials: true,
                headers: {
                    "Cookie": cookieString
                }
            })
        ]);

        const data = responseData.data;
        return data
    } catch (error) {
        console.log(error)
    }
}
async function fetchCategories() {
    try {
        // Fetch banners, categories, and products concurrently
        const [categoriesResponse] = await Promise.all([
            axios.get(`${process.env.API_URL}/categories`),
        ]);
        // Parse the JSON responses

        const categories = categoriesResponse?.data?.categories || [];
        return { categories };
    } catch (error) {
        console.error("Error fetching data:", error);
        const categories = []
        return { categories }
        // return error
    }
}
async function checkCategories(categorySlug) {
    try {
        // Fetch banners, categories, and products concurrently
        const [categoriesResponse] = await Promise.all([
            axios.get(`${process.env.API_URL}/categories?category=${categorySlug}`),
        ]);
        // Parse the JSON response
        return categoriesResponse;
    } catch (error) {
        console.error("Error fetching data:", error);
        return false
        // return error
    }
}
async function checkCategoriesProducts(categorySlug, secondSlug) {
    try {
        // Fetch banners, categories, and products concurrently
        const [categoriesResponse] = await Promise.all([
            axios.get(`${process.env.API_URL}/categories?category=${categorySlug}&product=${secondSlug}`),
        ]);
        // Parse the JSON response
        return categoriesResponse;
    } catch (error) {
        console.error("Error fetching data:", error);
        return false
        // return error
    }
}
async function checkSubCategories(categorySlug, secondSlug, productSlug) {
    try {
        // Fetch banners, categories, and products concurrently
        const [categoriesResponse] = await Promise.all([
            axios.get(`${process.env.API_URL}/categories?category=${categorySlug}&sub-category=${secondSlug}&product=${productSlug}`),
        ]);
        // Parse the JSON response
        return categoriesResponse;
    } catch (error) {
        console.error("Error fetching data:", error);
        return false
        // return error
    }
}
async function getProductReviews(slug, searchParams) {
    const page = searchParams?.page || 1
    try {
        const response = await axios.get(`${process.env.API_URL}/get-reviews/${slug}?page=${page}`);
        console.log("reviews",response)
        if (response.data.success) {
            return response.data
        }
    } catch (error) {
        console.log(error)
        return {
            data: {
                reviews: []
            }
        }
    }
}

const page = async ({ params, searchParams }) => {
    const { slug = [] } = await params;

    if (slug.length === 1) {
        const [category] = slug;
        const { products, totalPages } = await fetchCategoryProducts(category, searchParams);
        const { categories } = await fetchCategories();




        if (products.length > 0) {
            return (

                <Suspense fallback={
                    <div className="d-flex align-items-center justify-content-center flex-col" style={{ height: "100vh" }}>
                        <div className="loader-circle">
                            <span class="loader"></span>
                        </div>
                    </div>
                }>
                    <Shop products={products} totalPages={totalPages} categories={categories} category_name={category} />
                </Suspense>
            )
        }
    }
    if (slug.length === 2) {
        const [categorySlug, secondSlug] = slug;

        const category = await checkCategories(categorySlug);
        if (!category?.data?.success) return notFound();

        const isProduct = await checkCategoriesProducts(categorySlug, secondSlug);
        if (isProduct?.data?.success) {
            const data = await fetchProduct(secondSlug);
            const reviews = await getProductReviews(secondSlug, searchParams)
            if (data) {
                return (
                    <Detail review={reviews} detailData={data} slug={secondSlug} />
                )
            }
        }

        // Try checking if secondSlug is a PRODUCT

        // Otherwise, maybe it's a sub-category

        const { sub_cate_products, totalPages } = await fetchSubCategoryProducts(categorySlug, secondSlug, searchParams);
        const { categories } = await fetchCategories();
        if (sub_cate_products.length > 0) {
            return (
                <Suspense fallback={
                    <div className="d-flex align-items-center justify-content-center flex-col" style={{ height: "100vh" }}>
                        <div className="loader-circle">
                            <span class="loader"></span>
                        </div>
                    </div>
                }>
                    <Shop products={sub_cate_products} totalPages={totalPages} categories={categories} category_name={secondSlug} />
                </Suspense>
            )
        }
    }
    if (slug.length === 3) {
        const [categorySlug, subCategorySlug, productSlug] = slug;
        const category = await checkSubCategories(categorySlug, subCategorySlug, productSlug);
        if (!category?.data?.success) return notFound()
        const data = await fetchProduct(productSlug);
        const reviews  = await getProductReviews(productSlug,searchParams);
       


        return (
            <Detail review={reviews} detailData={data} slug={productSlug} />
        )
    }

    notFound();
}

export default page
