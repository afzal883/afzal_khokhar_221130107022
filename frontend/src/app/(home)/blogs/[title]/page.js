import React from 'react'
import BlogPage from './BlogPage'
import { notFound } from 'next/navigation';
import axios from 'axios';
export const dynamic = 'force-dynamic'

export async function generateMetadata({ params }) {
    const slug =  params.title;
    // Fetch the home data for metadata purposes
    const { blogsData } = await fetchBlogData(slug);

    return {
        title: blogsData[0].meta_title || '',
        description: blogsData[0].meta_description || '',
        keywords: blogsData[0].keywords || '',
        robots: {
            index: false, // Prevent indexing
            follow: false, // Allow following links (set to false if you want to prevent it)
        },
        alternates: {
            canonical: `https://www.hidelifestyle.co.uk/blogs/${slug}/`,
        }
    };
}

const fetchBlogData = async(slug)=>{
    if(slug){
        const query = `/api/uk-blogs?filters[slug][$eq]=${slug}&populate=*`
        try {
            // Fetch banners, categories, and products concurrently
            const [dataResponse] = await Promise.all([
                axios.get(`${process.env.STRAPI_API}${query}`),
            ]);
            // Parse the JSON responses
            const blogsData = dataResponse.data.data;
            // console.log(blogsData);
            
            return { blogsData };
        } catch (error) {
            console.error("Error fetching data:", error);
        }
    }
}


async function page({params}) {
    if (params.slug !== "null") {
        const slug = await params.title;
        const { blogsData } = await fetchBlogData(slug)
        return (
            <BlogPage data={blogsData && blogsData[0]} />
        );
    }
    else {
        notFound()
    }
}

export default page
