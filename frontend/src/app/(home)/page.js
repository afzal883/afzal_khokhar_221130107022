
import Home from "./Home";
import axios from "axios";
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Buy Pure Attar & Lime Sticks Online | Icon Perfumes',
  description: 'Shop Icon Perfumes for great quality, long-lasting fragrances in India. Find premium attars and lime sticks for men & women.',
  alternates: {
    canonical: 'https://www.iconperfumes.in/',
  },
  robots: {
    index: true,
    follow: true,
  },
};


async function fetchData() {
  try {
    // Fetch banners, categories, and products concurrently
    const [productsResponse] = await Promise.all([
      axios.get(`${process.env.API_URL}/products/?best_seller=true`)
    ]);
    
    const products = productsResponse.data.variants;
    return { products };
  } catch (error) {
    console.error("Error fetching data:", error);
    return {products:[]}
    // return error
  }
}
async function fetchBanners(){
  try {
    const response = await axios.get(`${process.env.API_URL}/banners/`)
    
    if(response.data.success){
      return response.data
    }
  } catch (error) {
    return{
      banners:[]
    }
  }
}
async function fetchNewProducts() {
  try {
    // Fetch banners, categories, and products concurrently
    const [productsResponse] = await Promise.all([
      axios.get(`${process.env.API_URL}/products/?new_arrival=true`)
    ]);

    const newProducts = productsResponse.data.variants;
    return { newProducts };
  } catch (error) {
    console.error("Error fetching data:", error);
    return { newProducts: [] }
    // return error
  }
}
export default async function page() {

  const data = await fetchData()
  const {newProducts} = await fetchNewProducts()
  const {banners} =  await fetchBanners()
  
  return (
    <>
      <Home banners={banners} data={data} newProducts={newProducts} />
    </>
  );
}
