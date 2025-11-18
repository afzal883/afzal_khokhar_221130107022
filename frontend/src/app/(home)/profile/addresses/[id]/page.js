import React from 'react'
import AddressDetail from './AddressDetail'
import axios from 'axios';
import { cookies } from 'next/headers';

export async function generateMetadata({ params }) {
  const slug = params.id;
  // Fetch the home data for metadata purposes
  

  return {
    alternates: {
      canonical: `https://www.hidelifestyle.co.uk/profile/addresses/${slug}/`,
    }
  };
}

async function getAddressDetail(params) {
  const cookiesStore = await cookies()
  const cookieString = cookiesStore.toString()
    const id =  params.id
    try {
      const response = await axios.get(`${process.env.API_URL}/addresses/?address_id=${id}`,{
        withCredentials:true,
        headers:{
          "Cookie":cookieString,
          "Content-Type":"application/json"
        }
      })
      console.log(response.data);
      if(response.data.success){
        
        return response.data
      }
    } catch (error) {
      console.log(error);
      
        return null
    }
}

const page = async({params}) => {
  const data = await getAddressDetail(params)
  return (
    <AddressDetail address={data.address} id={params.id} />
  )
}

export default page
